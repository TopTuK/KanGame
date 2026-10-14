import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.username import generate_random_game_name
from app.models.agent import GameAction
from app.models.user import User
from app.schemas.agent import GameActionOut
from app.schemas.game import (
    GameCreate, GameResponse, GameListItem,
    AssignWorkerRequest, PullCardRequest,
    StartWorkResponse, EndDayResponse,
)
from app.services import game_engine, action_log
from app.services.action_log import ACTOR_HUMAN

router = APIRouter()


async def _ensure_human_playable(db: AsyncSession, game_id: uuid.UUID, user: User) -> None:
    """Agent games are played only by their agent; the owner can watch, not move."""
    game = await game_engine.get_game(db, game_id, user.id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.is_agent:
        raise HTTPException(status_code=409, detail="This game is played by an AI agent")


@router.post("", response_model=GameResponse, status_code=201)
async def create_game(
    payload: GameCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = (payload.name or "").strip() or generate_random_game_name()
    game = await game_engine.create_game(db, name, payload.player_name, current_user.id)
    await action_log.record_day_start(db, game)
    return game


@router.get("", response_model=list[GameListItem])
async def list_games(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await game_engine.get_all_games(db, current_user.id)


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    game = await game_engine.get_game(db, game_id, current_user.id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.get("/{game_id}/actions", response_model=list[GameActionOut])
async def list_game_actions(
    game_id: uuid.UUID,
    after_seq: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Player action log (human or agent) for one of the user's games, oldest first."""
    game = await game_engine.get_game(db, game_id, current_user.id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    result = await db.execute(
        select(GameAction)
        .where(GameAction.game_id == game_id, GameAction.seq > after_seq)
        .order_by(GameAction.seq)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.post("/{game_id}/assign-worker", response_model=GameResponse)
async def assign_worker(
    game_id: uuid.UUID,
    payload: AssignWorkerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _ensure_human_playable(db, game_id, current_user)
    game, error, _ = await action_log.logged_assign_worker(
        db, game_id, payload.worker_id, payload.card_id, current_user.id, actor=ACTOR_HUMAN
    )
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return game


@router.post("/{game_id}/pull-card", response_model=GameResponse)
async def pull_card(
    game_id: uuid.UUID,
    payload: PullCardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _ensure_human_playable(db, game_id, current_user)
    game, error, _ = await action_log.logged_pull_card(
        db, game_id, payload.card_id, current_user.id, actor=ACTOR_HUMAN
    )
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return game


@router.post("/{game_id}/start-work", response_model=StartWorkResponse)
async def start_work(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _ensure_human_playable(db, game_id, current_user)
    game, error, log, _ = await action_log.logged_start_work(
        db, game_id, current_user.id, actor=ACTOR_HUMAN
    )
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return StartWorkResponse(game=game, log=log)


@router.post("/{game_id}/end-day", response_model=EndDayResponse)
async def end_day(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _ensure_human_playable(db, game_id, current_user)
    game, error, modal, _ = await action_log.logged_end_day(
        db, game_id, current_user.id, actor=ACTOR_HUMAN
    )
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return EndDayResponse(game=game, modal=modal)
