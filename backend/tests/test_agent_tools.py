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


async def test_get_game_state_returns_readable_board(db_session, user):
    game, ctx, tools = await _setup(db_session, user)
    board = await tools["get_game_state"]()

    assert board.startswith("DAY 9 of 35 | status: active | work started today: no")
    # Working columns show work left in the card's current stage.
    assert "  - S1 (earns 7700/day) left: 6 test points" in board
    assert "fixed_date, value 10500, due end of day 15" in board  # F1 in ready
    # WIP usage per stage, counting working + done columns together.
    assert "analysis 3/3 [analysis+analysis_done] FULL" in board
    assert "development 4/5 [development+dev_done] 1 free" in board
    # Only legal pulls are listed: ready/analysis/test are full, development has one slot.
    pulls = board.split("PULLS POSSIBLE RIGHT NOW")[1].strip().splitlines()[1:]
    assert pulls == ["  - S8: analysis_done -> development"]
    assert "Unavailable (cannot be assigned): a3, a4, d3, d4, t4" in board
    assert "E1" not in board  # hidden expedite cards are not shown
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


async def test_worked_example_in_instructions_is_legal(db_session, user):
    """The opening-day walkthrough in KANBAN_INSTRUCTIONS must match real engine behaviour."""
    _, _, tools = await _setup(db_session, user)
    for key in ("S4", "S5"):
        assert (await tools["pull_card"](card_key=key, reason="r")) == "ERROR: WIP limit reached for test"
    assert (await tools["pull_card"](card_key="S8", reason="r")).startswith("OK: S8 moved to development")
    assert (await tools["pull_card"](card_key="S11", reason="r")).startswith("OK: S11 moved to analysis")
    for worker, card in (("t1", "S1"), ("t2", "S2"), ("t3", "S3"), ("d1", "S6"), ("d2", "S7"), ("a1", "S9"), ("a2", "S10")):
        assert (await tools["assign_worker"](worker_id=worker, card_key=card, reason="r")).startswith("OK:")
    board = await tools["get_game_state"]()
    assert "(not assigned yet)" not in board
    work = json.loads(await tools["start_work"](reason="r"))
    assert {e["worker_id"] for e in work["work_log"] if e["type"] == "work"} == {"t1", "t2", "t3", "d1", "d2", "a1", "a2"}


async def test_board_after_start_work_says_no_more_pulls(db_session, user):
    _, _, tools = await _setup(db_session, user)
    await tools["assign_worker"](worker_id="t1", card_key="S1", reason="Tester on test")
    assert "t1 tester -> on S1" in await tools["get_game_state"]()
    await tools["start_work"](reason="Go")

    board = await tools["get_game_state"]()
    assert "work started today: yes" in board
    assert "no more pulls or assignments; call end_day" in board
    assert "PULLS POSSIBLE RIGHT NOW" not in board


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


async def test_repeated_look_without_changes_returns_short_answer(db_session, user):
    _, ctx, tools = await _setup(db_session, user)
    assert (await tools["get_game_state"]()).startswith("DAY 9 of 35")
    assert (await tools["get_game_state"]()).startswith("Board unchanged since your last get_game_state call")
    # A failed pull changes nothing; a successful one does.
    assert (await tools["pull_card"](card_key="S11", reason="r")).startswith("ERROR")
    assert (await tools["get_game_state"]()).startswith("Board unchanged")
    assert (await tools["pull_card"](card_key="S8", reason="r")).startswith("OK")
    assert (await tools["get_game_state"]()).startswith("DAY 9 of 35")
    ctx.begin_day(10)
    assert (await tools["get_game_state"]()).startswith("DAY 9 of 35")  # a new day always shows the board
