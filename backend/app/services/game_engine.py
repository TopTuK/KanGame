"""
Core game engine — ported from shtaked32-code/kanbangame js/mechanics.js
"""
import random
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.models.game import Game, Card, GameEvent, GameMetric, GameStatus, CardColumn
from app.data.cards import (
    CARD_DEFINITIONS,
    EVENT_DEFINITIONS,
    INITIAL_BOARD,
    INITIAL_WORKERS,
    INITIAL_WIP,
    PULL_MOVES,
    ADVANCE_MAP,
    WIP_GROUPS,
    DAY_EVENTS,
    apply_initial_work_remaining,
)

PULL_WIP_KEYS = {
    "backlog": "ready",
    "ready": "analysis",
    "analysis_done": "development",
    "dev_done": "test",
    "exp_backlog": "expedite",
    "exp_ready": "exp_analysis",
    "exp_analysis_done": "exp_development",
    "exp_dev_done": "exp_test",
}

def _c(col) -> str:
    """Normalize column to string."""
    return col.value if isinstance(col, CardColumn) else str(col)


ACTIVE_WORK_LANES = [
    "analysis", "development", "test",
    "exp_analysis", "exp_development", "exp_test",
]

PIPELINE_AGE_LANES = [
    "ready", "analysis", "analysis_done", "development", "dev_done", "test", "test_done",
    "exp_ready", "exp_analysis", "exp_analysis_done",
    "exp_development", "exp_dev_done", "exp_test", "exp_test_done",
]

WORK_LANE_ORDER = [
    "exp_analysis", "exp_analysis_done", "exp_development", "exp_dev_done", "exp_test",
    "analysis", "analysis_done", "development", "dev_done", "test",
]


def _card_map(game: Game) -> dict[str, Card]:
    return {str(c.id): c for c in game.cards}


def _card_by_key(game: Game) -> dict[str, Card]:
    return {c.card_key: c for c in game.cards}


def _workers(game: Game) -> list[dict]:
    return [dict(worker) for worker in game.team_config.get("workers", [])]


def _set_workers(game: Game, workers: list[dict]):
    team = dict(game.team_config)
    team["workers"] = [dict(worker) for worker in workers]
    game.team_config = team
    flag_modified(game, "team_config")


def _buffs(game: Game) -> dict:
    return dict(game.team_config.get("buffs", {"analyst": 0, "developer": 0, "tester": 0}))


def _set_buffs(game: Game, buffs: dict):
    team = dict(game.team_config)
    team["buffs"] = buffs
    game.team_config = team
    flag_modified(game, "team_config")


def wip_count(game: Game, wip_key: str) -> int:
    lanes = WIP_GROUPS.get(wip_key, [wip_key])
    lane_set = set(lanes)
    return sum(1 for c in game.cards if c.column in lane_set)


def active_bar(card: Card) -> int:
    col = card.column
    if col in ("analysis", "exp_analysis"):
        return 0
    if col in ("development", "exp_development"):
        return 1
    if col in ("test", "exp_test"):
        return 2
    return -1


WORK_RANGES = {
    0: {"analyst": (1, 6), "developer": (1, 4), "tester": (1, 4)},   # Analysis
    1: {"analyst": (1, 3), "developer": (3, 7), "tester": (2, 4)},   # Development
    2: {"analyst": (2, 5), "developer": (2, 5), "tester": (3, 7)},   # Testing
}


def can_assign_worker(game: Game, worker: dict, card: Card) -> bool:
    if not worker or not worker.get("active"):
        return False
    bar = active_bar(card)
    if bar < 0:
        return False
    return True


def can_pull_to(game: Game, wip_key: str) -> bool:
    limit = game.wip_limits.get(wip_key, 999)
    return wip_count(game, wip_key) < limit


async def create_game(db: AsyncSession, name: str, player_name: str, user_id: uuid.UUID) -> Game:
    game = Game(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        player_name=player_name,
        status=GameStatus.active,
        current_day=9,
        total_days=35,
        phase="planning",
        work_done=False,
        carlos_policy=False,
        lockdown=False,
        wip_limits=dict(INITIAL_WIP),
        team_config={
            "workers": [dict(w) for w in INITIAL_WORKERS],
            "buffs": {"analyst": 0, "developer": 0, "tester": 0},
        },
    )
    db.add(game)
    await db.flush()

    placed_keys: set[str] = set()
    card_by_key: dict[str, Card] = {}

    for i, card_def in enumerate(CARD_DEFINITIONS):
        a, d, t = card_def["analysis"], card_def["dev"], card_def["test"]
        col = "hidden" if card_def["type"] == "expedite" else "backlog"

        card = Card(
            id=uuid.uuid4(),
            game_id=game.id,
            card_key=card_def["key"],
            title=card_def["title"],
            card_type=card_def["type"],
            column=col,
            analysis_total=a,
            analysis_remaining=float(a),
            dev_total=d,
            dev_remaining=float(d),
            test_total=t,
            test_remaining=float(t),
            val=card_def.get("val", 0),
            revenue_per_day=card_def.get("revenue", 0),
            due_day=card_def.get("due_day"),
            appear_day=card_def.get("appear_day"),
            buff=card_def.get("buff"),
            color=card_def["color"],
            sort_order=i,
        )
        db.add(card)
        card_by_key[card_def["key"]] = card

    for lane_str, keys in INITIAL_BOARD.items():
        for key in keys:
            card = card_by_key[key]
            card.column = lane_str
            card.entered_day = 1
            card.age = 0
            a_rem, d_rem, t_rem = apply_initial_work_remaining(
                card.analysis_total, card.dev_total, card.test_total, lane_str
            )
            card.analysis_remaining = a_rem
            card.dev_remaining = d_rem
            card.test_remaining = t_rem
            placed_keys.add(key)

    for event_def in EVENT_DEFINITIONS:
        db.add(GameEvent(
            id=uuid.uuid4(),
            game_id=game.id,
            day=event_def["day"],
            event_key=event_def["key"],
            title=event_def["title"],
            description=event_def["description"],
            event_type=event_def["type"],
            payload=event_def["payload"],
            is_resolved=False,
        ))

    await db.commit()
    return await get_game(db, game.id, user_id)


async def get_game(db: AsyncSession, game_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Game]:
    result = await db.execute(
        select(Game)
        .options(selectinload(Game.cards), selectinload(Game.events), selectinload(Game.metrics))
        .where(Game.id == game_id, Game.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_all_games(db: AsyncSession, user_id: uuid.UUID) -> list[Game]:
    result = await db.execute(
        select(Game).where(Game.user_id == user_id).order_by(Game.created_at.desc())
    )
    return list(result.scalars().all())


async def assign_worker(
    db: AsyncSession, game_id: uuid.UUID, worker_id: str, card_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Optional[Game], str | None]:
    game = await get_game(db, game_id, user_id)
    if not game or game.phase != "planning" or game.work_done:
        return game, "Cannot assign workers now"

    workers = _workers(game)
    worker = next((w for w in workers if w["id"] == worker_id), None)
    card = next((c for c in game.cards if c.id == card_id), None)
    if not worker or not card:
        return game, "Worker or card not found"

    if not can_assign_worker(game, worker, card):
        if not worker.get("active"):
            return game, "Worker unavailable"
        return game, "Assignment not allowed"

    wid = str(card_id)
    if worker.get("assigned_card_id") == wid:
        worker["assigned_card_id"] = None
    else:
        if worker.get("assigned_card_id"):
            worker["assigned_card_id"] = None
        worker["assigned_card_id"] = wid

    _set_workers(game, workers)
    await db.commit()
    return await get_game(db, game_id, user_id), None


async def pull_card(
    db: AsyncSession, game_id: uuid.UUID, card_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Optional[Game], str | None]:
    game = await get_game(db, game_id, user_id)
    if not game or game.phase != "planning" or game.work_done:
        return game, "Cannot pull now"

    card = next((c for c in game.cards if c.id == card_id), None)
    if not card:
        return game, "Card not found"

    from_col = card.column
    to_col_str = PULL_MOVES.get(from_col)
    if not to_col_str:
        return game, "Card cannot be pulled from this column"

    wip_key = PULL_WIP_KEYS.get(from_col)
    if wip_key and not can_pull_to(game, wip_key):
        return game, f"WIP limit reached for {wip_key}"

    card.column = to_col_str
    if from_col in ("backlog", "exp_backlog"):
        card.entered_day = game.current_day
        card.age = 0
    elif to_col_str in ("deployed", "exp_deployed"):
        card.deployed_day = game.current_day
        _apply_deploy_bonuses(game, card, [])

    await db.commit()
    return await get_game(db, game_id, user_id), None


def _roll_work(game: Game, worker: dict, card: Card) -> tuple[int, str]:
    bar = active_bar(card)
    lo, hi = WORK_RANGES[bar][worker["type"]]
    buffs = _buffs(game)
    r = random.randint(lo, hi)
    work = r + buffs.get(worker["type"], 0)
    return work, f"{lo}-{hi}: {r}"


def _advance_story(game: Game, card: Card, log: list[dict]) -> None:
    col = card.column
    next_col_str = ADVANCE_MAP.get(col)
    if not next_col_str:
        return

    if next_col_str in ("deployed", "exp_deployed"):
        card.deployed_day = game.current_day
        _apply_deploy_bonuses(game, card, log)
        log.append({"type": "deploy", "card_key": card.card_key, "day": game.current_day})
    else:
        log.append({"type": "advance", "card_key": card.card_key, "to": next_col_str})

    card.column = next_col_str


def _apply_deploy_bonuses(game: Game, card: Card, log: list[dict]) -> None:
    if card.card_type == "fixed_date":
        on_time = card.due_day and card.deployed_day <= card.due_day
        if on_time and card.val > 0:
            game.total_revenue += card.val
            log.append({"type": "bonus", "card_key": card.card_key, "amount": card.val})
        elif not on_time and card.val < 0:
            game.total_revenue += card.val
            log.append({"type": "penalty", "card_key": card.card_key, "amount": card.val})
    elif card.card_type == "intangible" and card.buff:
        buffs = _buffs(game)
        buffs[card.buff] = buffs.get(card.buff, 0) + 1
        _set_buffs(game, buffs)
        log.append({"type": "buff", "card_key": card.card_key, "buff": card.buff})
    elif card.card_type == "expedite":
        on_time = card.due_day and card.deployed_day <= card.due_day
        if on_time and card.val > 0:
            game.total_revenue += card.val
            log.append({"type": "bonus", "card_key": card.card_key, "amount": card.val})
        elif card.val < 0:
            game.total_revenue += card.val
            log.append({"type": "penalty", "card_key": card.card_key, "amount": card.val})


async def start_work(db: AsyncSession, game_id: uuid.UUID, user_id: uuid.UUID) -> tuple[Optional[Game], list[dict], str | None]:
    game = await get_game(db, game_id, user_id)
    if not game or game.phase != "planning":
        return game, [], "Wrong phase"
    if game.work_done:
        return game, [], "Work already done today"

    workers = _workers(game)
    log: list[dict] = []
    pending_advance: list[Card] = []

    for lane in WORK_LANE_ORDER:
        cards_in_lane = [c for c in game.cards if c.column == lane]
        for card in cards_in_lane:
            assigned = [w for w in workers if w.get("assigned_card_id") == str(card.id)]

            if card.is_blocked and card.blocker_remaining > 0:
                for worker in assigned:
                    r1 = random.randint(1, 6)
                    overflow = max(0, r1 - card.blocker_remaining)
                    card.blocker_remaining = max(0, card.blocker_remaining - r1)
                    log.append({
                        "type": "work", "worker_id": worker["id"], "worker_type": worker["type"],
                        "card_key": card.card_key, "stage": "blocker", "roll": f"1d6: {r1}", "work": r1,
                    })
                    if card.blocker_remaining == 0:
                        card.is_blocked = False
                        if overflow > 0:
                            bar = active_bar(card)
                            if bar == 0:
                                card.analysis_remaining = max(0, card.analysis_remaining - overflow)
                            elif bar == 1:
                                card.dev_remaining = max(0, card.dev_remaining - overflow)
                            elif bar == 2:
                                card.test_remaining = max(0, card.test_remaining - overflow)
                            if _stage_complete(card, bar):
                                pending_advance.append(card)
                continue

            bar = active_bar(card)
            if bar < 0:
                continue

            for worker in assigned:
                work, roll_desc = _roll_work(game, worker, card)
                if bar == 0:
                    card.analysis_remaining = max(0, card.analysis_remaining - work)
                elif bar == 1:
                    card.dev_remaining = max(0, card.dev_remaining - work)
                elif bar == 2:
                    card.test_remaining = max(0, card.test_remaining - work)

                log.append({
                    "type": "work", "worker_id": worker["id"], "worker_type": worker["type"],
                    "card_key": card.card_key, "stage": bar, "roll": roll_desc, "work": work,
                })

                if _stage_complete(card, bar) and card not in pending_advance:
                    pending_advance.append(card)

    for card in game.cards:
        if card.column in PIPELINE_AGE_LANES:
            card.age += 1

    for w in workers:
        w["assigned_card_id"] = None
    _set_workers(game, workers)

    for card in pending_advance:
        _advance_story(game, card, log)

    deployed_standard = [
        c for c in game.cards
        if c.column in ("deployed", "exp_deployed") and c.card_type == "standard"
    ]
    daily_rev = sum(c.val for c in deployed_standard)
    game.daily_revenue = daily_rev
    game.total_revenue += daily_rev
    game.work_done = True

    await db.commit()
    return await get_game(db, game_id, user_id), log, None


def _stage_complete(card: Card, bar: int) -> bool:
    if bar == 0:
        return card.analysis_remaining <= 0
    if bar == 1:
        return card.dev_remaining <= 0
    if bar == 2:
        return card.test_remaining <= 0
    return False


def _find_overdue(game: Game, day: int) -> list[Card]:
    active_lanes = [
        "ready", "analysis", "analysis_done", "development", "dev_done", "test", "test_done",
        "exp_backlog", "exp_ready", "exp_analysis", "exp_analysis_done",
        "exp_development", "exp_dev_done", "exp_test", "exp_test_done",
    ]
    return [
        c for c in game.cards
        if c.column in active_lanes
        and c.card_type in ("fixed_date", "expedite")
        and c.due_day == day
    ]


def _remove_overdue(game: Game, cards: list[Card], log: list[dict]) -> None:
    workers = _workers(game)
    for card in cards:
        for w in workers:
            if w.get("assigned_card_id") == str(card.id):
                w["assigned_card_id"] = None
        if card.val < 0:
            game.total_revenue += card.val
            log.append({"type": "overdue_penalty", "card_key": card.card_key, "amount": card.val})
        else:
            log.append({"type": "overdue_lost", "card_key": card.card_key})
        card.column = "removed"
    _set_workers(game, workers)


def _apply_blocker(game: Game, lane: str) -> None:
    lane_map = {
        "test": ("test", "exp_test"),
        "development": ("development", "exp_development"),
    }
    std_lane, exp_lane = lane_map.get(lane, (None, None))
    card = None
    if std_lane:
        card = next((c for c in game.cards if c.column == std_lane), None)
    if not card and exp_lane:
        card = next((c for c in game.cards if c.column == exp_lane), None)
    if card:
        total = 5 + random.randint(0, 2)
        card.is_blocked = True
        card.blocker_remaining = total
        card.blocker_total = total


def _apply_day_effects(game: Game, effects: list[dict]) -> None:
    workers = _workers(game)
    wip = dict(game.wip_limits)

    for eff in effects:
        etype = eff.get("type")
        if etype == "workerOut":
            wtype = eff.get("workerType")
            w = next((w for w in workers if w["type"] == wtype and w.get("active")), None)
            if w:
                w["assigned_card_id"] = None
                w["active"] = False
        elif etype == "workerIn":
            wtype = eff.get("workerType")
            w = next((w for w in workers if w["type"] == wtype and not w.get("active")), None)
            if w:
                w["active"] = True
        elif etype == "blocker":
            _apply_blocker(game, eff.get("lane", "test"))
        elif etype == "wipChange":
            wip[eff["lane"]] = eff["value"]
        elif etype == "carlosOn":
            game.carlos_policy = True
        elif etype == "carlosOff":
            game.carlos_policy = False
        elif etype == "lockdownOn":
            game.lockdown = True

    game.wip_limits = wip
    flag_modified(game, "wip_limits")
    _set_workers(game, workers)


def _reveal_expedite(game: Game, day: int) -> None:
    for card in game.cards:
        if (
            card.card_type == "expedite"
            and card.appear_day == day
            and card.column == "hidden"
        ):
            card.column = "exp_backlog"


async def end_day(db: AsyncSession, game_id: uuid.UUID, user_id: uuid.UUID) -> tuple[Optional[Game], dict, str | None]:
    game = await get_game(db, game_id, user_id)
    if not game:
        return game, {}, "Game not found"
    if not game.work_done:
        return game, {}, "Start work before ending the day"

    completed_day = game.current_day
    event_data = DAY_EVENTS.get(completed_day, {})
    overdue = _find_overdue(game, completed_day)
    end_log: list[dict] = []

    effects = event_data.get("effects", [])
    if effects:
        _apply_day_effects(game, effects)

    if overdue:
        _remove_overdue(game, overdue, end_log)

    wip = sum(1 for c in game.cards if c.column in ACTIVE_WORK_LANES)
    deployed = [c for c in game.cards if c.column in ("deployed", "exp_deployed")]
    throughput = sum(1 for c in deployed if c.deployed_day == completed_day)

    db.add(GameMetric(
        id=uuid.uuid4(),
        game_id=game.id,
        day=completed_day,
        throughput=throughput,
        wip=wip,
        daily_revenue=game.daily_revenue,
        cumulative_revenue=game.total_revenue,
        deployed_count=len(deployed),
    ))

    modal = {
        "day": completed_day,
        "event_key": event_data.get("key", ""),
        "title": event_data.get("title", ""),
        "description": event_data.get("description", ""),
        "overdue": [{"card_key": c.card_key, "due_day": c.due_day, "val": c.val} for c in overdue],
        "log": end_log,
    }

    for ev in game.events:
        if ev.day == completed_day:
            ev.is_resolved = True

    if completed_day >= game.total_days:
        game.status = GameStatus.completed
        game.phase = "completed"
    else:
        game.current_day += 1
        game.work_done = False
        game.daily_revenue = 0
        game.phase = "planning"
        _reveal_expedite(game, game.current_day)

    await db.commit()
    return await get_game(db, game_id, user_id), modal, None
