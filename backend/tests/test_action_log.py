"""
Human player actions are logged to game_actions through the regular game routes,
in the same shape the AI agent uses (card keys / worker ids, never UUIDs).
"""
from sqlalchemy import select

from app.models.agent import GameAction
from app.services import game_engine as ge


def _card_id(game_json: dict, key: str) -> str:
    return next(c["id"] for c in game_json["cards"] if c["card_key"] == key)


async def _actions(db_session, game_id) -> list[GameAction]:
    db_session.expire_all()
    result = await db_session.execute(
        select(GameAction).where(GameAction.game_id == game_id).order_by(GameAction.seq)
    )
    return list(result.scalars().all())


async def test_create_game_logs_initial_day_start_snapshot(api_client, db_session):
    res = await api_client.post("/api/games", json={"name": "G", "player_name": "Alice"})
    assert res.status_code == 201
    game = res.json()

    rows = await _actions(db_session, game["id"])
    assert [(r.seq, r.actor, r.action, r.day) for r in rows] == [(1, "human", "day_start", 9)]
    state = rows[0].state
    assert state["day"] == 9
    assert {c["key"] for c in state["cards"]} >= {"S1", "F1", "I1"}
    assert not any(c["key"].startswith("E") for c in state["cards"])  # hidden expedite cards
    assert state["wip"]["analysis"] == {"limit": 3, "count": 3, "lanes": ["analysis", "analysis_done"]}
    assert {w["id"] for w in state["workers"] if w["active"]} >= {"a1", "d1", "t1"}


async def test_pull_logs_success_and_engine_error_with_card_keys(api_client, db_session):
    game = (await api_client.post("/api/games", json={"player_name": "Alice"})).json()

    # Analysis lane (analysis + analysis_done) is full at the start: S9, S10, S8.
    res = await api_client.post(f"/api/games/{game['id']}/pull-card", json={"card_id": _card_id(game, "S11")})
    assert res.status_code == 400
    res = await api_client.post(f"/api/games/{game['id']}/pull-card", json={"card_id": _card_id(game, "S8")})
    assert res.status_code == 200

    rows = [r for r in await _actions(db_session, game["id"]) if r.action == "pull_card"]
    assert rows[0].actor == "human"
    assert rows[0].arguments == {"card_key": "S11", "from_col": "ready"}
    assert rows[0].result == {"ok": False, "error": "WIP limit reached for analysis"}
    assert rows[1].arguments == {"card_key": "S8", "from_col": "analysis_done"}
    assert rows[1].result["ok"] is True and rows[1].result["to_col"] == "development"


async def test_assign_logs_toggle_outcomes(api_client, db_session):
    game = (await api_client.post("/api/games", json={"player_name": "Alice"})).json()
    url = f"/api/games/{game['id']}/assign-worker"

    for key in ("S9", "S10", "S10"):
        res = await api_client.post(url, json={"worker_id": "a1", "card_id": _card_id(game, key)})
        assert res.status_code == 200

    rows = [r for r in await _actions(db_session, game["id"]) if r.action == "assign_worker"]
    assert [r.result.get("outcome") for r in rows] == ["assigned", "reassigned", "unassigned"]
    assert rows[1].result["previous_card"] == "S9"
    assert rows[0].arguments == {"worker_id": "a1", "worker_type": "analyst", "card_key": "S9", "card_col": "analysis"}


async def test_start_work_and_end_day_are_logged_with_next_day_snapshot(api_client, db_session):
    game = (await api_client.post("/api/games", json={"player_name": "Alice"})).json()
    await api_client.post(
        f"/api/games/{game['id']}/assign-worker", json={"worker_id": "t1", "card_id": _card_id(game, "S1")}
    )
    assert (await api_client.post(f"/api/games/{game['id']}/start-work")).status_code == 200
    assert (await api_client.post(f"/api/games/{game['id']}/end-day")).status_code == 200

    rows = await _actions(db_session, game["id"])
    actions = [r.action for r in rows]
    assert actions == ["day_start", "assign_worker", "start_work", "end_day", "day_start"]

    start = rows[2]
    assert start.arguments["assignments"]["t1"] == "S1"
    assert "a1" in start.arguments["idle_workers"]
    assert any(e["card_key"] == "S1" for e in start.result["log"])

    end = rows[3]
    assert end.day == 9 and end.result["next_day"] == 10 and end.result["event_key"] == "welcome"
    assert rows[4].day == 10 and rows[4].state["day"] == 10


async def test_actions_endpoint_returns_log_in_order(api_client):
    game = (await api_client.post("/api/games", json={"player_name": "Alice"})).json()
    await api_client.post(f"/api/games/{game['id']}/start-work")

    res = await api_client.get(f"/api/games/{game['id']}/actions")
    assert res.status_code == 200
    body = res.json()
    assert [a["seq"] for a in body] == [1, 2]
    assert body[1]["action"] == "start_work"

    res = await api_client.get(f"/api/games/{game['id']}/actions", params={"after_seq": 1})
    assert [a["seq"] for a in res.json()] == [2]


async def test_human_routes_refuse_agent_games(api_client, db_session, user):
    game = await ge.create_game(db_session, "Bot", "Bot", user.id, is_agent=True)
    res = await api_client.post(f"/api/games/{game.id}/start-work")
    assert res.status_code == 409
    assert await _actions(db_session, game.id) == []


async def test_games_list_flags_agent_games(api_client, db_session, user):
    await ge.create_game(db_session, "Bot", "Bot", user.id, is_agent=True)
    await api_client.post("/api/games", json={"player_name": "Alice"})

    res = await api_client.get("/api/games")
    assert sorted(g["is_agent"] for g in res.json()) == [False, True]
