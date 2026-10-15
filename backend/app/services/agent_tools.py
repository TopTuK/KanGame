"""
Function tools the AI agent plays with — one per human player action, plus a
read-only board view. Each tool opens its own DB session (the agent runs in a
background task that outlives any request), goes through the same logged
action wrappers as the human routes, and returns compact text for the LLM.
Engine errors are returned as text so the model can correct itself.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Annotated, Optional

from agent_framework import FunctionTool, tool
from pydantic import Field

from app.core.database import AsyncSessionLocal
from app.services import action_log, game_engine
from app.services.action_log import ACTOR_AGENT
from app.services.agent_prompts import board_text


@dataclass
class RunContext:
    run_id: uuid.UUID
    game_id: uuid.UUID
    user_id: uuid.UUID
    day_call_limit: int
    cancel: asyncio.Event = field(default_factory=asyncio.Event)
    day: int = 0
    day_calls: int = 0
    total_calls: int = 0
    day_ended: bool = False
    last_modal: Optional[dict] = None
    # Bumped by every successful change to the board; lets get_game_state answer
    # "unchanged" instead of re-sending the whole board into the context.
    board_version: int = 0
    seen_version: Optional[int] = None

    def begin_day(self, day: int) -> None:
        self.day = day
        self.day_calls = 0
        self.day_ended = False
        self.board_version = 0
        self.seen_version = None


def _dump(data) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _gate(ctx: RunContext, mutating: bool) -> Optional[str]:
    """Count the call; return a STOP message when the agent must stop calling tools."""
    ctx.day_calls += 1
    ctx.total_calls += 1
    if ctx.cancel.is_set():
        return "STOP: the run was cancelled by the user. Do not call any more tools."
    if ctx.day_calls > ctx.day_call_limit:
        return "STOP: tool-call limit for this day reached. Write your note for the day now."
    if mutating and ctx.day_ended:
        return "STOP: the day is already over. Write your note for the day now."
    return None


async def _resolve_card(db, ctx: RunContext, card_key: str) -> tuple[Optional[uuid.UUID], Optional[str]]:
    game = await game_engine.get_game(db, ctx.game_id, ctx.user_id)
    if not game:
        return None, "Game not found"
    key = (card_key or "").strip().upper()
    card = next((c for c in game.cards if c.card_key == key and c.column not in ("hidden", "removed")), None)
    if not card:
        return None, f"Unknown card '{card_key}'. Use a key shown by get_game_state (e.g. S14, F2, E1)."
    return card.id, None


def make_tools(ctx: RunContext) -> list[FunctionTool]:

    async def get_game_state() -> str:
        """Show the current board: cards grouped by column (with work left in their current stage
        and who works on them), WIP usage per stage, active and unavailable workers, and the
        pulls that are possible right now."""
        if stop := _gate(ctx, mutating=False):
            return stop
        unchanged = ctx.seen_version == ctx.board_version
        async with AsyncSessionLocal() as db:
            game = await game_engine.get_game(db, ctx.game_id, ctx.user_id)
            if not game:
                return "ERROR: game not found"
            board = board_text(game)
            await action_log.record(
                db, ctx.game_id, game.current_day, ACTOR_AGENT, "get_game_state",
                result={"ok": True, "unchanged": unchanged}, run_id=ctx.run_id,
            )
        if unchanged:
            return ("Board unchanged since your last get_game_state call (no successful pull, assignment or "
                    "start_work since). Act on that board instead of looking again.")
        ctx.seen_version = ctx.board_version
        return board

    async def pull_card(
        card_key: Annotated[str, Field(description="Key of the card to pull one column to the right, e.g. 'S14'.")],
        reason: Annotated[str, Field(description="One short sentence: why pull this card now.")],
    ) -> str:
        """Pull a card one column to the right (e.g. ready -> analysis, test_done -> deployed). Respects WIP limits."""
        if stop := _gate(ctx, mutating=True):
            return stop
        async with AsyncSessionLocal() as db:
            card_id, err = await _resolve_card(db, ctx, card_key)
            if err:
                return f"ERROR: {err}"
            game, error, result = await action_log.logged_pull_card(
                db, ctx.game_id, card_id, ctx.user_id, actor=ACTOR_AGENT, reason=reason, run_id=ctx.run_id,
            )
        if error:
            return f"ERROR: {error}"
        ctx.board_version += 1
        return f"OK: {card_key.upper()} moved to {result.get('to_col')}."

    async def assign_worker(
        worker_id: Annotated[str, Field(description="Worker id, e.g. 'a1' (analyst), 'd2' (developer), 't1' (tester).")],
        card_key: Annotated[str, Field(description="Key of a card in a working column (analysis/development/test or exp_*).")],
        reason: Annotated[str, Field(description="One short sentence: why this worker on this card.")],
    ) -> str:
        """Assign a worker to a card for today. Repeating the same assignment unassigns the worker."""
        if stop := _gate(ctx, mutating=True):
            return stop
        async with AsyncSessionLocal() as db:
            card_id, err = await _resolve_card(db, ctx, card_key)
            if err:
                return f"ERROR: {err}"
            game, error, result = await action_log.logged_assign_worker(
                db, ctx.game_id, (worker_id or "").strip().lower(), card_id, ctx.user_id,
                actor=ACTOR_AGENT, reason=reason, run_id=ctx.run_id,
            )
        if error:
            return f"ERROR: {error}"
        ctx.board_version += 1
        outcome = result.get("outcome")
        if outcome == "unassigned":
            return f"OK: {worker_id} unassigned from {card_key.upper()} (it was already assigned there)."
        if outcome == "reassigned":
            return f"OK: {worker_id} moved from {result.get('previous_card')} to {card_key.upper()}."
        return f"OK: {worker_id} assigned to {card_key.upper()}."

    async def start_work(
        reason: Annotated[str, Field(description="One short sentence: why you are ready to start work.")],
    ) -> str:
        """Roll the dice: every assigned worker works on their card. Returns the work log and revenue."""
        if stop := _gate(ctx, mutating=True):
            return stop
        async with AsyncSessionLocal() as db:
            game, error, log, result = await action_log.logged_start_work(
                db, ctx.game_id, ctx.user_id, actor=ACTOR_AGENT, reason=reason, run_id=ctx.run_id,
            )
        if not game:
            return "ERROR: game not found"
        if error:
            return f"ERROR: {error}"
        ctx.board_version += 1
        return _dump({
            "work_log": log,
            "daily_revenue": result.get("daily_revenue"),
            "total_revenue": result.get("total_revenue"),
        })

    async def end_day(
        reason: Annotated[str, Field(description="One short sentence: why the day is complete.")],
    ) -> str:
        """End the day. Reveals the day's event (team changes, blockers, WIP changes, new urgent work)."""
        if stop := _gate(ctx, mutating=True):
            return stop
        async with AsyncSessionLocal() as db:
            game, error, modal, result = await action_log.logged_end_day(
                db, ctx.game_id, ctx.user_id, actor=ACTOR_AGENT, reason=reason, run_id=ctx.run_id,
            )
        if not game:
            return "ERROR: game not found"
        if error:
            return f"ERROR: {error}"
        ctx.day_ended = True
        ctx.board_version += 1
        ctx.last_modal = modal
        return _dump({
            "event": modal.get("title"),
            "description": modal.get("description"),
            "overdue_removed": modal.get("overdue"),
            "total_revenue": result.get("total_revenue"),
            "game_status": result.get("status"),
            "next": "Day over. Write your short note for the day now; do not call more tools.",
        })

    return [
        tool(get_game_state, name="get_game_state"),
        tool(pull_card, name="pull_card"),
        tool(assign_worker, name="assign_worker"),
        tool(start_work, name="start_work"),
        tool(end_day, name="end_day"),
    ]
