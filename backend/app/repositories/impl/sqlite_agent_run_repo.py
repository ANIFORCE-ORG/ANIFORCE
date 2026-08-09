"""Agent run execution log repository."""

import json
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runs.state import ACTIVE_RUN_STATUSES, PERSISTED_TERMINAL_RUN_STATUSES
from app.models import AgentRun, AgentRunEvent, AgentSessionLease

TERMINAL_RUN_STATUSES = PERSISTED_TERMINAL_RUN_STATUSES


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
            "version": item.version,
            "lease_owner": item.lease_owner,
            "lease_expires_at": item.lease_expires_at.isoformat() if item.lease_expires_at else None,
            "heartbeat_at": item.heartbeat_at.isoformat() if item.heartbeat_at else None,
            "runtime_started_at": item.runtime_started_at.isoformat() if item.runtime_started_at else None,
            "execution_context": json.loads(item.run_state_json) if item.run_state_json else {},
            "execution_kind": item.execution_kind,
            "resume_payload": json.loads(item.resume_payload_json) if item.resume_payload_json else None,
            "error_code": item.error_code,
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
        execution_context: dict | None = None,
    ) -> dict:
        item = AgentRun(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            status=status,
            input_text=input_text,
            idempotency_key=idempotency_key,
            run_state_json=json.dumps(execution_context or {}, ensure_ascii=False),
            version=1,
            last_event_sequence=0,
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

    async def claim_next(self, worker_id: str, lease_seconds: int = 60) -> dict | None:
        now = datetime.utcnow()
        expiry = now + timedelta(seconds=lease_seconds)
        candidates = await self.session.execute(
            select(AgentRun)
            .where(
                AgentRun.status.in_(("queued", "resume_queued")),
                (AgentRun.lease_expires_at.is_(None)) | (AgentRun.lease_expires_at < now),
            )
            .order_by(AgentRun.started_at)
            .limit(10)
        )
        for candidate in candidates.scalars():
            lease_stmt = sqlite_insert(AgentSessionLease).values(
                session_id=candidate.session_id,
                run_id=candidate.run_id,
                lease_owner=worker_id,
                lease_expires_at=expiry,
                heartbeat_at=now,
                created_at=now,
            ).on_conflict_do_update(
                index_elements=[AgentSessionLease.session_id],
                set_={
                    "run_id": candidate.run_id,
                    "lease_owner": worker_id,
                    "lease_expires_at": expiry,
                    "heartbeat_at": now,
                },
                where=AgentSessionLease.lease_expires_at < now,
            )
            lease_result = await self.session.execute(lease_stmt)
            if lease_result.rowcount != 1:
                continue
            event_id = f"evt_{uuid4().hex}"
            event_type = "run.resuming" if candidate.status == "resume_queued" else "run.started"
            result = await self.session.execute(
                update(AgentRun)
                .where(
                    AgentRun.run_id == candidate.run_id,
                    AgentRun.version == candidate.version,
                    AgentRun.status == candidate.status,
                )
                .values(
                    status="running",
                    lease_owner=worker_id,
                    lease_expires_at=expiry,
                    heartbeat_at=now,
                    runtime_started_at=now,
                    last_event_sequence=AgentRun.last_event_sequence + 1,
                    version=AgentRun.version + 1,
                )
            )
            if result.rowcount != 1:
                await self.session.execute(
                    delete(AgentSessionLease).where(
                        AgentSessionLease.session_id == candidate.session_id,
                        AgentSessionLease.run_id == candidate.run_id,
                        AgentSessionLease.lease_owner == worker_id,
                    )
                )
                continue
            await self.session.flush()
            item = await self.session.get(AgentRun, candidate.run_id)
            if not item:
                return None
            self.session.add(AgentRunEvent(
                id=event_id,
                run_id=item.run_id,
                sequence=item.last_event_sequence,
                event_type=event_type,
                payload_json=json.dumps({"run_id": item.run_id, "status": "running"}),
                is_terminal=False,
                created_at=now,
            ))
            await self.session.flush()
            return self._to_dict(item)
        return None

    async def heartbeat(self, run_id: str, worker_id: str, lease_seconds: int = 60) -> bool:
        now = datetime.utcnow()
        expiry = now + timedelta(seconds=lease_seconds)
        result = await self.session.execute(
            update(AgentRun)
            .where(
                AgentRun.run_id == run_id,
                AgentRun.lease_owner == worker_id,
                AgentRun.status.in_(("running", "cancel_requested")),
                AgentRun.lease_expires_at > now,
            )
            .values(heartbeat_at=now, lease_expires_at=expiry, version=AgentRun.version + 1)
        )
        if result.rowcount != 1:
            return False
        lease_result = await self.session.execute(
            update(AgentSessionLease)
            .where(
                AgentSessionLease.run_id == run_id,
                AgentSessionLease.lease_owner == worker_id,
                AgentSessionLease.lease_expires_at > now,
            )
            .values(heartbeat_at=now, lease_expires_at=expiry)
        )
        return lease_result.rowcount == 1

    async def release_lease(self, run_id: str, worker_id: str) -> None:
        await self.session.execute(
            update(AgentRun)
            .where(AgentRun.run_id == run_id, AgentRun.lease_owner == worker_id)
            .values(lease_owner=None, lease_expires_at=None, heartbeat_at=None)
        )
        await self.session.execute(
            delete(AgentSessionLease).where(
                AgentSessionLease.run_id == run_id,
                AgentSessionLease.lease_owner == worker_id,
            )
        )

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
        lease_owner: str | None = None,
    ) -> dict | None:
        event_id = f"evt_{uuid4().hex}"
        values: dict = {
            "status": status,
            "last_event_sequence": AgentRun.last_event_sequence + 1,
            "version": AgentRun.version + 1,
        }
        if status == "running":
            values["runtime_started_at"] = datetime.utcnow()
        if is_terminal:
            values["completed_at"] = datetime.utcnow()
            values["terminal_event_id"] = event_id
            values["lease_owner"] = None
            values["lease_expires_at"] = None
            values["heartbeat_at"] = None
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
        if lease_owner is not None:
            stmt = stmt.where(
                AgentRun.lease_owner == lease_owner,
                AgentRun.lease_expires_at > datetime.utcnow(),
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
        if is_terminal and lease_owner is not None:
            await self.session.execute(delete(AgentSessionLease).where(AgentSessionLease.run_id == run_id))
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

    async def enqueue_resume(self, run_id: str, user_id: str, resume_payload: dict) -> dict | None:
        result = await self.session.execute(
            update(AgentRun)
            .where(
                AgentRun.run_id == run_id,
                AgentRun.user_id == user_id,
                AgentRun.status == "requires_action",
                AgentRun.terminal_event_id.is_(None),
            )
            .values(
                status="resume_queued",
                execution_kind="resume",
                resume_payload_json=json.dumps(resume_payload, ensure_ascii=False),
                version=AgentRun.version + 1,
            )
        )
        if result.rowcount != 1:
            return await self.get(run_id, user_id)
        await self.session.flush()
        return await self.get(run_id, user_id)

    async def request_cancel(self, run_id: str, user_id: str) -> dict | None:
        result = await self.session.execute(
            update(AgentRun)
            .where(
                AgentRun.run_id == run_id,
                AgentRun.user_id == user_id,
                AgentRun.status.in_(("queued", "resume_queued", "running", "requires_action")),
                AgentRun.terminal_event_id.is_(None),
            )
            .values(
                status="cancel_requested",
                cancel_requested_at=datetime.utcnow(),
                version=AgentRun.version + 1,
            )
        )
        if result.rowcount != 1:
            return await self.get(run_id, user_id)
        await self.session.flush()
        return await self.get(run_id, user_id)
