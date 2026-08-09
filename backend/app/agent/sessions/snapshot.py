"""Backend snapshot and persistent event replay services."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun
from app.repositories.impl.sqlite_agent_approval_repo import SqliteAgentApprovalRepository
from app.repositories.impl.sqlite_agent_fact_repo import SqliteAgentArtifactRepository, SqliteAgentToolCallRepository
from app.repositories.impl.sqlite_agent_message_repo import SqliteAgentMessageRepository
from app.repositories.impl.sqlite_agent_run_event_repo import SqliteAgentRunEventRepository
from app.repositories.impl.sqlite_agent_session_repo import SqliteAgentSessionRepository
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository


class AgentSnapshotService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def build(self, session_id: str, user_id: str) -> dict | None:
        product_session = await SqliteAgentSessionRepository(self.session).get(session_id, user_id)
        if not product_session:
            return None
        run_result = await self.session.execute(
            select(AgentRun)
            .where(AgentRun.session_id == session_id, AgentRun.user_id == user_id)
            .order_by(AgentRun.started_at.desc())
            .limit(1)
        )
        latest_model = run_result.scalar_one_or_none()
        latest_run = None
        approval_repo = SqliteAgentApprovalRepository(self.session)
        approvals: list[dict] = await approval_repo.list_for_session(session_id, user_id)
        tool_calls: list[dict] = []
        last_sequence = 0
        if latest_model:
            latest_run = {
                "run_id": latest_model.run_id,
                "session_id": latest_model.session_id,
                "status": latest_model.status,
                "checkpoint_ref": latest_model.checkpoint_ref,
                "last_event_sequence": latest_model.last_event_sequence,
                "started_at": latest_model.started_at.isoformat(),
                "completed_at": latest_model.completed_at.isoformat() if latest_model.completed_at else None,
                "error": __import__("json").loads(latest_model.error_json) if latest_model.error_json else None,
            }
            last_sequence = latest_model.last_event_sequence
            tool_calls = await SqliteAgentToolCallRepository(self.session).list_by_run(latest_model.run_id)
        return {
            "session": product_session,
            "state": await SqliteSessionStateRepository(self.session).get(session_id, user_id),
            "messages": await SqliteAgentMessageRepository(self.session).list_by_session(session_id, user_id),
            "latest_run": latest_run,
            "pending_approval": next(
                (item for item in approvals if item["status"] in {"pending", "resuming"}),
                None,
            ),
            "approvals": approvals,
            "tool_calls": tool_calls,
            "artifacts": await SqliteAgentArtifactRepository(self.session).list_by_session(session_id),
            "last_persisted_sequence": last_sequence,
        }

    async def events(self, run_id: str, user_id: str, after_sequence: int) -> list[dict]:
        result = await self.session.execute(
            select(AgentRun.run_id).where(AgentRun.run_id == run_id, AgentRun.user_id == user_id)
        )
        if result.scalar_one_or_none() is None:
            return []
        return await SqliteAgentRunEventRepository(self.session).list_after(run_id, after_sequence)
