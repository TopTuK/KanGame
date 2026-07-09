from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import text, select

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.username import resolve_initial_username
from app.models.user import User
from app.api.routes import games, auth

app = FastAPI(title="KanGame API", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="kangame_session",
    same_site="lax",
    https_only=settings.SESSION_COOKIE_SECURE,
    max_age=14 * 24 * 3600,
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    migrations = [
        "ALTER TABLE cards ADD COLUMN IF NOT EXISTS deployment_bonus INTEGER DEFAULT 0",
        "ALTER TABLE cards ADD COLUMN IF NOT EXISTS val INTEGER DEFAULT 0",
        "ALTER TABLE cards ADD COLUMN IF NOT EXISTS blocker_remaining INTEGER DEFAULT 0",
        "ALTER TABLE cards ADD COLUMN IF NOT EXISTS blocker_total INTEGER DEFAULT 0",
        "ALTER TABLE cards ADD COLUMN IF NOT EXISTS appear_day INTEGER",
        "ALTER TABLE cards ADD COLUMN IF NOT EXISTS buff VARCHAR(20)",
        "ALTER TABLE cards ADD COLUMN IF NOT EXISTS entered_day INTEGER",
        "ALTER TABLE cards ADD COLUMN IF NOT EXISTS age INTEGER DEFAULT 0",
        "ALTER TABLE games ADD COLUMN IF NOT EXISTS daily_revenue INTEGER DEFAULT 0",
        "ALTER TABLE games ADD COLUMN IF NOT EXISTS work_done BOOLEAN DEFAULT FALSE",
        "ALTER TABLE games ADD COLUMN IF NOT EXISTS carlos_policy BOOLEAN DEFAULT FALSE",
        "ALTER TABLE games ADD COLUMN IF NOT EXISTS lockdown BOOLEAN DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(255)",
    ]
    async with engine.begin() as conn:
        for sql in migrations:
            await conn.execute(text(sql))
        try:
            await conn.execute(text(
                "UPDATE cards SET column = 'backlog' WHERE column::text = 'options'"
            ))
        except Exception:
            pass

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username.is_(None)))
        stale_users = result.scalars().all()
        for u in stale_users:
            u.username = resolve_initial_username(u.name, u.email)
        if stale_users:
            await session.commit()


app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(auth.router, tags=["auth"])


@app.get("/health")
async def health():
    return {"status": "ok"}
