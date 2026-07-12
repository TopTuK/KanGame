from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    name: str
    profit: int
