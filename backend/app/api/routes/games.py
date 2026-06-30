import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.game import (
    GameCreate, GameResponse, GameListItem,
    AssignWorkerRequest, PullCardRequest, PullBacklogRequest,
    StartWorkResponse, EndDayResponse,
)
from app.services import game_engine

router = APIRouter()


@router.post("", response_model=GameResponse, status_code=201)
async def create_game(
    payload: GameCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await game_engine.create_game(db, payload.name, payload.player_name, current_user.id)


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


@router.post("/{game_id}/assign-worker", response_model=GameResponse)
async def assign_worker(
    game_id: uuid.UUID,
    payload: AssignWorkerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    game, error = await game_engine.assign_worker(
        db, game_id, payload.worker_id, payload.card_id, current_user.id
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
    game, error = await game_engine.pull_card(db, game_id, payload.card_id, current_user.id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return game


@router.post("/{game_id}/pull-backlog", response_model=GameResponse)
async def pull_backlog(
    game_id: uuid.UUID,
    payload: PullBacklogRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    game, error = await game_engine.pull_backlog(db, game_id, payload.card_type, current_user.id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return game


@router.post("/{game_id}/pull-expedite", response_model=GameResponse)
async def pull_expedite(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    game, error = await game_engine.pull_expedite(db, game_id, current_user.id)
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
    game, log, error = await game_engine.start_work(db, game_id, current_user.id)
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
    game, modal, error = await game_engine.end_day(db, game_id, current_user.id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return EndDayResponse(game=game, modal=modal)
