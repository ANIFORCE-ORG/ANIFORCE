"""Runtime session ownership persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class RuntimeSessionOwnerMismatch(Exception):
    """The product session belongs to another authenticated user."""


class RuntimeSessionNotRegistered(Exception):
    """The runtime session has not been registered by an authenticated run."""


class RuntimeSessionStore:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def register_or_validate(self, session_id: str, user_id: str) -> None:
        """Atomically register a new session or validate its existing owner."""
        now = datetime.utcnow().isoformat()
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO runtime_sessions(session_id, user_id, created_at, updated_at) "
                    "VALUES (:session_id, :user_id, :now, :now) "
                    "ON CONFLICT(session_id) DO NOTHING"
                ),
                {"session_id": session_id, "user_id": user_id, "now": now},
            )
            result = await conn.execute(
                text("SELECT user_id FROM runtime_sessions WHERE session_id = :session_id"),
                {"session_id": session_id},
            )
            owner = result.scalar_one()
            if owner != user_id:
                raise RuntimeSessionOwnerMismatch(session_id)
            await conn.execute(
                text("UPDATE runtime_sessions SET updated_at = :now WHERE session_id = :session_id"),
                {"session_id": session_id, "now": now},
            )

    async def require_owner(self, session_id: str, user_id: str) -> None:
        async with self.engine.connect() as conn:
            result = await conn.execute(
                text("SELECT user_id FROM runtime_sessions WHERE session_id = :session_id"),
                {"session_id": session_id},
            )
            owner = result.scalar_one_or_none()
        if owner is None:
            raise RuntimeSessionNotRegistered(session_id)
        if owner != user_id:
            raise RuntimeSessionOwnerMismatch(session_id)
