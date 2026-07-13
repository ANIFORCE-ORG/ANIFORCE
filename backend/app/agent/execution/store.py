"""Persist run execution state and session settlement in short transactions."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.impl.sqlite_agent_approval_repo import SqliteAgentApprovalRepository
from app.repositories.impl.sqlite_agent_fact_repo import (
    SqliteAgentArtifactRepository,
    SqliteAgentToolCallRepository,
)
from app.agent.projections.message_projection import MessageProjection
from app.agent.sessions.task_state import persist_task_state
from app.agent.projections.session_settlement import SessionSettlementProjection
from app.agent.projections.tool_audit import ToolAuditProjection
from app.agent.projections.workspace_artifact import WorkspaceArtifactProjection
from app.repositories.impl.sqlite_agent_message_repo import SqliteAgentMessageRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository
from app.agent.approvals.service import AgentApprovalService
from app.agent.runs.service import AgentRunService

T = TypeVar("T")


class AgentRunExecutionStore:
    """Expose explicit persistence operations required by the run executor."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def _transaction(self, operation: Callable[[AsyncSession], Awaitable[T]]) -> T:
        async with self._session_maker() as session:
            try:
                result = await operation(session)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    async def get_session_state(self, session_id: str, user_id: str) -> dict | None:
        async def operation(session: AsyncSession) -> dict | None:
            return await SqliteSessionStateRepository(session).get(session_id, user_id)

        return await self._transaction(operation)

    async def update_session_task_state(
        self, session_id: str, user_id: str, task_state: dict
    ) -> dict | None:
        async def operation(session: AsyncSession) -> dict | None:
            return await persist_task_state(
                SqliteSessionStateRepository(session), session_id, user_id, task_state
            )

        return await self._transaction(operation)

    async def mark_session_running(self, session_id: str, user_id: str, version: int) -> dict:
        async def operation(session: AsyncSession) -> dict:
            return await SqliteSessionStateRepository(session).mark_running(session_id, user_id, version)

        return await self._transaction(operation)

    async def settle_session(
        self,
        *,
        session_id: str,
        user_id: str,
        run_status: str | None,
        error: dict | None = None,
    ) -> None:
        async def operation(session: AsyncSession) -> None:
            await SessionSettlementProjection(SqliteSessionStateRepository(session)).project(
                session_id=session_id,
                user_id=user_id,
                run_status=run_status,
                error=error,
            )

        await self._transaction(operation)

    async def get_run(self, run_id: str, user_id: str) -> dict:
        async def operation(session: AsyncSession) -> dict:
            return await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, user_id)

        return await self._transaction(operation)

    async def mark_running(self, run_id: str, user_id: str) -> dict | None:
        async def operation(session: AsyncSession) -> dict | None:
            return await AgentRunService(SqliteAgentRunRepository(session)).mark_running(run_id, user_id)

        return await self._transaction(operation)

    async def complete(
        self,
        run_id: str,
        user_id: str,
        *,
        usage: dict | None = None,
        final_output: str | None = None,
        lease_owner: str | None = None,
    ) -> dict | None:
        async def operation(session: AsyncSession) -> dict | None:
            return await AgentRunService(SqliteAgentRunRepository(session)).mark_completed(
                run_id,
                user_id,
                usage=usage,
                final_output=final_output,
                lease_owner=lease_owner,
            )

        return await self._transaction(operation)

    async def require_action(
        self,
        *,
        run_id: str,
        user_id: str,
        data: dict,
        lease_owner: str | None = None,
    ) -> dict | None:
        checkpoint_ref = str(data.get("checkpoint_id") or "")

        async def operation(session: AsyncSession) -> dict | None:
            run_service = AgentRunService(SqliteAgentRunRepository(session))
            approval_repo = SqliteAgentApprovalRepository(session)
            existing = await approval_repo.list_for_checkpoint(run_id, checkpoint_ref, user_id)
            if existing:
                return await run_service.get(run_id, user_id)
            updated = await run_service.mark_requires_action(
                run_id,
                user_id,
                checkpoint_ref,
                event_payload={**data, "status": "requires_action"},
                lease_owner=lease_owner,
            )
            if not updated or updated.get("status") != "requires_action":
                return updated
            interruptions = list(data.get("interruptions") or [])
            await AgentApprovalService(approval_repo).create_for_interruption(
                run_id=run_id,
                checkpoint_ref=checkpoint_ref,
                user_id=user_id,
                interruptions=interruptions,
                expires_at=data.get("expires_at"),
            )
            tool_repo = SqliteAgentToolCallRepository(session)
            for interruption in interruptions:
                arguments = interruption.get("arguments") or {}
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {"raw": arguments}
                await tool_repo.upsert_started(
                    run_id=run_id,
                    tool_call_id=str(interruption.get("call_id") or ""),
                    tool_name=str(interruption.get("tool_name") or ""),
                    arguments=arguments,
                )
            return updated

        return await self._transaction(operation)

    async def persist_output(
        self,
        *,
        run_id: str,
        session_id: str,
        user_id: str,
        events: list[tuple[str, dict]],
        error: dict | None = None,
        complete_usage: dict | None = None,
        final_output: str | None = None,
        lease_owner: str | None = None,
    ) -> dict | None:
        async def operation(session: AsyncSession) -> dict | None:
            message_repo = SqliteAgentMessageRepository(session)
            run_service = AgentRunService(SqliteAgentRunRepository(session))
            current = await run_service.get(run_id, user_id)
            if error:
                if current["status"] != "error":
                    return current
                await MessageProjection(
                    message_repo,
                    SqliteAgentToolCallRepository(session),
                ).project_error(
                    run_id=run_id,
                    session_id=session_id,
                    user_id=user_id,
                    error=error,
                )
                return current

            completed = None
            if complete_usage is not None or final_output is not None:
                if current["status"] in {"completed", "error", "cancelled"}:
                    return current
                completed = await run_service.mark_completed(
                    run_id,
                    user_id,
                    usage=complete_usage,
                    final_output=final_output,
                    lease_owner=lease_owner,
                )
                if not completed or completed["status"] != "completed":
                    return completed

            tool_repo = SqliteAgentToolCallRepository(session)
            await ToolAuditProjection(tool_repo).project(run_id, events)
            await MessageProjection(message_repo, tool_repo).project_success(
                run_id=run_id,
                session_id=session_id,
                user_id=user_id,
                events=events,
            )
            await WorkspaceArtifactProjection(
                SqliteAgentArtifactRepository(session)
            ).project(
                run_id=run_id,
                session_id=session_id,
                events=events,
            )
            return completed

        return await self._transaction(operation)

    async def fail(
        self,
        run_id: str,
        user_id: str,
        error: dict,
        *,
        lease_owner: str | None = None,
    ) -> dict | None:
        async def operation(session: AsyncSession) -> dict | None:
            return await AgentRunService(SqliteAgentRunRepository(session)).mark_error(
                run_id, user_id, error, lease_owner=lease_owner
            )

        return await self._transaction(operation)

    async def cancel(
        self,
        run_id: str,
        user_id: str,
        *,
        lease_owner: str | None = None,
    ) -> dict | None:
        async def operation(session: AsyncSession) -> dict | None:
            return await AgentRunService(SqliteAgentRunRepository(session)).mark_cancelled(
                run_id, user_id, lease_owner=lease_owner
            )

        return await self._transaction(operation)
