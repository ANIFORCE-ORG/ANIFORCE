"""Agent product session repository."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentSession, AgentSessionStatus


class SqliteAgentSessionRepository:
    """Data access for backend-owned Agent sessions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_dict(self, item: AgentSession) -> dict:
        return {
            "session_id": item.session_id,
            "title": item.title,
            "status": item.status.value if hasattr(item.status, "value") else str(item.status),
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
            "archived_at": item.archived_at.isoformat() if item.archived_at else None,
        }

    async def create(self, session_id: str, user_id: str, title: str) -> dict:
        now = datetime.utcnow()
        item = AgentSession(
            session_id=session_id,
            user_id=user_id,
            title=title,
            status=AgentSessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self.session.add(item)
        await self.session.flush()
        return self._to_dict(item)

    async def get(self, session_id: str, user_id: str) -> dict | None:
        result = await self.session.execute(
            select(AgentSession).where(
                AgentSession.session_id == session_id,
                AgentSession.user_id == user_id,
            )
        )
        item = result.scalar_one_or_none()
        return self._to_dict(item) if item else None

    async def list_by_user(
        self,
        user_id: str,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        query = select(AgentSession).where(AgentSession.user_id == user_id)
        if not include_archived:
            query = query.where(AgentSession.status == AgentSessionStatus.ACTIVE)
        query = query.order_by(AgentSession.updated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return [self._to_dict(item) for item in result.scalars().all()]

    async def rename(self, session_id: str, user_id: str, title: str) -> dict | None:
        now = datetime.utcnow()
        result = await self.session.execute(
            update(AgentSession)
            .where(
                AgentSession.session_id == session_id,
                AgentSession.user_id == user_id,
                AgentSession.status == AgentSessionStatus.ACTIVE,
            )
            .values(title=title, updated_at=now)
        )
        if result.rowcount != 1:
            return None
        await self.session.flush()
        return await self.get(session_id, user_id)

    async def archive(self, session_id: str, user_id: str) -> dict | None:
        now = datetime.utcnow()
        result = await self.session.execute(
            update(AgentSession)
            .where(
                AgentSession.session_id == session_id,
                AgentSession.user_id == user_id,
                AgentSession.status == AgentSessionStatus.ACTIVE,
            )
            .values(status=AgentSessionStatus.ARCHIVED, archived_at=now, updated_at=now)
        )
        if result.rowcount != 1:
            return None
        await self.session.flush()
        return await self.get(session_id, user_id)

    async def touch(self, session_id: str, user_id: str) -> dict | None:
        result = await self.session.execute(
            update(AgentSession)
            .where(
                AgentSession.session_id == session_id,
                AgentSession.user_id == user_id,
                AgentSession.status == AgentSessionStatus.ACTIVE,
            )
            .values(updated_at=datetime.utcnow())
        )
        if result.rowcount != 1:
            return None
        await self.session.flush()
        return await self.get(session_id, user_id)
