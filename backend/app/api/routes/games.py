import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.game import (
    GameCreate, GameResponse, GameListItem,
    AllocateCapacityRequest, MoveCardRequest,
)
from app.services import game_engine

router = APIRouter()


@router.post("", response_model=GameResponse, status_code=201)
async def create_game(payload: GameCreate, db: AsyncSession = Depends(get_db)):
    game = await game_engine.create_game(db, payload.name, payload.player_name)
    return game


@router.get("", response_model=list[GameListItem])
async def list_games(db: AsyncSession = Depends(get_db)):
    return await game_engine.get_all_games(db)


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(game_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    game = await game_engine.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("/{game_id}/resolve-event", response_model=GameResponse)
async def resolve_event(game_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    game = await game_engine.resolve_event(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("/{game_id}/allocate", response_model=GameResponse)
async def allocate_capacity(
    game_id: uuid.UUID,
    payload: AllocateCapacityRequest,
    db: AsyncSession = Depends(get_db),
):
    game = await game_engine.allocate_capacity(db, game_id, payload.allocations)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("/{game_id}/move-card", response_model=GameResponse)
async def move_card(
    game_id: uuid.UUID,
    payload: MoveCardRequest,
    db: AsyncSession = Depends(get_db),
):
    game, error = await game_engine.move_card(db, game_id, payload.card_id, payload.target_column)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return game


@router.post("/{game_id}/end-day", response_model=GameResponse)
async def end_day(game_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    game = await game_engine.end_day(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game
