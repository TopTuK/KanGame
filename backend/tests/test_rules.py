"""
The public rules data and the agent's rule knowledge both come from the engine
constants — these tests pin them to the actual numbers the game plays with.
"""
from app.data.cards import CARD_DEFINITIONS, INITIAL_WORKERS
from app.services.agent_prompts import KANBAN_INSTRUCTIONS
from app.services.game_engine import WORK_RANGES
from app.services.rules import rules_payload


def test_rules_payload_mirrors_engine_constants():
    rules = rules_payload()
    assert (rules["start_day"], rules["total_days"]) == (9, 35)
    assert rules["work_ranges"]["development"]["developer"] == list(WORK_RANGES[1]["developer"])
    assert rules["initial_wip"] == {"ready": 5, "analysis": 3, "development": 5, "test": 3, "expedite": 1}
    assert [w["id"] for w in rules["workers"] if w["active_at_start"]] == ["a1", "a2", "d1", "d2", "t1", "t2", "t3"]
    assert [r["min_revenue"] for r in rules["ranks"]] == [700_000, 500_000, 300_000, 150_000, 0]


def test_rules_catalog_lists_every_card_except_unannounced_expedites():
    cards = {c["key"]: c for c in rules_payload()["cards"]}
    assert len(cards) == sum(1 for c in CARD_DEFINITIONS if c["type"] != "expedite")
    assert not any(k.startswith("E") for k in cards)
    assert cards["S1"] == {
        "key": "S1", "type": "standard", "title": "Real-time Dashboard", "analysis": 8, "development": 8,
        "test": 6, "value": 7700, "start_column": "test", "due_day": None, "buff": None,
    }
    assert cards["F2"]["value"] == -35000 and cards["F2"]["due_day"] == 20 and cards["F2"]["start_column"] == "backlog"
    assert cards["I1"]["buff"] == "developer" and cards["I1"]["start_column"] == "ready"


async def test_rules_endpoint_is_public(api_client):
    # api_client is signed in; the route itself has no auth dependency, which the response shape confirms.
    res = await api_client.get("/api/rules")
    assert res.status_code == 200
    assert res.json()["cards"][0]["key"] == "S1"


def test_agent_instructions_know_every_card_estimate():
    for c in CARD_DEFINITIONS:
        if c["type"] == "standard":
            assert f"{c['key']} {c['val']}/day A{c['analysis']} D{c['dev']} T{c['test']}" in KANBAN_INSTRUCTIONS
        elif c["type"] in ("fixed_date", "intangible"):
            assert f"{c['key']} (" in KANBAN_INSTRUCTIONS and f"A/D/T {c['analysis']}/{c['dev']}/{c['test']}" in KANBAN_INSTRUCTIONS


def test_agent_instructions_know_team_and_capacity():
    for role in ("analyst", "developer", "tester"):
        ids = ", ".join(w["id"] for w in INITIAL_WORKERS if w["type"] == role)
        assert f"- {role}s: {ids} (active at the start:" in KANBAN_INSTRUCTIONS
    assert "test about 3 x 5 = 15 points/day" in KANBAN_INSTRUCTIONS
    assert "| developer | 1-4, avg 2.5 | 3-7, avg 5 (specialist) | 2-5, avg 3.5 |" in KANBAN_INSTRUCTIONS


def test_agent_instructions_describe_every_card_type():
    for marker in ("Standard cards (S*) earn their value **every day**", "Fixed-date cards (F*)",
                   "Expedite cards (E*)", "Intangible cards (I*)", "deploying on time costs nothing"):
        assert marker in KANBAN_INSTRUCTIONS
