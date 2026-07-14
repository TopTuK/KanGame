"""
Integration tests for the async game_engine flows against a real Postgres
database (see tests/conftest.py::db_session). These exercise the full
lifecycle: create_game -> assign_worker -> start_work -> end_day, plus the
leaderboard query.
"""
import uuid
from datetime import datetime, timedelta

import pytest

from app.data.cards import CARD_DEFINITIONS, EVENT_DEFINITIONS
from app.models.game import Game, GameStatus
from app.models.user import User
from app.services import game_engine as ge


async def _make_second_user(db_session) -> User:
    u = User(id=uuid.uuid4(), sub="second-sub", email="second@example.com", name="Second", username="second")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


# --- create_game -----------------------------------------------------

async def test_create_game_seeds_all_cards_and_events(db_session, user):
    game = await ge.create_game(db_session, "My Game", "Alice", user.id)

    assert len(game.cards) == len(CARD_DEFINITIONS)
    assert len(game.events) == len(EVENT_DEFINITIONS)
    assert game.current_day == 9
    assert game.total_days == 35
    assert game.wip_limits == {"ready": 5, "analysis": 3, "development": 5, "test": 3, "expedite": 1}


async def test_create_game_places_initial_board_cards_in_expected_lanes(db_session, user):
    game = await ge.create_game(db_session, "My Game", "Alice", user.id)
    by_key = {c.card_key: c for c in game.cards}

    assert by_key["S1"].column == "test"
    assert by_key["S9"].column == "analysis"
    assert by_key["F1"].column == "ready"
    # expedite cards are hidden until their appear_day
    assert by_key["E1"].column == "hidden"


# --- assign_worker -----------------------------------------------------

async def test_assign_worker_toggles_assignment(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    card = next(c for c in game.cards if c.column == "analysis")

    game, err = await ge.assign_worker(db_session, game.id, "a1", card.id, user.id)
    assert err is None
    worker = next(w for w in game.team_config["workers"] if w["id"] == "a1")
    assert worker["assigned_card_id"] == str(card.id)

    game, err = await ge.assign_worker(db_session, game.id, "a1", card.id, user.id)
    assert err is None
    worker = next(w for w in game.team_config["workers"] if w["id"] == "a1")
    assert worker["assigned_card_id"] is None


async def test_assign_worker_rejects_inactive_worker(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    card = next(c for c in game.cards if c.column == "analysis")

    game, err = await ge.assign_worker(db_session, game.id, "a3", card.id, user.id)  # a3 starts inactive
    assert err == "Worker unavailable"


async def test_assign_worker_rejects_card_outside_active_lane(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    card = next(c for c in game.cards if c.column == "ready")

    game, err = await ge.assign_worker(db_session, game.id, "a1", card.id, user.id)
    assert err == "Assignment not allowed"


# --- pull_card -----------------------------------------------------

async def test_pull_card_enforces_wip_limit(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    # the initial board already fills "ready" (S11, S12, S13, F1, I1) to its WIP limit of 5
    assert ge.wip_count(game, "ready") == 5
    backlog_card = next(c for c in game.cards if c.column == "backlog")

    game, err = await ge.pull_card(db_session, game.id, backlog_card.id, user.id)
    assert err == "WIP limit reached for ready"


async def test_pull_card_succeeds_when_under_the_wip_limit(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    # "development" (development + dev_done) starts at 4 of its WIP limit of 5
    assert ge.wip_count(game, "development") == 4
    s8 = next(c for c in game.cards if c.card_key == "S8")
    assert s8.column == "analysis_done"

    game, err = await ge.pull_card(db_session, game.id, s8.id, user.id)
    assert err is None
    updated = next(c for c in game.cards if c.card_key == "S8")
    assert updated.column == "development"


async def test_pull_card_into_deployed_applies_fixed_date_bonus(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    f1 = next(c for c in game.cards if c.card_key == "F1")  # due_day 15, val 10500
    f1.column = "test_done"
    f1.deployed_day = None
    await db_session.commit()

    game, err = await ge.pull_card(db_session, game.id, f1.id, user.id)
    assert err is None
    assert game.total_revenue == 10500


# --- start_work -----------------------------------------------------

async def test_start_work_reduces_remaining_work_by_dice_plus_buff(db_session, user, monkeypatch):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    card = next(c for c in game.cards if c.column == "analysis")
    before = card.analysis_remaining

    game, err = await ge.assign_worker(db_session, game.id, "a1", card.id, user.id)
    assert err is None

    monkeypatch.setattr(ge.random, "randint", lambda lo, hi: hi)  # deterministic max roll

    game, log, err = await ge.start_work(db_session, game.id, user.id)
    assert err is None
    updated = next(c for c in game.cards if c.id == card.id)
    assert updated.analysis_remaining == before - 6  # analyst max roll on Analysis bar is 6
    assert game.work_done is True
    # workers are cleared for the next day's planning phase
    assert all(w["assigned_card_id"] is None for w in game.team_config["workers"])


async def test_start_work_twice_in_a_day_is_rejected(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    game, log, err = await ge.start_work(db_session, game.id, user.id)
    assert err is None

    game, log, err = await ge.start_work(db_session, game.id, user.id)
    assert err == "Work already done today"


# --- end_day -----------------------------------------------------

async def test_end_day_advances_the_day_and_applies_its_event(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    assert game.current_day == 9

    game, _, err = await ge.start_work(db_session, game.id, user.id)
    assert err is None

    game, modal, err = await ge.end_day(db_session, game.id, user.id)
    assert err is None
    assert game.current_day == 10
    assert game.phase == "planning"
    assert game.work_done is False
    assert modal["day"] == 9


async def test_end_day_before_start_work_is_rejected(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    game, modal, err = await ge.end_day(db_session, game.id, user.id)
    assert err == "Start work before ending the day"


async def test_end_day_applies_tester_sick_event_on_day_10(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    active_testers_before = sum(1 for w in game.team_config["workers"] if w["type"] == "tester" and w["active"])

    for _ in range(2):  # day 9 -> day 10 event ("tester_sick") fires when day 10 completes
        game, _, err = await ge.start_work(db_session, game.id, user.id)
        assert err is None
        game, modal, err = await ge.end_day(db_session, game.id, user.id)
        assert err is None

    active_testers_after = sum(1 for w in game.team_config["workers"] if w["type"] == "tester" and w["active"])
    assert active_testers_after == active_testers_before - 1


async def test_end_day_removes_overdue_fixed_date_card_with_penalty(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    f1 = next(c for c in game.cards if c.card_key == "F1")  # due_day 15, positive val -> no penalty on removal
    f2 = next(c for c in game.cards if c.card_key == "F2")  # due_day 20, val -35000
    f2.column = "development"
    f2.due_day = game.current_day  # force it overdue today for a fast test
    await db_session.commit()

    game, _, err = await ge.start_work(db_session, game.id, user.id)
    assert err is None
    game, modal, err = await ge.end_day(db_session, game.id, user.id)
    assert err is None

    updated_f2 = next(c for c in game.cards if c.card_key == "F2")
    assert updated_f2.column == "removed"
    assert game.total_revenue == -35000
    assert modal["overdue"][0]["card_key"] == "F2"


async def test_end_day_on_final_day_completes_the_game(db_session, user):
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    game.current_day = game.total_days
    await db_session.commit()

    game, _, err = await ge.start_work(db_session, game.id, user.id)
    assert err is None
    game, modal, err = await ge.end_day(db_session, game.id, user.id)
    assert err is None
    assert game.status == GameStatus.completed
    assert game.phase == "completed"


async def test_end_day_applies_test_blocker_event_when_a_card_is_in_test(db_session, user):
    # Day 12's scripted event ("blocker_test") fires normally when the
    # default board still has a card sitting in Test at that point.
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    game.current_day = 12
    await db_session.commit()

    game, _, err = await ge.start_work(db_session, game.id, user.id)
    assert err is None
    game, modal, err = await ge.end_day(db_session, game.id, user.id)
    assert err is None
    assert modal["event_key"] == "blocker_test"
    assert any(c.is_blocked for c in game.cards)


async def test_end_day_skips_test_blocker_event_when_test_is_empty(db_session, user):
    # If the player has cleared Test out entirely before day 12 completes,
    # the "defect found in Test" story makes no sense and should fall back
    # to the quiet-day content instead of blocking a nonexistent card.
    game = await ge.create_game(db_session, "G", "Alice", user.id)
    for card in game.cards:
        if card.column in ("test", "exp_test"):
            card.column = "test_done"
    game.current_day = 12
    await db_session.commit()

    game, _, err = await ge.start_work(db_session, game.id, user.id)
    assert err is None
    game, modal, err = await ge.end_day(db_session, game.id, user.id)
    assert err is None
    assert modal["event_key"] == "quiet_day"
    assert not any(c.is_blocked for c in game.cards)


# --- leaderboard -----------------------------------------------------

async def test_leaderboard_ranks_by_best_revenue_and_respects_limit(db_session, user):
    other = await _make_second_user(db_session)

    game_a = await ge.create_game(db_session, "A", "Alice", user.id)
    game_a.status = GameStatus.completed
    game_a.total_revenue = 20000

    game_b = await ge.create_game(db_session, "B", "Bob", other.id)
    game_b.status = GameStatus.completed
    game_b.total_revenue = 50000
    await db_session.commit()

    board = await ge.get_top_leaderboard(db_session, limit=5)
    assert [entry["profit"] for entry in board] == [50000, 20000]

    board = await ge.get_top_leaderboard(db_session, limit=1)
    assert len(board) == 1
    assert board[0]["profit"] == 50000


# --- demo games -----------------------------------------------------

async def test_create_demo_game_spans_day_9_through_15(db_session, demo_user):
    game = await ge.create_demo_game(db_session)

    assert game.current_day == 9
    assert game.total_days == 15
    assert game.is_demo is True
    assert game.user_id == demo_user.id


async def test_create_demo_game_without_demo_user_raises(db_session):
    with pytest.raises(RuntimeError):
        await ge.create_demo_game(db_session)


async def test_demo_game_reaches_completed_status_at_day_15(db_session, demo_user):
    game = await ge.create_demo_game(db_session)
    game.current_day = game.total_days
    await db_session.commit()

    demo_id = game.user_id
    game, _, err = await ge.start_work(db_session, game.id, demo_id)
    assert err is None
    game, modal, err = await ge.end_day(db_session, game.id, demo_id)
    assert err is None
    assert game.status == GameStatus.completed
    assert game.phase == "completed"


async def test_leaderboard_excludes_demo_games(db_session, user, demo_user):
    real_game = await ge.create_game(db_session, "A", "Alice", user.id)
    real_game.status = GameStatus.completed
    real_game.total_revenue = 20000

    demo_game = await ge.create_demo_game(db_session)
    demo_game.status = GameStatus.completed
    demo_game.total_revenue = 999999
    await db_session.commit()

    board = await ge.get_top_leaderboard(db_session, limit=5)
    assert [entry["profit"] for entry in board] == [20000]


async def test_demo_game_isolated_from_real_users_games(db_session, user, demo_user):
    real_game = await ge.create_game(db_session, "A", "Alice", user.id)
    demo_game = await ge.create_demo_game(db_session)

    # the real user's id can't fetch the demo game, and vice versa
    assert await ge.get_game(db_session, demo_game.id, user.id) is None
    assert await ge.get_game(db_session, real_game.id, demo_user.id) is None


async def test_delete_demo_games_removes_children_and_respects_age_cutoff(db_session, demo_user):
    old_game = await ge.create_demo_game(db_session)
    old_game.created_at = datetime.utcnow() - timedelta(hours=25)
    await db_session.commit()

    fresh_game = await ge.create_demo_game(db_session)

    deleted = await ge.delete_demo_games(db_session, older_than=timedelta(hours=24))
    assert deleted == 1

    assert await db_session.get(Game, old_game.id) is None
    assert await db_session.get(Game, fresh_game.id) is not None


async def test_delete_demo_games_ignores_real_games(db_session, user):
    real_game = await ge.create_game(db_session, "A", "Alice", user.id)
    real_game.created_at = datetime.utcnow() - timedelta(hours=48)
    await db_session.commit()

    deleted = await ge.delete_demo_games(db_session, older_than=timedelta(hours=24))
    assert deleted == 0
    assert await db_session.get(Game, real_game.id) is not None
