"""SDK HITL checkpoint persistence in agent.db."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import text


class RuntimeCheckpointClaimError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class RuntimeCheckpointStore:
    """Stores short-lived SDK RunState checkpoints for HITL resume."""

    def __init__(self, engine):
        self.engine = engine

    async def create(
        self,
        *,
        run_id: str,
        session_id: str,
        user_id: str,
        interruptions: list[dict[str, Any]],
        run_state: dict[str, Any],
        ttl_hours: int = 24,
        sdk_version: str | None = None,
        agent_version: str | None = "workspace-agent-v1",
        context_schema_version: int = 1,
    ) -> dict[str, Any]:
        now = datetime.utcnow()
        checkpoint_id = f"ckpt_{uuid4().hex}"
        item = {
            "id": checkpoint_id,
            "run_id": run_id,
            "session_id": session_id,
            "user_id": user_id,
            "kind": "sdk_tool_approval",
            "status": "pending",
            "interruptions_json": json.dumps(interruptions, ensure_ascii=False, default=str),
            "run_state_json": json.dumps(run_state, ensure_ascii=False, default=str),
            "approved_arguments_json": None,
            "argument_diff_json": None,
            "sdk_version": sdk_version,
            "agent_version": agent_version,
            "context_schema_version": context_schema_version,
            "expires_at": (now + timedelta(hours=ttl_hours)).isoformat(),
            "created_at": now.isoformat(),
            "resolved_at": None,
            "error_json": None,
        }
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO runtime_checkpoints (
                        id, run_id, session_id, user_id, kind, status,
                        interruptions_json, run_state_json,
                        approved_arguments_json, argument_diff_json,
                        sdk_version, agent_version, context_schema_version,
                        expires_at, created_at, resolved_at, error_json
                    ) VALUES (
                        :id, :run_id, :session_id, :user_id, :kind, :status,
                        :interruptions_json, :run_state_json,
                        :approved_arguments_json, :argument_diff_json,
                        :sdk_version, :agent_version, :context_schema_version,
                        :expires_at, :created_at, :resolved_at, :error_json
                    )
                    """
                ),
                item,
            )
        return self._decode(item)

    async def get(self, checkpoint_id: str, user_id: str) -> dict[str, Any] | None:
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text("SELECT * FROM runtime_checkpoints WHERE id = :id AND user_id = :user_id"),
                {"id": checkpoint_id, "user_id": user_id},
            )
            row = result.mappings().first()
        return self._decode(dict(row)) if row else None

    async def claim_for_resume(
        self,
        checkpoint_id: str,
        user_id: str,
        *,
        approved_arguments: dict[str, Any] | None = None,
        argument_diff: list[dict[str, Any]] | None = None,
        claimed_by: str | None = None,
    ) -> dict[str, Any] | None:
        """Atomically claim one pending, unexpired checkpoint for resume."""
        now = datetime.utcnow().isoformat()
        values = {
            "id": checkpoint_id,
            "user_id": user_id,
            "now": now,
            "approved_arguments_json": json.dumps(approved_arguments or {}, ensure_ascii=False, default=str),
            "argument_diff_json": json.dumps(argument_diff or [], ensure_ascii=False, default=str),
            "claimed_by": claimed_by,
        }
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                    UPDATE runtime_checkpoints
                    SET status = 'resuming',
                        approved_arguments_json = :approved_arguments_json,
                        argument_diff_json = :argument_diff_json,
                        claimed_by = :claimed_by,
                        claimed_at = :now,
                        version = version + 1
                    WHERE id = :id
                      AND user_id = :user_id
                      AND status = 'pending'
                      AND expires_at > :now
                    """
                ),
                values,
            )
            claimed = result.rowcount == 1

        if claimed:
            return await self.get(checkpoint_id, user_id)

        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    UPDATE runtime_checkpoints
                    SET status = 'expired', resolved_at = :now, version = version + 1
                    WHERE id = :id
                      AND user_id = :user_id
                      AND status = 'pending'
                      AND expires_at <= :now
                    """
                ),
                values,
            )
        return None

    async def claim_or_raise(
        self,
        checkpoint_id: str,
        user_id: str,
        *,
        approved_arguments: dict[str, Any] | None = None,
        argument_diff: list[dict[str, Any]] | None = None,
        claimed_by: str | None = None,
    ) -> dict[str, Any]:
        checkpoint = await self.claim_for_resume(
            checkpoint_id,
            user_id,
            approved_arguments=approved_arguments,
            argument_diff=argument_diff,
            claimed_by=claimed_by,
        )
        if checkpoint:
            return checkpoint
        current = await self.get(checkpoint_id, user_id)
        if not current:
            raise RuntimeCheckpointClaimError("CHECKPOINT_NOT_FOUND", "Checkpoint not found", 404)
        if current["status"] == "expired":
            raise RuntimeCheckpointClaimError("CHECKPOINT_EXPIRED", "Checkpoint has expired", 410)
        raise RuntimeCheckpointClaimError(
            "CHECKPOINT_CONFLICT",
            f"Checkpoint cannot be resumed from status {current['status']}",
            409,
        )

    async def mark_status(
        self,
        checkpoint_id: str,
        user_id: str,
        status: str,
        *,
        error: dict[str, Any] | None = None,
        expected_status: str | None = None,
        claimed_by: str | None = None,
    ) -> dict[str, Any] | None:
        values = {
            "id": checkpoint_id,
            "user_id": user_id,
            "status": status,
            "expected_status": expected_status,
            "claimed_by": claimed_by,
            "resolved_at": datetime.utcnow().isoformat(),
            "error_json": json.dumps(error, ensure_ascii=False) if error else None,
        }
        status_guard = " AND status = :expected_status" if expected_status else ""
        owner_guard = " AND claimed_by = :claimed_by" if claimed_by else ""
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text(
                    f"""
                    UPDATE runtime_checkpoints
                    SET status = :status, resolved_at = :resolved_at,
                        error_json = :error_json, version = version + 1
                    WHERE id = :id AND user_id = :user_id{status_guard}{owner_guard}
                    """
                ),
                values,
            )
        current = await self.get(checkpoint_id, user_id)
        if expected_status and result.rowcount != 1:
            raise RuntimeCheckpointClaimError(
                "CHECKPOINT_FENCED",
                "Checkpoint ownership was lost before completion",
                409,
            )
        return current

    async def recover_stale_resuming(self, cutoff: datetime) -> int:
        """Fail stale claims; automatic replay could duplicate tool side effects."""
        now = datetime.utcnow().isoformat()
        error = json.dumps(
            {
                "code": "CHECKPOINT_RESUME_INTERRUPTED",
                "message": "Checkpoint resume was interrupted",
                "retryable": True,
            },
            ensure_ascii=False,
        )
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                    UPDATE runtime_checkpoints
                    SET status = 'failed', resolved_at = :now,
                        error_json = :error, version = version + 1
                    WHERE status = 'resuming'
                      AND claimed_at IS NOT NULL
                      AND claimed_at < :cutoff
                    """
                ),
                {"now": now, "error": error, "cutoff": cutoff.isoformat()},
            )
        return int(result.rowcount or 0)

    def _decode(self, item: dict[str, Any]) -> dict[str, Any]:
        decoded = dict(item)
        decoded["interruptions"] = json.loads(decoded.pop("interruptions_json") or "[]")
        decoded["run_state"] = json.loads(decoded.pop("run_state_json") or "{}")
        decoded["approved_arguments"] = json.loads(decoded.pop("approved_arguments_json") or "null") or {}
        decoded["argument_diff"] = json.loads(decoded.pop("argument_diff_json") or "null") or []
        decoded["error"] = json.loads(decoded.pop("error_json") or "null")
        return decoded


def serialize_workspace_context_for_checkpoint(context) -> dict[str, Any]:
    """Serialize WorkspaceRunContext without auth_token."""
    return {
        "user_id": context.user_id,
        "session_id": context.session_id,
        "run_id": context.run_id,
        "business_context_summary": context.business_context_summary,
        "ui_snapshot": context.ui_snapshot,
        "session_state": context.session_state,
        "task_type": context.task_type,
        "selected_skill_ids": context.selected_skill_ids,
        "selected_skill_versions": context.selected_skill_versions,
        "skill_slots": context.skill_slots,
        "skill_load_reason": context.skill_load_reason,
        "skill_status": context.skill_status,
        "skill_missing_slots": context.skill_missing_slots,
        "skill_pending_question": context.skill_pending_question,
    }


def interruption_to_dict(item) -> dict[str, Any]:
    raw = getattr(item, "raw_item", None)
    return {
        "type": getattr(item, "type", None),
        "tool_name": getattr(item, "tool_name", None) or getattr(raw, "name", None),
        "arguments": getattr(item, "arguments", None) or getattr(raw, "arguments", None),
        "call_id": getattr(item, "call_id", None) or getattr(raw, "call_id", None),
        "agent_name": getattr(getattr(item, "agent", None), "name", None),
    }
