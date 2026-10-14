"""
Agent function tools against a real game: they act through the same logged
wrappers as human routes and return compact text for the LLM.
"""
import json
import uuid

from sqlalchemy import select

from app.models.agent import AgentRun, GameAction
from app.services import game_engine as ge
from app.services.agent_tools import RunContext, make_tools


async def _setup(db_session, user, day_call_limit=40):
    game = await ge.create_game(db_session, "🤖 Bot", "Bot", user.id, is_agent=True)
    run = AgentRun(id=uuid.uuid4(), user_id=user.id, game_id=game.id, name="Bot", model="fake", base_url="http://fake")
    db_session.add(run)
    await db_session.commit()
    ctx = RunContext(run_id=run.id, game_id=game.id, user_id=user.id, day_call_limit=day_call_limit)
    ctx.begin_day(game.current_day)
    tools = {t.name: t.func for t in make_tools(ctx)}
    return game, ctx, tools


async def _actions(db_session, game_id):
    db_session.expire_all()
    rows = await db_session.execute(select(GameAction).where(GameAction.game_id == game_id).order_by(GameAction.seq))
    return list(rows.scalars().all())


async def test_get_game_state_returns_compact_board(db_session, user):
    game, ctx, tools = await _setup(db_session, user)
    state = json.loads(await tools["get_game_state"]())

    assert state["day"] == 9 and state["status"] == "active"
    s8 = next(c for c in state["cards"] if c["key"] == "S8")
    assert s8["col"] == "analysis_done" and s8["pull_to"] == "development"
    assert "id" not in s8
    rows = await _actions(db_session, game.id)
    assert rows[-1].action == "get_game_state" and rows[-1].actor == "agent" and rows[-1].run_id == ctx.run_id


async def test_pull_and_assign_are_logged_with_reason(db_session, user):
    game, ctx, tools = await _setup(db_session, user)

    out = await tools["pull_card"](card_key="S11", reason="Start new work")
    assert out == "ERROR: WIP limit reached for analysis"
    assert (await tools["pull_card"](card_key="s8", reason="Free dev capacity")).startswith("OK: S8 moved to development")
    assert (await tools["assign_worker"](worker_id="D1", card_key="S8", reason="Dev on dev")).startswith("OK: D1 assigned")

    rows = [r for r in await _actions(db_session, game.id) if r.action in ("pull_card", "assign_worker")]
    assert [(r.action, r.arguments["card_key"], r.result["ok"], r.reason) for r in rows] == [
        ("pull_card", "S11", False, "Start new work"),
        ("pull_card", "S8", True, "Free dev capacity"),
        ("assign_worker", "S8", True, "Dev on dev"),
    ]


async def test_unknown_or_hidden_card_gives_friendly_error(db_session, user):
    _, _, tools = await _setup(db_session, user)
    assert (await tools["pull_card"](card_key="X99", reason="r")).startswith("ERROR: Unknown card 'X99'")
    # Expedite cards are hidden until they appear — the agent can't see or move them early.
    assert (await tools["pull_card"](card_key="E1", reason="r")).startswith("ERROR: Unknown card 'E1'")


async def test_end_day_marks_day_over_and_blocks_further_mutations(db_session, user):
    _, ctx, tools = await _setup(db_session, user)
    await tools["start_work"](reason="All set")
    out = json.loads(await tools["end_day"](reason="Done"))

    assert out["event"] == "First Day Complete" and out["game_status"] == "active"
    assert ctx.day_ended and ctx.last_modal["day"] == 9
    assert (await tools["pull_card"](card_key="S8", reason="r")).startswith("STOP: the day is already over")


async def test_tool_call_limit_and_cancel_return_stop(db_session, user):
    _, ctx, tools = await _setup(db_session, user, day_call_limit=2)
    await tools["get_game_state"]()
    await tools["get_game_state"]()
    assert (await tools["get_game_state"]()).startswith("STOP: tool-call limit")

    ctx.begin_day(9)
    ctx.cancel.set()
    assert (await tools["get_game_state"]()).startswith("STOP: the run was cancelled")


async def test_tools_cannot_reach_another_users_game(db_session, user):
    other_game = await ge.create_game(db_session, "Theirs", "Other", user.id)
    ctx = RunContext(run_id=uuid.uuid4(), game_id=other_game.id, user_id=uuid.uuid4(), day_call_limit=40)
    tools = {t.name: t.func for t in make_tools(ctx)}
    assert await tools["get_game_state"]() == "ERROR: game not found"
    assert await tools["start_work"](reason="r") == "ERROR: game not found"
