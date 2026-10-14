"""
Background runner for AI agent playthroughs (Microsoft Agent Framework).

One asyncio task per run plays the game day by day: each day is a fresh
`agent.run(day_prompt)` in which the model calls the player tools itself. If
the model forgets to start work or end the day, a logged `system` safety net
does it so the game always progresses. The provider API key lives only in
this task's memory (inside the client) and is redacted from error messages.
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.agent import AgentRun, AgentRunStatus, ACTIVE_RUN_STATUSES
from app.models.game import GameStatus
from app.services import action_log, game_engine
from app.services.action_log import ACTOR_AGENT, ACTOR_SYSTEM
from app.services.agent_prompts import KANBAN_INSTRUCTIONS, day_prompt
from app.services.agent_tools import RunContext, make_tools

logger = logging.getLogger(__name__)

LLM_RETRIES = 2
_RETRY_DELAYS = (3, 10)

_runs: dict[uuid.UUID, RunContext] = {}
_tasks: set[asyncio.Task] = set()


class RunCancelled(Exception):
    pass


def _provider_headers(base_url: str) -> dict[str, str] | None:
    """OpenRouter's optional app attribution headers (shown in its usage dashboard)."""
    if "openrouter.ai" in base_url:
        return {"HTTP-Referer": settings.BASE_URL, "X-Title": "KanGame"}
    return None


def build_agent(model: str, api_key: str, base_url: str, tools: list, max_calls: int) -> Any:
    """Single construction point for the Agent Framework objects (tests replace this)."""
    from agent_framework import Agent
    from agent_framework.openai import OpenAIChatCompletionClient

    client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        base_url=base_url,
        default_headers=_provider_headers(base_url),
        function_invocation_configuration={
            "max_function_calls": max_calls,
            "max_iterations": max_calls,
        },
    )
    return Agent(client=client, name="KanbanAgent", instructions=KANBAN_INSTRUCTIONS, tools=tools)


# --- registry ------------------------------------------------------------

def is_running(run_id: uuid.UUID) -> bool:
    return run_id in _runs


def cancel(run_id: uuid.UUID) -> bool:
    ctx = _runs.get(run_id)
    if not ctx:
        return False
    ctx.cancel.set()
    return True


def start(run_id: uuid.UUID, game_id: uuid.UUID, user_id: uuid.UUID, api_key: str, base_url: str, model: str) -> None:
    ctx = RunContext(
        run_id=run_id, game_id=game_id, user_id=user_id,
        day_call_limit=settings.AGENT_DAY_TOOL_CALL_LIMIT,
    )
    _runs[run_id] = ctx
    task = asyncio.create_task(run_agent(ctx, api_key=api_key, base_url=base_url, model=model))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def fail_interrupted_runs(db: AsyncSession) -> int:
    """At startup no task can be alive, so any active run was interrupted by a restart."""
    result = await db.execute(
        update(AgentRun)
        .where(AgentRun.status.in_(ACTIVE_RUN_STATUSES))
        .values(status=AgentRunStatus.failed, error="interrupted by server restart", finished_at=datetime.utcnow())
    )
    await db.commit()
    return result.rowcount or 0


# --- helpers ---------------------------------------------------------------

async def _update_run(run_id: uuid.UUID, **values) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(update(AgentRun).where(AgentRun.id == run_id).values(**values))
        await db.commit()


async def _load_game(ctx: RunContext):
    async with AsyncSessionLocal() as db:
        return await game_engine.get_game(db, ctx.game_id, ctx.user_id)


async def _record(ctx: RunContext, day: int, actor: str, action: str, **kwargs) -> None:
    async with AsyncSessionLocal() as db:
        await action_log.record(db, ctx.game_id, day, actor, action, run_id=ctx.run_id, **kwargs)


def _deadlines(game) -> list[str]:
    out = []
    for c in sorted(game.cards, key=lambda c: c.due_day or 0):
        if c.card_type in ("fixed_date", "expedite") and c.due_day and c.due_day >= game.current_day \
                and c.column not in ("hidden", "removed", "deployed", "exp_deployed"):
            out.append(f"{c.card_key} due end of day {c.due_day} (value {c.val}, now in {c.column})")
    return out


def _redact(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text


def _is_transient(exc: BaseException) -> bool:
    names = set()
    seen = exc
    while seen is not None and len(names) < 10:
        names.add(type(seen).__name__)
        seen = seen.__cause__ or seen.__context__
    if names & {"AuthenticationError", "PermissionDeniedError", "NotFoundError", "BadRequestError"}:
        return False
    return bool(names & {
        "APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError",
        "TimeoutError", "ConnectError", "ReadTimeout",
    })


def _usage(response) -> tuple[int, int]:
    usage = getattr(response, "usage_details", None) or {}
    get = usage.get if isinstance(usage, dict) else (lambda k, d=None: getattr(usage, k, d))
    return int(get("input_token_count", 0) or 0), int(get("output_token_count", 0) or 0)


async def _run_day(agent, ctx: RunContext, prompt: str):
    attempt = 0
    while True:
        try:
            return await agent.run(prompt)
        except Exception as exc:  # noqa: BLE001 — classified below
            if ctx.day_ended or attempt >= LLM_RETRIES or not _is_transient(exc):
                raise
            delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
            attempt += 1
            await _record(
                ctx, ctx.day, ACTOR_SYSTEM, "run_event",
                result={"ok": False, "event": "llm_retry", "attempt": attempt, "error": type(exc).__name__},
            )
            await asyncio.sleep(delay)


async def _safety_net(ctx: RunContext, day: int) -> None:
    """Finish the day on the agent's behalf if it stopped early — logged as `system`."""
    game = await _load_game(ctx)
    if not game or game.status != GameStatus.active or game.current_day != day:
        return
    async with AsyncSessionLocal() as db:
        if not game.work_done:
            await action_log.logged_start_work(
                db, ctx.game_id, ctx.user_id, actor=ACTOR_SYSTEM,
                reason="Safety net: the agent ended its turn without starting work.", run_id=ctx.run_id,
            )
        _, error, modal, _ = await action_log.logged_end_day(
            db, ctx.game_id, ctx.user_id, actor=ACTOR_SYSTEM,
            reason="Safety net: the agent ended its turn without ending the day.", run_id=ctx.run_id,
        )
    if not error:
        ctx.last_modal = modal


# --- main loop -------------------------------------------------------------

async def run_agent(ctx: RunContext, api_key: str, base_url: str, model: str) -> None:
    secret = api_key
    # Pessimistic default: only a normal end of the day loop marks the run completed.
    status, error = AgentRunStatus.failed, "aborted"
    llm_turns = in_tokens = out_tokens = 0
    start_day = 0
    try:
        start_game = await _load_game(ctx)
        start_day = start_game.current_day if start_game else 0
        await _update_run(ctx.run_id, status=AgentRunStatus.running, started_at=datetime.utcnow())
        await _record(ctx, start_day, ACTOR_SYSTEM, "run_event",
                      result={"ok": True, "event": "started", "model": model, "base_url": base_url})
        agent = build_agent(model, api_key, base_url, make_tools(ctx), settings.AGENT_DAY_TOOL_CALL_LIMIT + 5)
        api_key = None  # the client holds the only copy from here on

        note: Optional[str] = None
        async with asyncio.timeout(settings.AGENT_MAX_RUN_MINUTES * 60):
            while True:
                if ctx.cancel.is_set():
                    raise RunCancelled()
                game = await _load_game(ctx)
                if not game:
                    raise RuntimeError("game disappeared")
                if game.status != GameStatus.active:
                    break

                day = game.current_day
                ctx.begin_day(day)
                prompt = day_prompt(day, game.total_days, ctx.last_modal, note, _deadlines(game))
                response = await _run_day(agent, ctx, prompt)

                note = (getattr(response, "text", "") or "").strip()
                i, o = _usage(response)
                llm_turns += 1
                in_tokens += i
                out_tokens += o
                await _record(
                    ctx, day, ACTOR_AGENT, "day_summary", reason=note or None,
                    result={"ok": True, "tool_calls": ctx.day_calls, "input_tokens": i, "output_tokens": o},
                )
                await _update_run(ctx.run_id, tool_calls=ctx.total_calls, llm_turns=llm_turns,
                                  input_tokens=in_tokens, output_tokens=out_tokens)
                if ctx.cancel.is_set():
                    raise RunCancelled()
                await _safety_net(ctx, day)
                after = await _load_game(ctx)
                if after and after.status == GameStatus.active and after.current_day == day:
                    raise RuntimeError(f"day {day} could not be completed")
        status, error = AgentRunStatus.completed, None
    except RunCancelled:
        status, error = AgentRunStatus.cancelled, None
    except asyncio.CancelledError:
        # The task itself was cancelled (e.g. server shutdown). CancelledError is
        # not an Exception, so record the outcome here, then re-raise so asyncio
        # sees the cancellation; `finally` still finalizes the run row.
        if ctx.cancel.is_set():
            status, error = AgentRunStatus.cancelled, None
        else:
            status, error = AgentRunStatus.failed, "interrupted: agent task was cancelled"
        raise
    except TimeoutError:
        status, error = AgentRunStatus.failed, f"timeout after {settings.AGENT_MAX_RUN_MINUTES} minutes"
    except Exception as exc:  # noqa: BLE001 — any failure ends the run
        if ctx.cancel.is_set():
            status, error = AgentRunStatus.cancelled, None
            return
        logger.exception("Agent run %s failed", ctx.run_id)
        status, error = AgentRunStatus.failed, _redact(f"{type(exc).__name__}: {exc}", secret)[:2000]
    finally:
        secret = None
        _runs.pop(ctx.run_id, None)
        try:
            game = await _load_game(ctx)
            await _record(
                ctx, game.current_day if game else start_day, ACTOR_SYSTEM, "run_event",
                result={"ok": status == AgentRunStatus.completed, "event": status.value, "error": error,
                        "total_revenue": game.total_revenue if game else None},
            )
            await _update_run(
                ctx.run_id, status=status, error=error, finished_at=datetime.utcnow(),
                tool_calls=ctx.total_calls, llm_turns=llm_turns,
                input_tokens=in_tokens, output_tokens=out_tokens,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Could not finalize agent run %s", ctx.run_id)
