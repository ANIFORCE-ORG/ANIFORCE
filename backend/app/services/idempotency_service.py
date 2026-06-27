"""Minimal idempotency support for backend write APIs."""

import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyRecord


IDEMPOTENCY_HEADER = "Idempotency-Key"


class IdempotencyService:
    """Stores and replays first successful response for a user-scoped key."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_response(self, user_id: str, key: str | None) -> dict | None:
        if not key:
            return None
        result = await self.session.execute(
            select(IdempotencyRecord).where(
                IdempotencyRecord.user_id == user_id,
                IdempotencyRecord.key == key,
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            return None
        try:
            return json.loads(record.response_json)
        except json.JSONDecodeError:
            return None

    async def save_response(self, user_id: str, key: str | None, method: str, path: str, response: dict) -> None:
        if not key:
            return
        existing = await self.get_response(user_id, key)
        if existing is not None:
            return
        self.session.add(
            IdempotencyRecord(
                id=f"idem_{uuid4().hex}",
                user_id=user_id,
                key=key,
                method=method,
                path=path,
                response_json=json.dumps(response, ensure_ascii=False, default=str),
            )
        )
        await self.session.flush()
