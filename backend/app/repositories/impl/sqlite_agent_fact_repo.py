"""Repositories for persistent tool call and Workspace artifact facts."""

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentArtifact, AgentToolCall


class SqliteAgentToolCallRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_started(self, *, run_id: str, tool_call_id: str, tool_name: str, arguments: dict) -> None:
        item = await self.session.get(AgentToolCall, tool_call_id)
        if item:
            return
        self.session.add(
            AgentToolCall(
                tool_call_id=tool_call_id,
                run_id=run_id,
                tool_name=tool_name,
                status="running",
                arguments_json=json.dumps(arguments, ensure_ascii=False),
                idempotency_key=tool_call_id,
                started_at=datetime.utcnow(),
            )
        )
        await self.session.flush()

    async def complete(self, *, tool_call_id: str, result: object) -> None:
        item = await self.session.get(AgentToolCall, tool_call_id)
        if not item:
            return
        item.status = "completed"
        item.result_json = json.dumps(result, ensure_ascii=False, default=str)
        item.completed_at = datetime.utcnow()
        await self.session.flush()

    async def list_by_run(self, run_id: str) -> list[dict]:
        result = await self.session.execute(
            select(AgentToolCall).where(AgentToolCall.run_id == run_id).order_by(AgentToolCall.started_at)
        )
        return [
            {
                "tool_call_id": item.tool_call_id,
                "run_id": item.run_id,
                "tool_name": item.tool_name,
                "status": item.status,
                "arguments": json.loads(item.arguments_json or "{}"),
                "result": json.loads(item.result_json) if item.result_json else None,
                "error": json.loads(item.error_json) if item.error_json else None,
                "started_at": item.started_at.isoformat(),
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            }
            for item in result.scalars()
        ]


class SqliteAgentArtifactRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_projection(
        self,
        *,
        session_id: str,
        run_id: str,
        source_tool_call_id: str | None,
        surface: str,
        payload: dict,
    ) -> dict:
        now = datetime.utcnow()
        item = AgentArtifact(
            artifact_id=f"artifact_{uuid4().hex}",
            session_id=session_id,
            run_id=run_id,
            source_tool_call_id=source_tool_call_id,
            surface=surface,
            schema_version=1,
            status="ready",
            payload_json=json.dumps(payload, ensure_ascii=False, default=str),
            created_at=now,
            updated_at=now,
        )
        self.session.add(item)
        await self.session.flush()
        return self._to_dict(item)

    async def list_by_session(self, session_id: str) -> list[dict]:
        result = await self.session.execute(
            select(AgentArtifact)
            .where(AgentArtifact.session_id == session_id)
            .order_by(AgentArtifact.updated_at)
        )
        return [self._to_dict(item) for item in result.scalars()]

    @staticmethod
    def _to_dict(item: AgentArtifact) -> dict:
        return {
            "artifact_id": item.artifact_id,
            "session_id": item.session_id,
            "run_id": item.run_id,
            "source_tool_call_id": item.source_tool_call_id,
            "surface": item.surface,
            "schema_version": item.schema_version,
            "status": item.status,
            "payload": json.loads(item.payload_json),
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
