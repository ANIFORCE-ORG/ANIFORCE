"""Versioned schema migrations for the Agent SDK runtime database."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


Migration = Callable[[object], Awaitable[None]]


CHECKPOINTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runtime_checkpoints (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    interruptions_json TEXT NOT NULL,
    run_state_json TEXT NOT NULL,
    approved_arguments_json TEXT,
    argument_diff_json TEXT,
    sdk_version TEXT,
    agent_version TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    error_json TEXT
)
"""

RUNTIME_SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runtime_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


async def _column_names(conn: object, table_name: str) -> set[str]:
    result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
    return {str(row[1]) for row in result.fetchall()}


async def _migration_1(conn: object) -> None:
    await conn.execute(text(CHECKPOINTS_TABLE_SQL))
    columns = await _column_names(conn, "runtime_checkpoints")
    for name in ("approved_arguments_json", "argument_diff_json"):
        if name not in columns:
            await conn.execute(text(f"ALTER TABLE runtime_checkpoints ADD COLUMN {name} TEXT"))
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_runtime_checkpoints_run "
            "ON runtime_checkpoints(run_id, session_id, user_id, status)"
        )
    )
    await conn.execute(text(RUNTIME_SESSIONS_TABLE_SQL))
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_runtime_sessions_user "
            "ON runtime_sessions(user_id, updated_at)"
        )
    )


MIGRATIONS: tuple[tuple[int, Migration], ...] = ((1, _migration_1),)


class RuntimeSchemaMigrator:
    """Applies runtime DB migrations once during service startup."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def migrate(self) -> None:
        if self.engine.dialect.name != "sqlite":
            raise RuntimeError("Runtime migrations currently support SQLite only")
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS runtime_schema_migrations ("
                    "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
                )
            )
            result = await conn.execute(text("SELECT version FROM runtime_schema_migrations"))
            applied = {int(row[0]) for row in result.fetchall()}
            for version, migration in MIGRATIONS:
                if version in applied:
                    continue
                await migration(conn)
                await conn.execute(
                    text(
                        "INSERT INTO runtime_schema_migrations(version, applied_at) "
                        "VALUES (:version, CURRENT_TIMESTAMP)"
                    ),
                    {"version": version},
                )
