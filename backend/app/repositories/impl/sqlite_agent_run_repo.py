"""Agent run execution log repository."""

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, AgentRunEvent


ACTIVE_RUN_STATUSES = {"queued", "running", "requires_action"}
TERMINAL_RUN_STATUSES = {"completed", "error", "cancelled"}


class SqliteAgentRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_dict(self, item: AgentRun) -> dict:
        return {
            "run_id": item.run_id,
            "session_id": item.session_id,
            "user_id": item.user_id,
            "status": item.status,
            "input_text": item.input_text,
            "trace_id": item.trace_id,
            "idempotency_key": item.idempotency_key,
            "usage": json.loads(item.usage_json) if item.usage_json else None,
            "error": json.loads(item.error_json) if item.error_json else None,
            "pending_approval": json.loads(item.pending_approval_json) if item.pending_approval_json else None,
            "checkpoint_ref": item.checkpoint_ref,
            "last_event_sequence": item.last_event_sequence,
            "terminal_event_id": item.terminal_event_id,
            "started_at": item.started_at.isoformat(),
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        }

    async def create(
        self,
        *,
        run_id: str,
        session_id: str,
        user_id: str,
        input_text: str,
        idempotency_key: str | None = None,
        status: str = "queued",
    ) -> dict:
        item = AgentRun(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            status=status,
            input_text=input_text,
            idempotency_key=idempotency_key,
            started_at=datetime.utcnow(),
        )
        self.session.add(item)
        await self.session.flush()
        return self._to_dict(item)

    async def get(self, run_id: str, user_id: str) -> dict | None:
        result = await self.session.execute(
            select(AgentRun).where(AgentRun.run_id == run_id, AgentRun.user_id == user_id)
        )
        item = result.scalar_one_or_none()
        return self._to_dict(item) if item else None

    async def get_by_idempotency(self, user_id: str, session_id: str, idempotency_key: str | None) -> dict | None:
        if not idempotency_key:
            return None
        result = await self.session.execute(
            select(AgentRun).where(
                AgentRun.user_id == user_id,
                AgentRun.session_id == session_id,
                AgentRun.idempotency_key == idempotency_key,
            )
        )
        item = result.scalar_one_or_none()
        return self._to_dict(item) if item else None

    async def get_active_for_session(self, user_id: str, session_id: str) -> dict | None:
        result = await self.session.execute(
            select(AgentRun)
            .where(
                AgentRun.user_id == user_id,
                AgentRun.session_id == session_id,
                AgentRun.status.in_(ACTIVE_RUN_STATUSES),
            )
            .order_by(AgentRun.started_at.desc())
            .limit(1)
        )
        item = result.scalar_one_or_none()
        return self._to_dict(item) if item else None

    async def transition_with_event(
        self,
        run_id: str,
        user_id: str,
        status: str,
        *,
        event_type: str,
        payload: dict,
        is_terminal: bool,
        usage: dict | None = None,
        error: dict | None = None,
        checkpoint_ref: str | None = None,
    ) -> dict | None:
        event_id = f"evt_{uuid4().hex}"
        values: dict = {
            "status": status,
            "last_event_sequence": AgentRun.last_event_sequence + 1,
        }
        if is_terminal:
            values["completed_at"] = datetime.utcnow()
            values["terminal_event_id"] = event_id
        if usage is not None:
            values["usage_json"] = json.dumps(usage, ensure_ascii=False)
        if error is not None:
            values["error_json"] = json.dumps(error, ensure_ascii=False)
        if checkpoint_ref is not None:
            values["checkpoint_ref"] = checkpoint_ref or None

        stmt = update(AgentRun).where(
            AgentRun.run_id == run_id,
            AgentRun.user_id == user_id,
            AgentRun.terminal_event_id.is_(None),
        )
        if status == "cancelled":
            stmt = stmt.where(AgentRun.status.in_(ACTIVE_RUN_STATUSES))
        elif status == "requires_action":
            stmt = stmt.where(
                ~AgentRun.status.in_(TERMINAL_RUN_STATUSES),
                AgentRun.status != "requires_action",
            )
        else:
            stmt = stmt.where(~AgentRun.status.in_(TERMINAL_RUN_STATUSES))
        result = await self.session.execute(stmt.values(**values))
        if result.rowcount != 1:
            return await self.get(run_id, user_id)

        run = await self.get(run_id, user_id)
        if run is None:
            return None
        self.session.add(
            AgentRunEvent(
                id=event_id,
                run_id=run_id,
                sequence=run["last_event_sequence"],
                event_type=event_type,
                payload_json=json.dumps(payload, ensure_ascii=False),
                is_terminal=is_terminal,
                created_at=datetime.utcnow(),
            )
        )
        await self.session.flush()
        return run

    async def mark_status(
        self,
        run_id: str,
        user_id: str,
        status: str,
        *,
        usage: dict | None = None,
        error: dict | None = None,
        checkpoint_ref: str | None = None,
    ) -> dict | None:
        values: dict = {"status": status}
        if status in {"completed", "error", "cancelled"}:
            values["completed_at"] = datetime.utcnow()
        if usage is not None:
            values["usage_json"] = json.dumps(usage, ensure_ascii=False)
        if error is not None:
            values["error_json"] = json.dumps(error, ensure_ascii=False)
        if checkpoint_ref is not None:
            values["checkpoint_ref"] = checkpoint_ref or None
        stmt = update(AgentRun).where(AgentRun.run_id == run_id, AgentRun.user_id == user_id)
        if status == "cancelled":
            stmt = stmt.where(AgentRun.status.in_(ACTIVE_RUN_STATUSES))
        elif status in {"running", "completed", "error", "requires_action"}:
            stmt = stmt.where(~AgentRun.status.in_(TERMINAL_RUN_STATUSES))
        result = await self.session.execute(stmt.values(**values))
        if result.rowcount != 1:
            return await self.get(run_id, user_id)
        await self.session.flush()
        return await self.get(run_id, user_id)
