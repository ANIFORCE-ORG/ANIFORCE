"""One-time reconciliation for historical Agent run and session state drift."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.session_state import SessionState
from app.models.agent_session_lease import AgentSessionLease
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.services.agent_run_service import AgentRunService


@dataclass(frozen=True)
class ReconciliationAction:
    entity: str
    entity_id: str
    from_status: str
    to_status: str
    reason: str


@dataclass(frozen=True)
class ReconciliationReport:
    dry_run: bool
    cutoff: str
    actions: list[ReconciliationAction]
    conflicts: int

    def to_dict(self) -> dict:
        return {
            "dry_run": self.dry_run,
            "cutoff": self.cutoff,
            "actions": [asdict(action) for action in self.actions],
            "conflicts": self.conflicts,
        }


class AgentStateReconciler:
    """Repairs stale execution states using conditional updates."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def reconcile(self, *, cutoff: datetime, apply: bool = False) -> ReconciliationReport:
        actions: list[ReconciliationAction] = []
        conflicts = 0
        now = datetime.utcnow()
        stale_result = await self.session.execute(
            select(AgentRun).where(
                AgentRun.status.in_(("running", "cancel_requested")),
                or_(
                    AgentRun.lease_expires_at < now,
                    (AgentRun.lease_expires_at.is_(None)) & (AgentRun.started_at < cutoff),
                ),
            )
        )
        stale_runs = list(stale_result.scalars())
        stale_ids = {run.run_id for run in stale_runs}
        error_payload = {
            "code": "RUN_INTERRUPTED",
            "message": "Agent run was interrupted before completion",
            "retryable": True,
            "reconciled_at": datetime.utcnow().isoformat(),
        }
        error = json.dumps(error_payload, ensure_ascii=False)
        for run in stale_runs:
            actions.append(
                ReconciliationAction(
                    entity="agent_run",
                    entity_id=run.run_id,
                    from_status=run.status,
                    to_status="cancelled" if run.status == "cancel_requested" else "error",
                    reason="expired_execution_lease",
                )
            )
            if apply:
                service = AgentRunService(SqliteAgentRunRepository(self.session))
                if run.status == "cancel_requested":
                    updated = await service.mark_cancelled(run.run_id, run.user_id)
                    expected = "cancelled"
                else:
                    updated = await service.mark_error(run.run_id, run.user_id, error_payload)
                    expected = "error"
                await self.session.execute(delete(AgentSessionLease).where(AgentSessionLease.run_id == run.run_id))
                if not updated or updated.get("status") != expected:
                    conflicts += 1

        state_result = await self.session.execute(
            select(SessionState).where(SessionState.status.in_(("running", "error")))
        )
        states = list(state_result.scalars())
        for state in states:
            run_result = await self.session.execute(
                select(AgentRun)
                .where(
                    AgentRun.session_id == state.session_id,
                    AgentRun.user_id == state.user_id,
                )
                .order_by(AgentRun.started_at.desc())
                .limit(1)
            )
            latest = run_result.scalar_one_or_none()
            target = self._project_session_status(state.status, latest, stale_ids)
            if target == state.status:
                continue
            reason = "latest_run_projection" if latest else "orphan_running_session"
            actions.append(
                ReconciliationAction(
                    entity="session_state",
                    entity_id=state.session_id,
                    from_status=state.status,
                    to_status=target,
                    reason=reason,
                )
            )
            if apply:
                values = {
                    "status": target,
                    "version": state.version + 1,
                    "updated_at": datetime.utcnow(),
                }
                if target == "active":
                    values["last_error_json"] = None
                elif latest and (latest.status == "error" or latest.run_id in stale_ids):
                    values["last_error_json"] = latest.error_json or error
                result = await self.session.execute(
                    update(SessionState)
                    .where(
                        SessionState.session_id == state.session_id,
                        SessionState.user_id == state.user_id,
                        SessionState.version == state.version,
                        SessionState.status == state.status,
                    )
                    .values(**values)
                )
                if result.rowcount != 1:
                    conflicts += 1

        return ReconciliationReport(
            dry_run=not apply,
            cutoff=cutoff.isoformat(),
            actions=actions,
            conflicts=conflicts,
        )

    @staticmethod
    def _project_session_status(
        current_status: str,
        latest: AgentRun | None,
        stale_ids: set[str],
    ) -> str:
        if latest is None:
            return "active" if current_status == "running" else current_status
        effective_status = "error" if latest.run_id in stale_ids else latest.status
        if effective_status in {"queued", "running"}:
            return "running"
        if effective_status == "error":
            return "error"
        return "active"
