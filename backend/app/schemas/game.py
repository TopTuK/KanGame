from pydantic import BaseModel
from typing import Optional
import uuid


class GameCreate(BaseModel):
    name: str
    player_name: str


class CardResponse(BaseModel):
    id: uuid.UUID
    card_key: str
    title: str
    card_type: str
    column: str
    analysis_total: int
    analysis_remaining: float
    dev_total: int
    dev_remaining: float
    test_total: int
    test_remaining: float
    is_blocked: bool
    blocked_reason: Optional[str]
    revenue_per_day: int
    due_day: Optional[int]
    penalty: int
    deployed_day: Optional[int]
    color: str
    sort_order: int

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    id: uuid.UUID
    day: int
    event_key: str
    title: str
    description: str
    event_type: str
    payload: dict
    is_resolved: bool

    class Config:
        from_attributes = True


class MetricResponse(BaseModel):
    day: int
    throughput: int
    wip: int
    daily_revenue: int
    cumulative_revenue: int
    deployed_count: int

    class Config:
        from_attributes = True


class GameResponse(BaseModel):
    id: uuid.UUID
    name: str
    player_name: str
    status: str
    current_day: int
    total_days: int
    total_revenue: int
    phase: str
    team_config: dict
    wip_limits: dict
    day_capacity_used: dict
    cards: list[CardResponse]
    events: list[EventResponse]
    metrics: list[MetricResponse]

    class Config:
        from_attributes = True


class AllocateCapacityItem(BaseModel):
    card_id: uuid.UUID
    points: float


class AllocateCapacityRequest(BaseModel):
    allocations: list[AllocateCapacityItem]


class MoveCardRequest(BaseModel):
    card_id: uuid.UUID
    target_column: str


class GameListItem(BaseModel):
    id: uuid.UUID
    name: str
    player_name: str
    status: str
    current_day: int
    total_days: int
    total_revenue: int

    class Config:
        from_attributes = True
