"""
Pure data-integrity tests for the card/event definitions that drive the game.
No database required.
"""
import math

from app.data.cards import (
    ADVANCE_MAP,
    CARD_DEFINITIONS,
    DAY_EVENTS,
    EVENT_DEFINITIONS,
    INITIAL_BOARD,
    INITIAL_WORKERS,
    PULL_MOVES,
    apply_initial_work_remaining,
)


def test_card_counts_by_type():
    by_type = {}
    for card in CARD_DEFINITIONS:
        by_type[card["type"]] = by_type.get(card["type"], 0) + 1

    assert by_type == {"standard": 50, "fixed_date": 5, "intangible": 5, "expedite": 4}
    assert len(CARD_DEFINITIONS) == 64


def test_card_keys_are_unique():
    keys = [c["key"] for c in CARD_DEFINITIONS]
    assert len(keys) == len(set(keys))


def test_work_amounts_are_clamped_between_3_and_10():
    for card in CARD_DEFINITIONS:
        assert 3 <= card["analysis"] <= 10
        assert 3 <= card["dev"] <= 10
        assert 3 <= card["test"] <= 10


def test_standard_cards_have_revenue_equal_to_value():
    for card in CARD_DEFINITIONS:
        if card["type"] == "standard":
            assert card["revenue"] == card["val"]
        else:
            assert card["revenue"] == 0


def test_fixed_date_and_expedite_cards_have_due_days():
    by_key = {c["key"]: c for c in CARD_DEFINITIONS}
    for key in ("F1", "F2", "F3", "F4", "F5", "E1", "E2", "E3", "E4"):
        assert "due_day" in by_key[key]


def test_expedite_cards_have_appear_day_and_start_hidden():
    by_key = {c["key"]: c for c in CARD_DEFINITIONS}
    for key in ("E1", "E2", "E3", "E4"):
        assert "appear_day" in by_key[key]
        assert by_key[key]["appear_day"] < by_key[key]["due_day"]


def test_intangible_cards_have_a_buff_target():
    by_key = {c["key"]: c for c in CARD_DEFINITIONS}
    for key in ("I1", "I2", "I3", "I4", "I5"):
        assert by_key[key]["buff"] in ("analyst", "developer", "tester")


def test_initial_board_only_references_known_standard_cards():
    known_keys = {c["key"] for c in CARD_DEFINITIONS}
    placed = [key for keys in INITIAL_BOARD.values() for key in keys]
    assert len(placed) == len(set(placed)), "a card cannot start in two lanes at once"
    assert set(placed).issubset(known_keys)


def test_day_events_span_days_9_to_35_inclusive():
    assert set(DAY_EVENTS.keys()) == set(range(9, 36))


def test_event_definitions_are_sorted_and_match_day_events():
    assert len(EVENT_DEFINITIONS) == len(DAY_EVENTS)
    days = [ev["day"] for ev in EVENT_DEFINITIONS]
    assert days == sorted(days)
    for ev in EVENT_DEFINITIONS:
        assert ev["payload"]["effects"] == DAY_EVENTS[ev["day"]]["effects"]


def test_advance_map_targets_are_done_lanes_not_deployed():
    # start_work() only auto-advances active lanes into their "_done" lane;
    # the deployed transition always happens via an explicit pull_card().
    for target in ADVANCE_MAP.values():
        assert target not in ("deployed", "exp_deployed")


def test_pull_moves_cover_every_advance_map_target():
    for target in ADVANCE_MAP.values():
        assert target in PULL_MOVES


def test_initial_workers_counts_match_team_roster():
    by_type = {}
    active_by_type = {}
    for w in INITIAL_WORKERS:
        by_type[w["type"]] = by_type.get(w["type"], 0) + 1
        if w["active"]:
            active_by_type[w["type"]] = active_by_type.get(w["type"], 0) + 1

    assert by_type == {"analyst": 4, "developer": 4, "tester": 4}
    assert active_by_type == {"analyst": 2, "developer": 2, "tester": 3}


def test_apply_initial_work_remaining_for_test_lane():
    a, d, t = apply_initial_work_remaining(8, 8, 6, "test")
    assert (a, d, t) == (0.0, 0.0, 6.0)


def test_apply_initial_work_remaining_for_development_lane():
    a, d, t = apply_initial_work_remaining(10, 10, 6, "development")
    assert a == 0.0
    assert d == math.ceil(10 * 0.6)
    assert t == 6.0


def test_apply_initial_work_remaining_for_analysis_lane():
    a, d, t = apply_initial_work_remaining(10, 9, 6, "analysis")
    assert a == math.ceil(10 * 0.6)
    assert d == 9.0
    assert t == 6.0


def test_apply_initial_work_remaining_for_untouched_lane():
    a, d, t = apply_initial_work_remaining(7, 8, 9, "ready")
    assert (a, d, t) == (7.0, 8.0, 9.0)
