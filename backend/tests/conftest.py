"""
Shared pytest fixtures.

Sets required app settings via env vars *before* app.core.config is imported
anywhere, so tests never need a real OIDC provider or a .env file.
"""
import os

os.environ.setdefault("AuthClientId", "test-client")
os.environ.setdefault("AuthClientSecret", "test-secret")
os.environ.setdefault("AuthAuthority", "https://auth.invalid")
os.environ.setdefault("AuthCallbackUrl", "/auth/signin-oidc")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://kanban:kanban@localhost:5432/kanban_test",
)

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.core.database import AsyncSessionLocal, Base, engine
from app.models.game import Card, Game, GameEvent, GameMetric
from app.models.user import User


@pytest_asyncio.fixture
async def db_session():
    """A DB session backed by real Postgres, with a clean schema per test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        yield session

    async with AsyncSessionLocal() as session:
        await session.execute(delete(GameMetric))
        await session.execute(delete(GameEvent))
        await session.execute(delete(Card))
        await session.execute(delete(Game))
        await session.execute(delete(User))
        await session.commit()

    # pytest-asyncio gives each test its own event loop, but asyncpg connections
    # are bound to the loop they were created under. Dispose the pool so the next
    # test starts with fresh connections instead of reusing now-invalid ones.
    await engine.dispose()


@pytest_asyncio.fixture
async def user(db_session):
    u = User(
        id=uuid.uuid4(),
        sub="test-sub",
        email="tester@example.com",
        name="Tester",
        username="tester",
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
def make_worker():
    def _make(worker_id: str, worker_type: str, active: bool = True, assigned_card_id=None) -> dict:
        return {"id": worker_id, "type": worker_type, "active": active, "assigned_card_id": assigned_card_id}

    return _make


@pytest.fixture
def make_card():
    """Build a transient (non-persisted) Card for pure unit tests of game_engine helpers."""

    def _make(**kwargs) -> Card:
        defaults = dict(
            id=uuid.uuid4(),
            card_key="S1",
            title="Test Card",
            card_type="standard",
            column="analysis",
            analysis_total=5,
            analysis_remaining=5.0,
            dev_total=5,
            dev_remaining=5.0,
            test_total=5,
            test_remaining=5.0,
            val=1000,
            revenue_per_day=1000,
            color="blue",
            is_blocked=False,
            blocker_remaining=0,
            blocker_total=0,
            blocked_reason=None,
            deployment_bonus=0,
            due_day=None,
            appear_day=None,
            penalty=0,
            buff=None,
            deployed_day=None,
            entered_day=None,
            age=0,
            sort_order=0,
        )
        defaults.update(kwargs)
        return Card(**defaults)

    return _make


@pytest.fixture
def make_game():
    """Build a transient (non-persisted) Game with an in-memory cards list."""

    def _make(cards=None, **kwargs) -> Game:
        defaults = dict(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Test Game",
            player_name="Player",
            current_day=15,
            total_days=35,
            total_revenue=0,
            daily_revenue=0,
            phase="planning",
            work_done=False,
            carlos_policy=False,
            lockdown=False,
            wip_limits={"ready": 5, "analysis": 3, "development": 5, "test": 3, "expedite": 1},
            team_config={"workers": [], "buffs": {"analyst": 0, "developer": 0, "tester": 0}},
        )
        defaults.update(kwargs)
        game = Game(**defaults)
        game.cards = cards or []
        return game

    return _make
