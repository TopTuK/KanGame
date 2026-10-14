import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON, Index, Enum as SAEnum, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class AgentRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


ACTIVE_RUN_STATUSES = (AgentRunStatus.pending, AgentRunStatus.running)

# Shared with the startup migration in main.py, which adds them to existing tables.
AGENT_RUN_ACTIVE_INDEX = "uq_agent_runs_user_active"
ACTIVE_RUN_WHERE = "status IN ('pending', 'running')"
GAME_ACTION_SEQ_INDEX = "ix_game_actions_game_seq"


class AgentRun(Base):
    """One AI-agent playthrough of a game. The provider API key is never stored."""
    __tablename__ = "agent_runs"
    # At most one active (pending/running) run per user, enforced by the database.
    __table_args__ = (
        Index(AGENT_RUN_ACTIVE_INDEX, "user_id", unique=True, postgresql_where=text(ACTIVE_RUN_WHERE)),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"))
    name: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(500))
    status: Mapped[AgentRunStatus] = mapped_column(SAEnum(AgentRunStatus), default=AgentRunStatus.pending)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    llm_turns: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class GameAction(Base):
    """Shared, actor-agnostic log of player actions — humans and AI agents write
    the same rows so their play can be compared directly.

    actor:  human | agent | system (runner safety net acting on the agent's behalf)
    action: day_start | get_game_state | pull_card | assign_worker | start_work
            | end_day | day_summary | run_event
    """
    __tablename__ = "game_actions"
    __table_args__ = (Index(GAME_ACTION_SEQ_INDEX, "game_id", "seq", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor: Mapped[str] = mapped_column(String(10))
    seq: Mapped[int] = mapped_column(Integer)
    day: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(30))
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
