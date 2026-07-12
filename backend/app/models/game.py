import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.core.database import Base


class GameStatus(str, enum.Enum):
    lobby = "lobby"
    active = "active"
    completed = "completed"


class CardColumn(str, enum.Enum):
    backlog = "backlog"
    ready = "ready"
    analysis = "analysis"
    analysis_done = "analysis_done"
    development = "development"
    dev_done = "dev_done"
    test = "test"
    test_done = "test_done"
    deployed = "deployed"
    hidden = "hidden"
    exp_backlog = "exp_backlog"
    exp_ready = "exp_ready"
    exp_analysis = "exp_analysis"
    exp_analysis_done = "exp_analysis_done"
    exp_development = "exp_development"
    exp_dev_done = "exp_dev_done"
    exp_test = "exp_test"
    exp_test_done = "exp_test_done"
    exp_deployed = "exp_deployed"
    removed = "removed"


class CardType(str, enum.Enum):
    standard = "standard"
    bug = "bug"
    expedite = "expedite"
    fixed_date = "fixed_date"
    intangible = "intangible"


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100))
    player_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[GameStatus] = mapped_column(SAEnum(GameStatus), default=GameStatus.active)
    current_day: Mapped[int] = mapped_column(Integer, default=9)
    total_days: Mapped[int] = mapped_column(Integer, default=35)
    total_revenue: Mapped[int] = mapped_column(Integer, default=0)
    daily_revenue: Mapped[int] = mapped_column(Integer, default=0)
    phase: Mapped[str] = mapped_column(String(50), default="planning")
    work_done: Mapped[bool] = mapped_column(Boolean, default=False)
    carlos_policy: Mapped[bool] = mapped_column(Boolean, default=False)
    lockdown: Mapped[bool] = mapped_column(Boolean, default=False)
    team_config: Mapped[dict] = mapped_column(JSON, default=lambda: {
        "workers": [],
        "buffs": {"analyst": 0, "developer": 0, "tester": 0},
    })
    wip_limits: Mapped[dict] = mapped_column(JSON, default=lambda: {
        "ready": 5,
        "analysis": 3,
        "development": 5,
        "test": 3,
        "expedite": 1,
    })
    day_capacity_used: Mapped[dict] = mapped_column(JSON, default=lambda: {
        "analysis": 0,
        "development": 0,
        "test": 0,
    })
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cards: Mapped[list["Card"]] = relationship("Card", back_populates="game", cascade="all, delete-orphan")
    events: Mapped[list["GameEvent"]] = relationship("GameEvent", back_populates="game", cascade="all, delete-orphan")
    metrics: Mapped[list["GameMetric"]] = relationship("GameMetric", back_populates="game", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"))
    card_key: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(200))
    card_type: Mapped[str] = mapped_column(String(30))
    column: Mapped[str] = mapped_column(String(40), default=CardColumn.backlog.value)
    analysis_total: Mapped[int] = mapped_column(Integer, default=0)
    analysis_remaining: Mapped[float] = mapped_column(Float, default=0.0)
    dev_total: Mapped[int] = mapped_column(Integer, default=0)
    dev_remaining: Mapped[float] = mapped_column(Float, default=0.0)
    test_total: Mapped[int] = mapped_column(Integer, default=0)
    test_remaining: Mapped[float] = mapped_column(Float, default=0.0)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    blocker_remaining: Mapped[int] = mapped_column(Integer, default=0)
    blocker_total: Mapped[int] = mapped_column(Integer, default=0)
    blocked_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    val: Mapped[int] = mapped_column(Integer, default=0)
    revenue_per_day: Mapped[int] = mapped_column(Integer, default=0)
    deployment_bonus: Mapped[int] = mapped_column(Integer, default=0)
    due_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    appear_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    penalty: Mapped[int] = mapped_column(Integer, default=0)
    buff: Mapped[str | None] = mapped_column(String(20), nullable=True)
    deployed_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entered_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str] = mapped_column(String(20), default="blue")

    game: Mapped["Game"] = relationship("Game", back_populates="cards")


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"))
    day: Mapped[int] = mapped_column(Integer)
    event_key: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    game: Mapped["Game"] = relationship("Game", back_populates="events")


class GameMetric(Base):
    __tablename__ = "game_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"))
    day: Mapped[int] = mapped_column(Integer)
    throughput: Mapped[int] = mapped_column(Integer, default=0)
    wip: Mapped[int] = mapped_column(Integer, default=0)
    daily_revenue: Mapped[int] = mapped_column(Integer, default=0)
    cumulative_revenue: Mapped[int] = mapped_column(Integer, default=0)
    deployed_count: Mapped[int] = mapped_column(Integer, default=0)

    game: Mapped["Game"] = relationship("Game", back_populates="metrics")
