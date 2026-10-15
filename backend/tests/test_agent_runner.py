"""
Agent runner end-to-end with a scripted fake agent in place of the LLM:
the fake calls the real tools, so games, logs and run rows are all real.
"""
import json
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from agent_framework import Message

from app.models.agent import AgentRun, AgentRunStatus, GameAction
from app.models.game import Game, GameStatus
from app.services import agent_runner
from app.services import game_engine as ge
from app.services.agent_tools import RunContext

SECRET = "sk-test-secret-123"
STAGE_FOR_ROLE = {"analyst": "analysis", "developer": "development", "tester": "test"}
WORKING = ("analysis", "development", "test", "exp_analysis", "exp_development", "exp_test")


async def _structured_state() -> dict:
    """The scripted player reads the same snapshot the action log stores (each test has one active agent game)."""
    from app.core.database import AsyncSessionLocal
    from app.services.action_log import snapshot

    async with AsyncSessionLocal() as db:
        game_id, user_id = (await db.execute(
            select(Game.id, Game.user_id).where(Game.is_agent.is_(True), Game.status == GameStatus.active)
        )).one()
        return snapshot(await ge.get_game(db, game_id, user_id))


async def play_day(tools, prompt):
    """A simple human-like strategy: deploy, pull right-to-left, staff every worker, work, end day."""
    await tools["get_game_state"]()
    state = await _structured_state()
    for col in ("test_done", "dev_done", "analysis_done", "ready"):
        for card in [c for c in state["cards"] if c["col"] == col]:
            await tools["pull_card"](card_key=card["key"], reason=f"Pull from {col}")
    state = await _structured_state()
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
    """Receives the whole conversation like the real Agent; the script sees today's prompt."""

    def __init__(self, tools, script, on_run=None):
        self.tools = {t.name: t.func for t in tools}
        self.script = script
        self.on_run = on_run
        self.prompts: list[str] = []
        self.conversations: list[list] = []

    async def run(self, messages):
        prompt = messages[-1].text
        self.prompts.append(prompt)
        self.conversations.append(list(messages))
        if self.on_run:
            self.on_run(len(self.prompts))
        text = await self.script(self.tools, prompt)
        return SimpleNamespace(
            text=text,
            usage_details={"input_token_count": 100, "output_token_count": 20},
            messages=[Message("assistant", [text])],
        )


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


async def test_agent_leaderboard_lists_finished_runs_with_model(db_session, user, api_client):
    from datetime import datetime
    from app.models.user import User

    other = User(id=uuid.uuid4(), sub="bot-owner", name="Owner Two", username="owner2")
    db_session.add(other)
    await db_session.commit()

    async def finished(owner, name, model, revenue, run_status=AgentRunStatus.completed, done=True):
        game = await ge.create_game(db_session, f"🤖 {name}", name, owner.id, is_agent=True)
        game.status = GameStatus.completed if done else GameStatus.active
        game.total_revenue = revenue
        db_session.add(AgentRun(
            id=uuid.uuid4(), user_id=owner.id, game_id=game.id, name=name, model=model,
            base_url="http://private-llm.internal/v1", status=run_status, finished_at=datetime.utcnow(),
        ))
        await db_session.commit()

    await finished(user, "Nano", "openai/gpt-4.1-nano", 300000)
    await finished(other, "Big", "anthropic/claude-opus", 650000)
    await finished(user, "Quit", "m", 999999, run_status=AgentRunStatus.cancelled, done=False)
    await finished(other, "Broke", "m", 888888, run_status=AgentRunStatus.failed, done=False)
    human = await ge.create_game(db_session, "Human", "Alice", user.id)
    human.status, human.total_revenue = GameStatus.completed, 777777
    await db_session.commit()

    board = await ge.get_top_agent_runs(db_session)
    assert [(e["agent_name"], e["model"], e["owner"], e["profit"]) for e in board] == [
        ("Big", "anthropic/claude-opus", "owner2", 650000),
        ("Nano", "openai/gpt-4.1-nano", "tester", 300000),
    ]
    assert len(await ge.get_top_agent_runs(db_session, limit=1)) == 1
    # The human leaderboard stays human-only.
    assert [e["profit"] for e in await ge.get_top_leaderboard(db_session)] == [777777]

    res = await api_client.get("/api/leaderboard/agents")
    assert res.status_code == 200 and res.json()[0]["model"] == "anthropic/claude-opus"
    assert "private-llm" not in res.text  # base URLs are never exposed


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
        "default_base_url": "https://routerai.ru/api/v1",
        "default_model": "openai/gpt-4.1-nano",
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
    assert body["base_url"] == "https://routerai.ru/api/v1" and body["model"] == "openai/gpt-4.1-nano"
    assert started[0][3:] == (SECRET, "https://routerai.ru/api/v1", "openai/gpt-4.1-nano")
    assert SECRET not in res.text


def test_openrouter_gets_attribution_headers():
    assert agent_runner._provider_headers("https://openrouter.ai/api/v1")["X-Title"] == "KanGame"
    assert agent_runner._provider_headers("https://api.openai.com/v1") is None


# --- concurrency & cancellation --------------------------------------------

async def test_concurrent_run_requests_start_only_one_run(api_client, db_session, user, monkeypatch):
    import asyncio
    started = []
    monkeypatch.setattr(agent_runner, "start", lambda *args: started.append(args))
    payload = {"name": "Bot", "base_url": "https://api.example.com/v1", "model": "m", "api_key": SECRET}

    responses = await asyncio.gather(*(api_client.post("/api/agent/runs", json=payload) for _ in range(4)))

    assert sorted(r.status_code for r in responses) == [201, 409, 409, 409]
    assert len(started) == 1
    user_id = user.id  # read before expiring: lazy loads can't run here
    db_session.expire_all()
    runs = (await db_session.execute(select(AgentRun).where(AgentRun.user_id == user_id))).scalars().all()
    agent_games = (await db_session.execute(
        select(Game.id).where(Game.user_id == user_id, Game.is_agent.is_(True))
    )).scalars().all()
    assert len(runs) == 1 and agent_games == [runs[0].game_id]  # losers' games were cleaned up


async def test_database_rejects_second_active_run_for_user(db_session, user):
    from sqlalchemy.exc import IntegrityError
    await _new_run(db_session, user)
    with pytest.raises(IntegrityError):
        await _new_run(db_session, user)


async def test_cancelled_task_is_recorded_as_failed_and_reraises(db_session, user, fake_agent):
    import asyncio
    game, run, ctx = await _new_run(db_session, user)
    entered = asyncio.Event()

    async def hang(tools, prompt):
        entered.set()
        await asyncio.Event().wait()

    fake_agent(hang)
    task = asyncio.create_task(agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake"))
    await asyncio.wait_for(entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    _, r, rows = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.failed and r.finished_at
    assert r.error == "interrupted: agent task was cancelled"
    assert rows[-1].action == "run_event" and rows[-1].result["event"] == "failed"


# --- timeouts, retries and memory ------------------------------------------------

class APITimeoutError(Exception):
    """Same class name as openai's, which is what the runner classifies as transient."""


@pytest.fixture
def no_backoff(monkeypatch):
    monkeypatch.setattr(agent_runner, "_retry_delay", lambda exc, attempt: 0)


def _events(rows, name):
    return [x for x in rows if x.action == "run_event" and x.result.get("event") == name]


async def test_transient_failure_retries_with_a_fresh_board(db_session, user, fake_agent, no_backoff):
    game, run, ctx = await _new_run(db_session, user, total_days=9)
    calls = {"n": 0}

    async def flaky(tools, prompt):
        calls["n"] += 1
        if calls["n"] == 1:
            await tools["pull_card"](card_key="S8", reason="Free capacity in development")
            raise APITimeoutError("model did not answer")
        return await play_day(tools, prompt)

    holder = fake_agent(flaky)
    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    g, r, rows = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.completed and g.status == GameStatus.completed
    retries = _events(rows, "llm_retry")
    assert len(retries) == 1 and retries[0].result["error"] == "APITimeoutError"
    first, second = holder["agent"].prompts
    assert not first.startswith(agent_runner.RETRY_NOTE)
    assert second.startswith(agent_runner.RETRY_NOTE)
    # The retry sees the pull the interrupted attempt already made.
    assert "S8: analysis_done -> development" in first
    assert "S8: analysis_done -> development" not in second


async def test_hanging_model_hits_day_timeout_then_retries(db_session, user, fake_agent, no_backoff, monkeypatch):
    import asyncio
    from app.core.config import settings
    monkeypatch.setattr(settings, "AGENT_DAY_TIMEOUT_SECONDS", 2)  # ample for a normal simulated day
    game, run, ctx = await _new_run(db_session, user, total_days=9)
    calls = {"n": 0}

    async def hang_once(tools, prompt):
        calls["n"] += 1
        if calls["n"] == 1:
            await asyncio.Event().wait()
        return await play_day(tools, prompt)

    fake_agent(hang_once)
    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    _, r, rows = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.completed
    retries = _events(rows, "llm_retry")
    assert retries and retries[0].result["error"] == "TimeoutError" and retries[0].day == 9


async def test_run_fails_when_retries_are_exhausted(db_session, user, fake_agent, no_backoff, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "AGENT_LLM_RETRIES", 2)
    game, run, ctx = await _new_run(db_session, user)

    async def down(tools, prompt):
        raise APITimeoutError("still down")

    holder = fake_agent(down)
    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    _, r, rows = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.failed and "APITimeoutError" in r.error
    assert [x.result["attempt"] for x in _events(rows, "llm_retry")] == [1, 2]
    assert len(holder["agent"].prompts) == 3


async def test_permanent_error_is_not_retried(db_session, user, fake_agent, no_backoff):
    game, run, ctx = await _new_run(db_session, user)

    class AuthenticationError(Exception):
        pass

    async def bad_key(tools, prompt):
        raise AuthenticationError("invalid key")

    fake_agent(bad_key)
    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    _, r, rows = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.failed and not _events(rows, "llm_retry")


async def test_error_after_end_day_does_not_fail_the_run(db_session, user, fake_agent, no_backoff):
    game, run, ctx = await _new_run(db_session, user, total_days=10)

    async def play_then_drop(tools, prompt):
        await play_day(tools, prompt)
        raise APITimeoutError("connection dropped while writing the note")

    holder = fake_agent(play_then_drop)
    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    g, r, rows = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.completed and g.status == GameStatus.completed
    assert len(_events(rows, "llm_error_after_day_end")) == 2
    assert len(holder["agent"].prompts) == 2  # no day was replayed


def test_retry_delay_backs_off_and_honours_retry_after():
    class RateLimitError(Exception):
        def __init__(self, retry_after):
            super().__init__("slow down")
            self.response = SimpleNamespace(headers={"retry-after": retry_after})

    assert agent_runner._retry_delay(RateLimitError("7"), 0) == 7
    first = agent_runner._retry_delay(APITimeoutError(), 0)
    third = agent_runner._retry_delay(APITimeoutError(), 2)
    assert 2 <= first <= 4 and 9 <= third <= 15
    assert agent_runner._retry_delay(APITimeoutError(), 10) <= agent_runner.RETRY_MAX_DELAY * 1.2


def test_transient_classification():
    class InternalServerError(Exception):
        pass

    class Wrapped(Exception):
        pass

    class BadRequestError(Exception):
        pass

    def chained(inner):
        try:
            raise inner
        except Exception as exc:
            try:
                raise Wrapped("framework wrapper") from exc
            except Wrapped as wrapped:
                return wrapped

    assert agent_runner._is_transient(chained(InternalServerError()))
    assert agent_runner._is_transient(chained(TimeoutError()))
    assert not agent_runner._is_transient(chained(BadRequestError()))
    assert not agent_runner._is_transient(ValueError("bug"))
    status_503 = Exception("unavailable")
    status_503.status_code = 503
    assert agent_runner._is_transient(status_503)


async def test_conversation_is_kept_across_days(db_session, user, fake_agent):
    game, run, ctx = await _new_run(db_session, user, total_days=11)
    holder = fake_agent(play_day)

    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    # Each day adds its prompt and the agent's reply to the conversation.
    assert [len(c) for c in holder["agent"].conversations] == [1, 3, 5]
    day3 = holder["agent"].conversations[2]
    assert day3[0].text.startswith("Day 9 of 11")
    assert day3[1].role == "assistant" and day3[1].text.startswith("Played: Day 9 of 11")
    assert day3[2].text.startswith("Day 10 of 11")


async def test_context_is_summarized_when_it_grows(db_session, user, fake_agent, monkeypatch):
    from app.core.config import settings
    # A tiny window (instructions alone are ~4.3k tokens) so a few days of boards cross the threshold.
    monkeypatch.setattr(settings, "AGENT_CONTEXT_WINDOW_TOKENS", 12_000)
    monkeypatch.setattr(settings, "AGENT_CONTEXT_SUMMARY_THRESHOLD", 0.5)
    monkeypatch.setattr(settings, "AGENT_CONTEXT_KEEP_RECENT_DAYS", 1)
    seen = []

    async def summarize(agent, instructions, transcript):
        seen.append(transcript)
        return "SUMMARY: deployed S1-S3, keep testers on test."

    monkeypatch.setattr(agent_runner, "summarize_with_llm", summarize)
    game, run, ctx = await _new_run(db_session, user, total_days=14)
    holder = fake_agent(play_day)

    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    _, r, rows = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.completed
    events = _events(rows, "context_summarized")
    assert events and not events[0].result["fallback"]
    assert events[0].result["tokens_after"] < events[0].result["tokens_before"]
    assert "=== Day 9 ===" in seen[0] and "Current board" not in seen[0]
    last = holder["agent"].conversations[-1]
    assert last[0].text.startswith("Game memory (your own summary of days 9-")
    assert "SUMMARY: deployed S1-S3" in last[0].text


async def test_summarizer_failure_falls_back_to_the_journal(db_session, user, fake_agent, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "AGENT_CONTEXT_WINDOW_TOKENS", 12_000)
    monkeypatch.setattr(settings, "AGENT_CONTEXT_SUMMARY_THRESHOLD", 0.5)
    monkeypatch.setattr(settings, "AGENT_CONTEXT_KEEP_RECENT_DAYS", 1)

    async def broken(agent, instructions, transcript):
        raise APITimeoutError("summarizer down")

    monkeypatch.setattr(agent_runner, "summarize_with_llm", broken)
    game, run, ctx = await _new_run(db_session, user, total_days=14)
    holder = fake_agent(play_day)

    await agent_runner.run_agent(ctx, api_key=SECRET, base_url="http://fake", model="fake")

    _, r, rows = await _reload(db_session, game, run)
    assert r.status == AgentRunStatus.completed
    events = _events(rows, "context_summarized")
    assert events and events[0].result["fallback"] is True
    memory_text = holder["agent"].conversations[-1][0].text
    assert "Day 9: event 'First Day Complete'." in memory_text and "Total revenue" in memory_text
