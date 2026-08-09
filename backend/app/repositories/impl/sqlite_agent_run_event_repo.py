"""Persistent Agent run event replay repository."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRunEvent


class SqliteAgentRunEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_after(self, run_id: str, after_sequence: int = 0, limit: int = 500) -> list[dict]:
        result = await self.session.execute(
            select(AgentRunEvent)
            .where(AgentRunEvent.run_id == run_id, AgentRunEvent.sequence > after_sequence)
            .order_by(AgentRunEvent.sequence)
            .limit(limit)
        )
        return [
            {
                "id": item.id,
                "run_id": item.run_id,
                "sequence": item.sequence,
                "event_type": item.event_type,
                "payload": json.loads(item.payload_json),
                "is_terminal": item.is_terminal,
                "created_at": item.created_at.isoformat(),
            }
            for item in result.scalars()
        ]
