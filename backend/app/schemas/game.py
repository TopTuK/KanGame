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
    blocker_remaining: int
    blocker_total: int
    blocked_reason: Optional[str]
    val: int
    revenue_per_day: int
    deployment_bonus: int
    due_day: Optional[int]
    appear_day: Optional[int]
    penalty: int
    buff: Optional[str]
    deployed_day: Optional[int]
    entered_day: Optional[int]
    age: int
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
    user_id: uuid.UUID
    name: str
    player_name: str
    status: str
    current_day: int
    total_days: int
    total_revenue: int
    daily_revenue: int
    phase: str
    work_done: bool
    carlos_policy: bool
    lockdown: bool
    team_config: dict
    wip_limits: dict
    day_capacity_used: dict
    cards: list[CardResponse]
    events: list[EventResponse]
    metrics: list[MetricResponse]

    class Config:
        from_attributes = True


class AssignWorkerRequest(BaseModel):
    worker_id: str
    card_id: uuid.UUID


class PullCardRequest(BaseModel):
    card_id: uuid.UUID


class PullBacklogRequest(BaseModel):
    card_type: str  # s, f, i


class WorkLogEntry(BaseModel):
    type: str
    worker_id: Optional[str] = None
    worker_type: Optional[str] = None
    card_key: Optional[str] = None
    stage: Optional[str | int] = None
    roll: Optional[str] = None
    work: Optional[int] = None
    to: Optional[str] = None
    day: Optional[int] = None
    amount: Optional[int] = None
    buff: Optional[str] = None


class StartWorkResponse(BaseModel):
    game: GameResponse
    log: list[dict]


class EndDayModal(BaseModel):
    day: int
    title: str
    description: str
    overdue: list[dict]
    log: list[dict]


class EndDayResponse(BaseModel):
    game: GameResponse
    modal: EndDayModal


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
