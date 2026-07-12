from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.leaderboard import LeaderboardEntry
from app.services import game_engine

router = APIRouter()


@router.get("", response_model=list[LeaderboardEntry])
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    return await game_engine.get_top_leaderboard(db)
