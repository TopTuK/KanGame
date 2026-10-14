"""
Startup migrations must upgrade databases created by older versions of the app
(create_all never alters existing tables).
"""
from sqlalchemy import text

from app.core.database import engine
from app.main import run_migrations
from app.services import game_engine as ge


async def _has_column(table: str, column: str) -> bool:
    async with engine.connect() as conn:
        row = await conn.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"
        ), {"t": table, "c": column})
        return row.first() is not None


async def test_migrations_add_missing_columns_and_fix_legacy_cards(db_session, user):
    game = await ge.create_game(db_session, "Old", "Alice", user.id)
    game_id = game.id
    await db_session.commit()  # release the session's read locks; DROP COLUMN needs an exclusive lock
    async with engine.begin() as conn:
        # Simulate a database from before the agent feature, with a legacy 'options' card.
        await conn.execute(text("ALTER TABLE games DROP COLUMN is_agent"))
        await conn.execute(text(
            """UPDATE cards SET "column" = 'options' WHERE game_id = :g AND card_key = 'S14'"""
        ), {"g": game_id})

    await run_migrations()

    # Regression: the legacy UPDATE used to fail and silently roll back every ALTER.
    assert await _has_column("games", "is_agent")
    async with engine.connect() as conn:
        col = (await conn.execute(text(
            """SELECT "column" FROM cards WHERE game_id = :g AND card_key = 'S14'"""
        ), {"g": game_id})).scalar_one()
        is_agent = (await conn.execute(text("SELECT is_agent FROM games WHERE id = :g"), {"g": game_id})).scalar_one()
    assert col == "backlog"
    assert is_agent is False
