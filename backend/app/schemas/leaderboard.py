from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    name: str
    profit: int


class AgentLeaderboardEntry(BaseModel):
    agent_name: str
    model: str
    owner: str
    profit: int
    finished_at: Optional[datetime] = None
