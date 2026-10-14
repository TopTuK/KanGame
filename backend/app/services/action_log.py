"""
Actor-agnostic player action log.

Human routes and the AI agent tools both perform player actions through the
`logged_*` wrappers below, so every pull / assignment / start-work / end-day
lands in `game_actions` in the same shape regardless of who made it. Rows use
stable card keys (S1, F2, ...) and worker ids (a1, d2, ...) — never UUIDs — so
human and agent behaviour can be compared with plain queries.
"""
import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.cards import PULL_MOVES, WIP_GROUPS
from app.models.agent import GameAction
from app.models.game import Game, Card
from app.services import game_engine

ACTOR_HUMAN = "human"
ACTOR_AGENT = "agent"
ACTOR_SYSTEM = "system"

_HIDDEN_COLUMNS = ("hidden", "removed")
_DEPLOYED_COLUMNS = ("deployed", "exp_deployed")


def player_actor(game: Game) -> str:
    return ACTOR_AGENT if game.is_agent else ACTOR_HUMAN


def _card_key_by_id(game: Game, card_id: Optional[str]) -> Optional[str]:
    if not card_id:
        return None
    return next((c.card_key for c in game.cards if str(c.id) == str(card_id)), None)


def _worker(game: Game, worker_id: str) -> Optional[dict]:
    return next((w for w in game.team_config.get("workers", []) if w["id"] == worker_id), None)


def _card_view(card: Card) -> dict:
    view = {"key": card.card_key, "type": card.card_type, "col": card.column}
    if card.column in _DEPLOYED_COLUMNS:
        view["deployed_day"] = card.deployed_day
    else:
        view["rem"] = [
            round(card.analysis_remaining, 1),
            round(card.dev_remaining, 1),
            round(card.test_remaining, 1),
        ]
        if card.column in PULL_MOVES:
            view["pull_to"] = PULL_MOVES[card.column]
        if card.age:
            view["age"] = card.age
    if card.is_blocked:
        view["blocked"] = card.blocker_remaining
    if card.val:
        view["val"] = card.val
    if card.due_day:
        view["due"] = card.due_day
    if card.buff:
        view["buff"] = card.buff
    return view


def snapshot(game: Game) -> dict:
    """Compact board view: what a player sees on screen at this moment."""
    workers = game.team_config.get("workers", [])
    wip = {
        key: {"limit": limit, "count": game_engine.wip_count(game, key), "lanes": WIP_GROUPS.get(key, [key])}
        for key, limit in game.wip_limits.items()
    }
    return {
        "day": game.current_day,
        "total_days": game.total_days,
        "status": _status(game),
        "work_done": game.work_done,
        "total_revenue": game.total_revenue,
        "daily_revenue": game.daily_revenue,
        "carlos_policy": game.carlos_policy,
        "lockdown": game.lockdown,
        "buffs": game.team_config.get("buffs", {}),
        "wip": wip,
        "workers": [
            {
                "id": w["id"],
                "type": w["type"],
                "active": bool(w.get("active")),
                "on": _card_key_by_id(game, w.get("assigned_card_id")),
            }
            for w in workers
        ],
        "cards": [
            _card_view(c)
            for c in sorted(game.cards, key=lambda c: c.sort_order)
            if c.column not in _HIDDEN_COLUMNS
        ],
    }


def _status(game: Game) -> str:
    return game.status.value if hasattr(game.status, "value") else str(game.status)


async def record(
    db: AsyncSession,
    game_id: uuid.UUID,
    day: int,
    actor: str,
    action: str,
    arguments: Optional[dict] = None,
    result: Optional[dict] = None,
    reason: Optional[str] = None,
    run_id: Optional[uuid.UUID] = None,
    state: Optional[dict] = None,
) -> GameAction:
    seq = (await db.execute(
        select(func.coalesce(func.max(GameAction.seq), 0)).where(GameAction.game_id == game_id)
    )).scalar_one() + 1
    entry = GameAction(
        id=uuid.uuid4(),
        game_id=game_id,
        run_id=run_id,
        actor=actor,
        seq=seq,
        day=day,
        action=action,
        arguments=arguments or {},
        result=result or {},
        reason=reason,
        state=state,
    )
    db.add(entry)
    await db.commit()
    return entry


async def record_day_start(db: AsyncSession, game: Game, run_id: Optional[uuid.UUID] = None) -> GameAction:
    """Board snapshot at the start of a day — the shared baseline of what the player saw."""
    return await record(
        db, game.id, game.current_day, player_actor(game), "day_start",
        result={"ok": True}, run_id=run_id, state=snapshot(game),
    )


# --- logged player actions ----------------------------------------------
# Each returns (game, error, result_dict). `game` is None only when the game
# doesn't exist for this user, in which case nothing is logged.

async def logged_pull_card(
    db: AsyncSession, game_id: uuid.UUID, card_id: uuid.UUID, user_id: uuid.UUID,
    actor: str, reason: Optional[str] = None, run_id: Optional[uuid.UUID] = None,
) -> tuple[Optional[Game], Optional[str], dict]:
    before = await game_engine.get_game(db, game_id, user_id)
    if not before:
        return None, "Game not found", {}
    day = before.current_day
    card = next((c for c in before.cards if c.id == card_id), None)
    card_key = card.card_key if card else None
    from_col = card.column if card else None

    game, error = await game_engine.pull_card(db, game_id, card_id, user_id)

    result: dict = {"ok": error is None}
    if error:
        result["error"] = error
    elif card:
        result["to_col"] = card.column
        result["total_revenue"] = game.total_revenue
    await record(
        db, game_id, day, actor, "pull_card",
        arguments={"card_key": card_key, "from_col": from_col},
        result=result, reason=reason, run_id=run_id,
    )
    return game, error, result


async def logged_assign_worker(
    db: AsyncSession, game_id: uuid.UUID, worker_id: str, card_id: uuid.UUID, user_id: uuid.UUID,
    actor: str, reason: Optional[str] = None, run_id: Optional[uuid.UUID] = None,
) -> tuple[Optional[Game], Optional[str], dict]:
    before = await game_engine.get_game(db, game_id, user_id)
    if not before:
        return None, "Game not found", {}
    day = before.current_day
    card = next((c for c in before.cards if c.id == card_id), None)
    card_key = card.card_key if card else None
    card_col = card.column if card else None
    worker = _worker(before, worker_id)
    previous_key = _card_key_by_id(before, worker.get("assigned_card_id")) if worker else None

    game, error = await game_engine.assign_worker(db, game_id, worker_id, card_id, user_id)

    result: dict = {"ok": error is None}
    if error:
        result["error"] = error
    else:
        now_on = _card_key_by_id(game, (_worker(game, worker_id) or {}).get("assigned_card_id"))
        if now_on is None:
            result["outcome"] = "unassigned"
        elif previous_key and previous_key != now_on:
            result["outcome"] = "reassigned"
            result["previous_card"] = previous_key
        else:
            result["outcome"] = "assigned"
    await record(
        db, game_id, day, actor, "assign_worker",
        arguments={
            "worker_id": worker_id,
            "worker_type": worker["type"] if worker else None,
            "card_key": card_key,
            "card_col": card_col,
        },
        result=result, reason=reason, run_id=run_id,
    )
    return game, error, result


async def logged_start_work(
    db: AsyncSession, game_id: uuid.UUID, user_id: uuid.UUID,
    actor: str, reason: Optional[str] = None, run_id: Optional[uuid.UUID] = None,
) -> tuple[Optional[Game], Optional[str], list[dict], dict]:
    before = await game_engine.get_game(db, game_id, user_id)
    if not before:
        return None, "Game not found", [], {}
    day = before.current_day
    workers = before.team_config.get("workers", [])
    assignments = {
        w["id"]: _card_key_by_id(before, w.get("assigned_card_id"))
        for w in workers if w.get("active")
    }

    game, log, error = await game_engine.start_work(db, game_id, user_id)

    result: dict = {"ok": error is None}
    if error:
        result["error"] = error
    else:
        result.update({
            "log": log,
            "daily_revenue": game.daily_revenue,
            "total_revenue": game.total_revenue,
        })
    await record(
        db, game_id, day, actor, "start_work",
        arguments={
            "assignments": assignments,
            "idle_workers": sorted(w for w, k in assignments.items() if k is None),
        },
        result=result, reason=reason, run_id=run_id,
    )
    return game, error, log, result


async def logged_end_day(
    db: AsyncSession, game_id: uuid.UUID, user_id: uuid.UUID,
    actor: str, reason: Optional[str] = None, run_id: Optional[uuid.UUID] = None,
) -> tuple[Optional[Game], Optional[str], dict, dict]:
    before = await game_engine.get_game(db, game_id, user_id)
    if not before:
        return None, "Game not found", {}, {}
    day = before.current_day

    game, modal, error = await game_engine.end_day(db, game_id, user_id)

    result: dict = {"ok": error is None}
    if error:
        result["error"] = error
    else:
        result.update({
            "event_key": modal.get("event_key"),
            "event_title": modal.get("title"),
            "overdue": modal.get("overdue", []),
            "log": modal.get("log", []),
            "next_day": game.current_day,
            "status": _status(game),
            "total_revenue": game.total_revenue,
        })
    await record(
        db, game_id, day, actor, "end_day",
        result=result, reason=reason, run_id=run_id,
    )
    if not error and _status(game) == "active":
        await record_day_start(db, game, run_id=run_id)
    return game, error, modal, result
