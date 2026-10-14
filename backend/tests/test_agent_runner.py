"""
Agent runner end-to-end with a scripted fake agent in place of the LLM:
the fake calls the real tools, so games, logs and run rows are all real.
"""
import json
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.agent import AgentRun, AgentRunStatus, GameAction
from app.models.game import Game, GameStatus
from app.services import agent_runner
from app.services import game_engine as ge
from app.services.agent_tools import RunContext

SECRET = "sk-test-secret-123"
STAGE_FOR_ROLE = {"analyst": "analysis", "developer": "development", "tester": "test"}
WORKING = ("analysis", "development", "test", "exp_analysis", "exp_development", "exp_test")


async def play_day(tools, prompt):
    """A simple human-like strategy: deploy, pull right-to-left, staff every worker, work, end day."""
    state = json.loads(await tools["get_game_state"]())
    for col in ("test_done", "dev_done", "analysis_done", "ready"):
        for card in [c for c in state["cards"] if c["col"] == col]:
            await tools["pull_card"](card_key=card["key"], reason=f"Pull from {col}")
    state = json.loads(await tools["get_game_state"]())
    working = [c for c in state["cards"] if c["col"] in WORKING and not c.get("blocked")]
    for w in (w for w in state["workers"] if w["active"]):
        own = [c for c in working if c["col"].endswith(STAGE_FOR_ROLE[w["type"]])]
        target = (own or working or [None])[0]
        if target:
            await tools["assign_worker"](worker_id=w["id"], card_key=target["key"], reason="Specialist first")
    await tools["start_work"](reason="Everyone staffed")
    await tools["end_day"](reason="Work done")
    return f"Played: {prompt.splitlines()[0]}"


async def only_look(tools, prompt):
    await tools["get_game_state"]()
    return "I forgot to press the buttons."


class FakeAgent:
    def __init__(self, tools, script, on_run=None):
        self.tools = {t.name: t.func for t in tools}
        self.script = script
        self.on_run = on_run
        self.prompts: list[str] = []

    async def run(self, prompt):
        self.prompts.append(prompt)
        if self.on_run:
            self.on_run(len(self.prompts))
        text = await self.script(self.tools, prompt)
        return SimpleNamespace(text=text, usage_details={"input_token_count": 100, "output_token_count": 20})


@pytest.fixture
def fake_agent(monkeypatch):
    holder = {}

    def install(script, on_run=None):
        def build(model, api_key, base_url, tools, max_calls):
            holder["api_key"] = api_key
            holder["agent"] = FakeAgent(tools, script, on_run)
            return holder["agent"]
        monkeypatch.setattr(agent_runner, "build_agent", build)
        return holder

    return install


async def _new_run(db_session, user, total_days=12):
    game = await ge.create_game(db_session, "🤖 Bot", "Bot", user.id, total_days=total_days, is_agent=True)
    run = AgentRun(id=uuid.uuid4(), user_id=user.id, game_id=game.id, name="Bot", model="fake", base_url="http://fake")
    db_session.add(run)
    await db_session.commit()
    ctx = RunContext(run_id=run.id, game_id=game.id, user_id=user.id, day_call_limit=60)
    return game, run, ctx


async def _reload(db_session, game, run):
    game_id, run_id = game.id, run.id  # read before expiring: lazy loads can't run here
    db_session.expire_all()
    g = await db_session.get(Game, game_id)
    r = await db_session.get(AgentRun, run_id)
    rows = (await db_session.execute(
        select(GameAction).where(GameAction.game_id == game_id).order_by(GameAction.seq)
    )).scalars().all()
    return g, r, list(rows)


async def test_happy_path_plays_to_completion_and_logs_everything(db_session, user, fake_agent):
    game, run, ctx = await _new_run(db_session, user, total_days=12)
    holder = fake_agent(play_day)

    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    g, r, rows = await _reload(db_session, game, run)
    assert g.status == GameStatus.completed and g.current_day == 12
    assert r.status == AgentRunStatus.completed and r.started_at and r.finished_at and r.error is None
    assert r.llm_turns == 4 and r.input_tokens == 400 and r.tool_calls > 0
    assert holder["api_key"] == SECRET

    summaries = [x for x in rows if x.action == "day_summary"]
    assert [x.day for x in summaries] == [9, 10, 11, 12]
    assert all(x.reason.startswith("Played: Day") for x in summaries)
    assert not any(x.actor == "system" and x.action in ("start_work", "end_day") for x in rows)
    assert [x.result["event"] for x in rows if x.action == "run_event"] == ["started", "completed"]
    assert all(x.reason for x in rows if x.action in ("pull_card", "assign_worker", "start_work", "end_day"))
    # Day 10 prompt carries the end-of-day event a human would have read, plus the agent's own note.
    assert "First Day Complete" in holder["agent"].prompts[1]
    assert "Your note from yesterday: Played: Day 9" in holder["agent"].prompts[1]


async def test_safety_net_finishes_days_the_agent_left_open(db_session, user, fake_agent):
    game, run, ctx = await _new_run(db_session, user, total_days=10)
    fake_agent(only_look)

    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    g, r, rows = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.completed and g.status == GameStatus.completed
    system = [(x.day, x.action) for x in rows if x.actor == "system" and x.action != "run_event"]
    assert system == [(9, "start_work"), (9, "end_day"), (10, "start_work"), (10, "end_day")]


async def test_cancel_mid_run(db_session, user, fake_agent):
    game, run, ctx = await _new_run(db_session, user, total_days=20)
    fake_agent(play_day, on_run=lambda n: ctx.cancel.set() if n == 2 else None)

    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    g, r, _ = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.cancelled and r.finished_at
    assert g.status == GameStatus.active and g.current_day == 10


async def test_failure_is_recorded_without_leaking_the_api_key(db_session, user, fake_agent):
    game, run, ctx = await _new_run(db_session, user)

    async def boom(tools, prompt):
        raise ValueError(f"provider rejected key {SECRET}")

    fake_agent(boom)
    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    _, r, rows = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.failed
    assert "provider rejected key ***" in r.error
    dumped = json.dumps([[x.arguments, x.result, x.reason, x.state] for x in rows], default=str)
    assert SECRET not in dumped and SECRET not in (r.error or "")


async def test_leaderboard_excludes_agent_games(db_session, user):
    from app.models.user import User

    bot_owner = User(id=uuid.uuid4(), sub="bot-owner", name="BotOwner", username="botowner")
    db_session.add(bot_owner)
    await db_session.commit()
    human = await ge.create_game(db_session, "Human", "Alice", user.id)
    bot = await ge.create_game(db_session, "Bot", "Bot", bot_owner.id, is_agent=True)
    for g, revenue in ((human, 1000), (bot, 999999)):
        g.status = GameStatus.completed
        g.total_revenue = revenue
    await db_session.commit()

    board = await ge.get_top_leaderboard(db_session)
    assert board == [{"name": "tester", "profit": 1000}]


async def test_fail_interrupted_runs_marks_active_runs_failed(db_session, user):
    _, run, _ = await _new_run(db_session, user)
    run_id = run.id
    assert await agent_runner.fail_interrupted_runs(db_session) == 1
    db_session.expire_all()
    r = await db_session.get(AgentRun, run_id)
    assert r.status == AgentRunStatus.failed and r.error == "interrupted by server restart"


# --- API -------------------------------------------------------------------

async def test_agent_run_api_lifecycle(api_client, db_session, monkeypatch):
    started = []
    monkeypatch.setattr(agent_runner, "start", lambda *args: started.append(args))
    payload = {"name": "GPT bot", "base_url": "https://api.example.com/v1/", "model": "gpt-x", "api_key": SECRET}

    res = await api_client.post("/api/agent/runs", json=payload)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "pending" and body["base_url"] == "https://api.example.com/v1"
    assert body["game"]["name"] == "🤖 GPT bot"
    assert SECRET not in res.text
    assert started[0][3] == SECRET  # key handed to the runner in memory only

    assert (await api_client.post("/api/agent/runs", json=payload)).status_code == 409

    detail = (await api_client.get(f"/api/agent/runs/{body['id']}")).json()
    assert [a["action"] for a in detail["actions"]] == ["day_start"]
    assert detail["actions"][0]["actor"] == "agent"
    assert (await api_client.get(f"/api/agent/runs/{body['id']}", params={"after_seq": 1})).json()["actions"] == []

    runs = (await api_client.get("/api/agent/runs")).json()
    assert [r["id"] for r in runs] == [body["id"]]

    log = await api_client.get(f"/api/agent/runs/{body['id']}/log")
    assert log.headers["content-disposition"].startswith("attachment")
    assert SECRET not in log.text

    # No live task in this test, so cancel closes the row directly.
    res = await api_client.post(f"/api/agent/runs/{body['id']}/cancel")
    assert res.json()["status"] == "cancelled"
    assert (await api_client.post("/api/agent/runs", json=payload)).status_code == 201


async def test_agent_run_api_validates_input(api_client):
    bad = {"name": "", "base_url": "ftp://x", "model": "m", "api_key": "k"}
    assert (await api_client.post("/api/agent/runs", json=bad)).status_code == 422


# --- default provider config -----------------------------------------------

async def test_config_exposes_defaults_but_never_the_server_key(api_client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "AGENT_DEFAULT_API_KEY", SECRET)

    res = await api_client.get("/api/agent/config")
    assert res.json() == {
        "enabled": True,
        "default_base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-6-luna",
        "has_server_key": True,
    }
    assert SECRET not in res.text


async def test_run_without_key_uses_server_key_only_for_default_provider(api_client, monkeypatch):
    from app.core.config import settings
    started = []
    monkeypatch.setattr(agent_runner, "start", lambda *args: started.append(args))

    # No server key configured: a key is required.
    assert (await api_client.post("/api/agent/runs", json={"name": "Bot"})).status_code == 400

    monkeypatch.setattr(settings, "AGENT_DEFAULT_API_KEY", SECRET)
    # The server key is never sent to a user-chosen endpoint.
    res = await api_client.post("/api/agent/runs", json={"name": "Bot", "base_url": "https://evil.example.com/v1"})
    assert res.status_code == 400 and not started

    res = await api_client.post("/api/agent/runs", json={"name": "Bot"})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["base_url"] == "https://openrouter.ai/api/v1" and body["model"] == "openai/gpt-6-luna"
    assert started[0][3:] == (SECRET, "https://openrouter.ai/api/v1", "openai/gpt-6-luna")
    assert SECRET not in res.text


def test_openrouter_gets_attribution_headers():
    assert agent_runner._provider_headers("https://openrouter.ai/api/v1")["X-Title"] == "KanGame"
    assert agent_runner._provider_headers("https://api.openai.com/v1") is None
