import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl, SecretStr


class AgentRunCreate(BaseModel):
    """Omitted base_url/model fall back to the server defaults; a blank api_key
    falls back to the server key, but only for the default base URL."""
    name: str = Field(min_length=1, max_length=60)
    base_url: Optional[HttpUrl] = None
    model: Optional[str] = Field(None, max_length=200)
    api_key: Optional[SecretStr] = None


class AgentConfigOut(BaseModel):
    enabled: bool
    default_base_url: str
    default_model: str
    has_server_key: bool


class GameActionOut(BaseModel):
    id: uuid.UUID
    run_id: Optional[uuid.UUID]
    actor: str
    seq: int
    day: int
    action: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    reason: Optional[str]
    state: Optional[dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class AgentGameSummary(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    current_day: int
    total_days: int
    total_revenue: int


class AgentRunOut(BaseModel):
    id: uuid.UUID
    game_id: uuid.UUID
    name: str
    model: str
    base_url: str
    status: str
    error: Optional[str]
    tool_calls: int
    llm_turns: int
    input_tokens: int
    output_tokens: int
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    game: Optional[AgentGameSummary] = None


class AgentRunDetail(AgentRunOut):
    actions: list[GameActionOut]
