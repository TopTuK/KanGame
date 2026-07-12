"""
Pure unit tests for game_engine's business-logic helpers.

These build transient (never persisted) Game/Card model instances directly,
so they run without a database and exercise the actual rules: WIP limits,
worker/card eligibility, deploy bonuses & penalties, day-event effects,
blockers, and overdue handling.
"""
import pytest

from app.services import game_engine as ge


# --- WIP -----------------------------------------------------------------

def test_wip_count_groups_active_and_done_lanes_together(make_game, make_card):
    game = make_game(cards=[
        make_card(column="analysis"),
        make_card(column="analysis_done"),
        make_card(column="ready"),
    ])
    assert ge.wip_count(game, "analysis") == 2
    assert ge.wip_count(game, "ready") == 1


def test_can_pull_to_respects_wip_limit(make_game, make_card):
    game = make_game(
        cards=[make_card(column="analysis"), make_card(column="analysis")],
        wip_limits={"ready": 5, "analysis": 3, "development": 5, "test": 3, "expedite": 1},
    )
    assert ge.can_pull_to(game, "analysis") is True

    game.cards.append(make_card(column="analysis_done"))
    assert ge.wip_count(game, "analysis") == 3
    assert ge.can_pull_to(game, "analysis") is False


# --- Worker eligibility ----------------------------------------------------

@pytest.mark.parametrize("column,expected", [
    ("analysis", 0), ("exp_analysis", 0),
    ("development", 1), ("exp_development", 1),
    ("test", 2), ("exp_test", 2),
    ("ready", -1), ("analysis_done", -1), ("deployed", -1),
])
def test_active_bar(make_card, column, expected):
    assert ge.active_bar(make_card(column=column)) == expected


def test_can_assign_worker_rejects_inactive_worker(make_game, make_card):
    game = make_game()
    card = make_card(column="analysis")
    assert ge.can_assign_worker(game, {"active": False}, card) is False


def test_can_assign_worker_rejects_card_outside_active_lane(make_game, make_card):
    game = make_game()
    card = make_card(column="ready")
    assert ge.can_assign_worker(game, {"active": True}, card) is False


def test_can_assign_worker_allows_active_worker_on_active_card(make_game, make_card):
    game = make_game()
    card = make_card(column="development")
    assert ge.can_assign_worker(game, {"active": True}, card) is True


# --- Stage completion ------------------------------------------------------

@pytest.mark.parametrize("bar,field,remaining,expected", [
    (0, "analysis_remaining", 0.0, True),
    (0, "analysis_remaining", -1.0, True),
    (0, "analysis_remaining", 0.5, False),
    (1, "dev_remaining", 0.0, True),
    (1, "dev_remaining", 2.0, False),
    (2, "test_remaining", 0.0, True),
    (2, "test_remaining", 1.0, False),
])
def test_stage_complete(make_card, bar, field, remaining, expected):
    card = make_card(**{field: remaining})
    assert ge._stage_complete(card, bar) is expected


# --- Deploy bonuses / penalties --------------------------------------------

def test_fixed_date_card_deployed_on_time_earns_bonus(make_game, make_card):
    game = make_game(current_day=15)
    card = make_card(card_type="fixed_date", due_day=15, deployed_day=15, val=10500)
    log = []
    ge._apply_deploy_bonuses(game, card, log)
    assert game.total_revenue == 10500
    assert log == [{"type": "bonus", "card_key": card.card_key, "amount": 10500}]


def test_fixed_date_card_deployed_late_with_negative_value_is_penalized(make_game, make_card):
    game = make_game(current_day=21)
    card = make_card(card_type="fixed_date", due_day=20, deployed_day=21, val=-35000)
    log = []
    ge._apply_deploy_bonuses(game, card, log)
    assert game.total_revenue == -35000
    assert log == [{"type": "penalty", "card_key": card.card_key, "amount": -35000}]


def test_fixed_date_card_deployed_late_with_positive_value_gets_nothing(make_game, make_card):
    game = make_game(current_day=16)
    card = make_card(card_type="fixed_date", due_day=15, deployed_day=16, val=10500)
    log = []
    ge._apply_deploy_bonuses(game, card, log)
    assert game.total_revenue == 0
    assert log == []


def test_intangible_card_deployment_grants_a_permanent_buff(make_game, make_card):
    game = make_game()
    card = make_card(card_type="intangible", buff="developer", val=0)
    log = []
    ge._apply_deploy_bonuses(game, card, log)
    assert ge._buffs(game)["developer"] == 1
    assert log == [{"type": "buff", "card_key": card.card_key, "buff": "developer"}]


def test_expedite_card_with_negative_value_is_always_penalized_on_deploy(make_game, make_card):
    # E2/E3-style cards: negative value means deploying them costs money
    # regardless of whether they beat their due day.
    game = make_game(current_day=10)
    card = make_card(card_type="expedite", due_day=25, deployed_day=10, val=-175000)
    log = []
    ge._apply_deploy_bonuses(game, card, log)
    assert game.total_revenue == -175000
    assert log[0]["type"] == "penalty"


def test_expedite_card_with_positive_value_earns_bonus_only_if_on_time(make_game, make_card):
    game = make_game(current_day=18)
    card = make_card(card_type="expedite", due_day=18, deployed_day=18, val=140000)
    log = []
    ge._apply_deploy_bonuses(game, card, log)
    assert game.total_revenue == 140000
    assert log[0]["type"] == "bonus"


# --- Story advancement -------------------------------------------------

def test_advance_story_moves_card_to_its_done_lane(make_game, make_card):
    game = make_game()
    card = make_card(column="development")
    log = []
    ge._advance_story(game, card, log)
    assert card.column == "dev_done"
    assert log == [{"type": "advance", "card_key": card.card_key, "to": "dev_done"}]


# --- Overdue handling -------------------------------------------------

def test_find_overdue_matches_active_fixed_date_and_expedite_cards_due_today(make_game, make_card):
    game = make_game(current_day=20)
    due_today = make_card(column="development", card_type="fixed_date", due_day=20)
    not_due_yet = make_card(column="development", card_type="fixed_date", due_day=25)
    wrong_type = make_card(column="development", card_type="standard", due_day=20)
    already_deployed = make_card(column="deployed", card_type="fixed_date", due_day=20)
    game.cards = [due_today, not_due_yet, wrong_type, already_deployed]

    overdue = ge._find_overdue(game, 20)
    assert overdue == [due_today]


def test_remove_overdue_penalizes_negative_value_cards_and_frees_their_worker(make_game, make_card, make_worker):
    card = make_card(column="development", card_type="fixed_date", due_day=20, val=-35000)
    worker = make_worker("d1", "developer", assigned_card_id=str(card.id))
    game = make_game(cards=[card], team_config={"workers": [worker], "buffs": {}})

    log = []
    ge._remove_overdue(game, [card], log)

    assert card.column == "removed"
    assert game.total_revenue == -35000
    assert ge._workers(game)[0]["assigned_card_id"] is None
    assert log == [{"type": "overdue_penalty", "card_key": card.card_key, "amount": -35000}]


def test_remove_overdue_just_drops_positive_value_cards(make_game, make_card):
    card = make_card(column="development", card_type="fixed_date", due_day=20, val=7000)
    game = make_game(cards=[card])

    log = []
    ge._remove_overdue(game, [card], log)

    assert card.column == "removed"
    assert game.total_revenue == 0
    assert log == [{"type": "overdue_lost", "card_key": card.card_key}]


# --- Day effects -------------------------------------------------

def test_apply_day_effects_worker_out_deactivates_an_active_worker_of_that_type(make_game, make_worker):
    card_id = "some-card"
    workers = [make_worker("t1", "tester", assigned_card_id=card_id), make_worker("t2", "tester")]
    game = make_game(team_config={"workers": workers, "buffs": {}})

    ge._apply_day_effects(game, [{"type": "workerOut", "workerType": "tester"}])

    t1 = next(w for w in ge._workers(game) if w["id"] == "t1")
    assert t1["active"] is False
    assert t1["assigned_card_id"] is None


def test_apply_day_effects_worker_in_activates_an_inactive_worker_of_that_type(make_game, make_worker):
    workers = [make_worker("d3", "developer", active=False), make_worker("d4", "developer", active=False)]
    game = make_game(team_config={"workers": workers, "buffs": {}})

    ge._apply_day_effects(game, [{"type": "workerIn", "workerType": "developer"}])

    active_devs = [w for w in ge._workers(game) if w["active"]]
    assert len(active_devs) == 1
    assert active_devs[0]["id"] == "d3"  # first matching inactive worker


def test_apply_day_effects_wip_change_updates_the_limit(make_game):
    game = make_game()
    ge._apply_day_effects(game, [{"type": "wipChange", "lane": "ready", "value": 3}])
    assert game.wip_limits["ready"] == 3


@pytest.mark.parametrize("effect,attr,expected", [
    ({"type": "carlosOn"}, "carlos_policy", True),
    ({"type": "lockdownOn"}, "lockdown", True),
])
def test_apply_day_effects_policy_flags(make_game, effect, attr, expected):
    game = make_game()
    ge._apply_day_effects(game, [effect])
    assert getattr(game, attr) is expected


def test_apply_day_effects_carlos_off_clears_the_flag(make_game):
    game = make_game(carlos_policy=True)
    ge._apply_day_effects(game, [{"type": "carlosOff"}])
    assert game.carlos_policy is False


def test_apply_blocker_picks_first_card_in_the_named_lane(make_game, make_card):
    first = make_card(column="test")
    second = make_card(column="test")
    game = make_game(cards=[first, second])

    ge._apply_blocker(game, "test")

    assert first.is_blocked is True
    assert 5 <= first.blocker_total <= 7
    assert first.blocker_remaining == first.blocker_total
    assert second.is_blocked is False


def test_apply_blocker_falls_back_to_expedite_lane_when_standard_lane_is_empty(make_game, make_card):
    exp_card = make_card(column="exp_development")
    game = make_game(cards=[exp_card])

    ge._apply_blocker(game, "development")

    assert exp_card.is_blocked is True


def test_apply_blocker_is_a_noop_when_lane_is_empty(make_game):
    game = make_game(cards=[])
    ge._apply_blocker(game, "test")  # must not raise


# --- Expedite reveal -------------------------------------------------

def test_reveal_expedite_only_reveals_cards_appearing_that_day(make_game, make_card):
    due_now = make_card(card_type="expedite", column="hidden", appear_day=15)
    later = make_card(card_type="expedite", column="hidden", appear_day=20)
    already_shown = make_card(card_type="expedite", column="exp_backlog", appear_day=15)
    game = make_game(cards=[due_now, later, already_shown])

    ge._reveal_expedite(game, 15)

    assert due_now.column == "exp_backlog"
    assert later.column == "hidden"
