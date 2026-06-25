"""
Core game engine for the Kanban simulation.
Implements the getKanban game mechanics:
- Pull system (right to left)
- WIP limits per column
- Class of service (expedite bypasses WIP)
- Capacity allocation to cards
- Revenue / scoring
- Event resolution
"""
import random
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.game import Game, Card, GameEvent, GameMetric, GameStatus, CardColumn, CardType
from app.data.cards import CARD_DEFINITIONS, EVENT_DEFINITIONS
from app.schemas.game import AllocateCapacityItem

# Random daily contribution ranges per role per stage (min, max)
MEMBER_CAPACITY_RANGES = {
    "analyst":   {"analysis": (0.8, 1.3), "development": (0.3, 0.5), "test": (0.4, 0.8)},
    "developer": {"analysis": (0.3, 0.6), "development": (0.8, 1.5), "test": (0.5, 0.7)},
    "tester":    {"analysis": (0.4, 0.6), "development": (0.3, 0.8), "test": (0.8, 1.4)},
}


COLUMN_ORDER = [
    CardColumn.options,
    CardColumn.ready,
    CardColumn.analysis,
    CardColumn.development,
    CardColumn.test,
    CardColumn.deployed,
]

ACTIVE_COLUMNS = [CardColumn.analysis, CardColumn.development, CardColumn.test]

WIP_COLUMN_MAP = {
    CardColumn.analysis: "analysis",
    CardColumn.development: "development",
    CardColumn.test: "test",
}


async def create_game(db: AsyncSession, name: str, player_name: str) -> Game:
    game = Game(
        id=uuid.uuid4(),
        name=name,
        player_name=player_name,
        status=GameStatus.active,
        current_day=1,
        phase="event",
    )
    db.add(game)
    await db.flush()

    # Create cards with randomized story points
    for i, card_def in enumerate(CARD_DEFINITIONS):
        start_col = CardColumn(card_def["start_column"])
        analysis_pts = random.randint(1, 5) if card_def["analysis"] > 0 else 0
        dev_pts = random.randint(1, 7)
        test_pts = random.randint(1, 6)
        card = Card(
            id=uuid.uuid4(),
            game_id=game.id,
            card_key=card_def["key"],
            title=card_def["title"],
            card_type=CardType(card_def["type"]),
            column=start_col,
            analysis_total=analysis_pts,
            analysis_remaining=float(analysis_pts),
            dev_total=dev_pts,
            dev_remaining=float(dev_pts),
            test_total=test_pts,
            test_remaining=float(test_pts),
            revenue_per_day=card_def.get("revenue", 0),
            due_day=card_def.get("due_day"),
            penalty=card_def.get("penalty", 0),
            color=card_def["color"],
            sort_order=i,
        )
        db.add(card)

    # Create events
    for event_def in EVENT_DEFINITIONS:
        event = GameEvent(
            id=uuid.uuid4(),
            game_id=game.id,
            day=event_def["day"],
            event_key=event_def["key"],
            title=event_def["title"],
            description=event_def["description"],
            event_type=event_def["type"],
            payload=event_def["payload"],
            is_resolved=False,
        )
        db.add(event)

    await db.commit()
    await db.refresh(game)
    return await get_game(db, game.id)


def _generate_member_capacities(team_config: dict) -> dict:
    """Generate random daily contribution values for each team member per stage."""
    capacities = {}
    members_spec = [
        ("analyst", "A", team_config.get("analysts", 2)),
        ("developer", "D", team_config.get("developers", 4)),
        ("tester", "T", team_config.get("testers", 3)),
    ]
    for role, prefix, count in members_spec:
        ranges = MEMBER_CAPACITY_RANGES[role]
        for i in range(count):
            mid = f"{prefix}{i + 1}"
            capacities[mid] = {
                stage: round(random.uniform(lo, hi), 2)
                for stage, (lo, hi) in ranges.items()
            }
    return capacities


async def get_game(db: AsyncSession, game_id: uuid.UUID) -> Optional[Game]:
    result = await db.execute(
        select(Game)
        .options(
            selectinload(Game.cards),
            selectinload(Game.events),
            selectinload(Game.metrics),
        )
        .where(Game.id == game_id)
    )
    return result.scalar_one_or_none()


async def get_all_games(db: AsyncSession) -> list[Game]:
    result = await db.execute(select(Game).order_by(Game.created_at.desc()))
    return list(result.scalars().all())


async def resolve_event(db: AsyncSession, game_id: uuid.UUID) -> Game:
    game = await get_game(db, game_id)
    if not game or game.phase != "event":
        return game

    # Get today's event
    today_events = [e for e in game.events if e.day == game.current_day and not e.is_resolved]

    for event in today_events:
        await _apply_event(db, game, event)
        event.is_resolved = True

    # Move to capacity phase (do NOT reset day_capacity_used here — end_day already
    # resets it to 0, and capacity_change events may have pre-consumed some capacity)
    game.phase = "capacity"

    # Generate random member capacities for today
    team = dict(game.team_config)
    team["member_capacities"] = _generate_member_capacities(team)
    game.team_config = team

    await db.commit()
    return await get_game(db, game_id)


async def _apply_event(db: AsyncSession, game: Game, event: GameEvent):
    payload = event.payload

    if event.event_type == "new_card":
        card_key = payload.get("card_key")
        if card_key:
            for card in game.cards:
                if card.card_key == card_key:
                    card.column = CardColumn.ready
                    break

    elif event.event_type == "capacity_change":
        # Negative delta: pre-consume capacity (reduces what's available)
        # Positive delta: store as bonus added on top of member capacities
        used = dict(game.day_capacity_used)
        team = dict(game.team_config)
        capacity_delta = payload.get("capacity_delta", {})
        bonus = dict(team.get("capacity_bonus") or {"analysis": 0, "development": 0, "test": 0})
        for col, delta in capacity_delta.items():
            if delta < 0:
                used[col] = max(0, used.get(col, 0) + abs(delta))
            elif delta > 0 and col in bonus:
                bonus[col] = round(bonus[col] + delta, 2)
        game.day_capacity_used = used
        team["capacity_bonus"] = bonus
        game.team_config = team

    elif event.event_type == "billing":
        deadline_card_key = payload.get("deadline_card")
        if deadline_card_key:
            for card in game.cards:
                if card.card_key == deadline_card_key and card.column != CardColumn.deployed:
                    game.total_revenue -= card.penalty


async def allocate_capacity(
    db: AsyncSession,
    game_id: uuid.UUID,
    allocations: list[AllocateCapacityItem],
) -> Game:
    game = await get_game(db, game_id)
    if not game or game.phase != "capacity":
        return game

    capacity_applied = {"analysis": 0.0, "development": 0.0, "test": 0.0}
    card_map = {card.id: card for card in game.cards}

    for alloc in allocations:
        card = card_map.get(alloc.card_id)
        if not card or card.is_blocked:
            continue

        col = card.column
        if col == CardColumn.analysis:
            pts = min(alloc.points, max(0.0, card.analysis_remaining))
            card.analysis_remaining = max(0.0, card.analysis_remaining - pts)
            capacity_applied["analysis"] += pts

        elif col == CardColumn.development:
            pts = min(alloc.points, max(0.0, card.dev_remaining))
            card.dev_remaining = max(0.0, card.dev_remaining - pts)
            capacity_applied["development"] += pts

        elif col == CardColumn.test:
            pts = min(alloc.points, max(0.0, card.test_remaining))
            card.test_remaining = max(0.0, card.test_remaining - pts)
            capacity_applied["test"] += pts

    used = dict(game.day_capacity_used)
    for role, pts in capacity_applied.items():
        used[role] = round((used.get(role) or 0) + pts, 2)
    game.day_capacity_used = used

    await db.commit()
    return await get_game(db, game_id)


async def move_card(db: AsyncSession, game_id: uuid.UUID, card_id: uuid.UUID, target_column: str) -> tuple[Game, str | None]:
    game = await get_game(db, game_id)
    if not game or game.phase not in ("capacity", "move"):
        return game, "Wrong game phase"

    target_col = CardColumn(target_column)
    card = next((c for c in game.cards if c.id == card_id), None)
    if not card:
        return game, "Card not found"

    current_col = card.column
    current_idx = COLUMN_ORDER.index(current_col)
    target_idx = COLUMN_ORDER.index(target_col)

    # Must move exactly one step forward
    if target_idx != current_idx + 1:
        return game, "Can only move one column at a time"

    # Check card is ready to move
    error = _check_card_ready_to_move(card)
    if error:
        return game, error

    # Check WIP limits (expedite bypasses)
    if card.card_type != CardType.expedite and target_col in ACTIVE_COLUMNS:
        wip_key = WIP_COLUMN_MAP[target_col]
        wip_limit = game.wip_limits.get(wip_key, 999)
        current_wip = sum(1 for c in game.cards if c.column == target_col)
        if current_wip >= wip_limit:
            return game, f"WIP limit reached for {wip_key} ({wip_limit} max)"

    card.column = target_col
    if target_col == CardColumn.deployed:
        card.deployed_day = game.current_day

    game.phase = "move"
    await db.commit()
    return await get_game(db, game_id), None


def _check_card_ready_to_move(card: Card) -> Optional[str]:
    col = card.column
    if col in (CardColumn.options, CardColumn.ready):
        return None
    if col == CardColumn.analysis and (card.analysis_remaining or 0) > 0.01:
        return f"Analysis not complete ({card.analysis_remaining:.1f} points remaining)"
    elif col == CardColumn.development and (card.dev_remaining or 0) > 0.01:
        return f"Development not complete ({card.dev_remaining:.1f} points remaining)"
    elif col == CardColumn.test and (card.test_remaining or 0) > 0.01:
        return f"Testing not complete ({card.test_remaining:.1f} points remaining)"
    return None


async def end_day(db: AsyncSession, game_id: uuid.UUID) -> Game:
    game = await get_game(db, game_id)
    if not game or game.phase not in ("capacity", "move"):
        return game

    # Calculate daily revenue from deployed cards
    deployed_cards = [c for c in game.cards if c.column == CardColumn.deployed]
    daily_revenue = sum(c.revenue_per_day for c in deployed_cards)
    game.total_revenue += daily_revenue

    # Record metric
    wip = sum(1 for c in game.cards if c.column in ACTIVE_COLUMNS)
    throughput = sum(1 for c in game.cards if c.deployed_day == game.current_day)
    metric = GameMetric(
        id=uuid.uuid4(),
        game_id=game.id,
        day=game.current_day,
        throughput=throughput,
        wip=wip,
        daily_revenue=daily_revenue,
        cumulative_revenue=game.total_revenue,
        deployed_count=len(deployed_cards),
    )
    db.add(metric)

    # Check if game over
    if game.current_day >= game.total_days:
        game.status = GameStatus.completed
        game.phase = "completed"
    else:
        game.current_day += 1
        game.phase = "event"
        # Restore base team_config (temporary event bonuses expire each day)
        game.team_config = {
            "analysts": 2,
            "developers": 4,
            "testers": 3,
            "analyst_capacity": 2,
            "dev_capacity": 2,
            "test_capacity": 2,
        }
        game.day_capacity_used = {"analysis": 0, "development": 0, "test": 0}

    await db.commit()
    return await get_game(db, game_id)
