import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.game import (
    GameResponse,
    AssignWorkerRequest, PullCardRequest,
    StartWorkResponse, EndDayResponse,
)
from app.services import game_engine

router = APIRouter()


@router.post("", response_model=GameResponse, status_code=201)
async def create_demo_game(db: AsyncSession = Depends(get_db)):
    return await game_engine.create_demo_game(db)


@router.post("/{game_id}/assign-worker", response_model=GameResponse)
async def demo_assign_worker(
    game_id: uuid.UUID,
    payload: AssignWorkerRequest,
    db: AsyncSession = Depends(get_db),
):
    demo_user = await game_engine.get_demo_user(db)
    game, error = await game_engine.assign_worker(
        db, game_id, payload.worker_id, payload.card_id, demo_user.id
    )
    if not game or not game.is_demo:
        raise HTTPException(status_code=404, detail="Demo game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return game


@router.post("/{game_id}/pull-card", response_model=GameResponse)
async def demo_pull_card(
    game_id: uuid.UUID,
    payload: PullCardRequest,
    db: AsyncSession = Depends(get_db),
):
    demo_user = await game_engine.get_demo_user(db)
    game, error = await game_engine.pull_card(db, game_id, payload.card_id, demo_user.id)
    if not game or not game.is_demo:
        raise HTTPException(status_code=404, detail="Demo game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return game


@router.post("/{game_id}/start-work", response_model=StartWorkResponse)
async def demo_start_work(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    demo_user = await game_engine.get_demo_user(db)
    game, log, error = await game_engine.start_work(db, game_id, demo_user.id)
    if not game or not game.is_demo:
        raise HTTPException(status_code=404, detail="Demo game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return StartWorkResponse(game=game, log=log)


@router.post("/{game_id}/end-day", response_model=EndDayResponse)
async def demo_end_day(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    demo_user = await game_engine.get_demo_user(db)
    game, modal, error = await game_engine.end_day(db, game_id, demo_user.id)
    if not game or not game.is_demo:
        raise HTTPException(status_code=404, detail="Demo game not found")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return EndDayResponse(game=game, modal=modal)
