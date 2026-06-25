"""Agent visible message repository."""

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentMessage


class SqliteAgentMessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_dict(self, item: AgentMessage) -> dict:
        return {
            "message_id": item.message_id,
            "id": item.message_id,
            "session_id": item.session_id,
            "user_id": item.user_id,
            "role": item.role,
            "content_json": json.loads(item.content_json),
            "content": json.loads(item.content_json),
            "run_id": item.run_id,
            "sequence": item.sequence,
            "created_at": item.created_at.isoformat(),
            "timestamp": item.created_at.isoformat() + "Z",
        }

    async def next_sequence(self, session_id: str, user_id: str) -> int:
        result = await self.session.execute(
            select(func.max(AgentMessage.sequence)).where(
                AgentMessage.session_id == session_id,
                AgentMessage.user_id == user_id,
            )
        )
        current = result.scalar_one_or_none()
        return int(current or 0) + 1

    async def create(
        self,
        *,
        session_id: str,
        user_id: str,
        role: str,
        content_json: dict,
        run_id: str | None = None,
    ) -> dict:
        item = AgentMessage(
            message_id=f"msg_{uuid4().hex}",
            session_id=session_id,
            user_id=user_id,
            role=role,
            content_json=json.dumps(content_json, ensure_ascii=False),
            run_id=run_id,
            sequence=await self.next_sequence(session_id, user_id),
            created_at=datetime.utcnow(),
        )
        self.session.add(item)
        await self.session.flush()
        return self._to_dict(item)

    async def list_by_session(self, session_id: str, user_id: str, limit: int = 500) -> list[dict]:
        result = await self.session.execute(
            select(AgentMessage)
            .where(AgentMessage.session_id == session_id, AgentMessage.user_id == user_id)
            .order_by(AgentMessage.sequence.asc())
            .limit(limit)
        )
        return [self._to_dict(item) for item in result.scalars().all()]
