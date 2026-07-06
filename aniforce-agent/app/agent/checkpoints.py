"""SDK HITL checkpoint persistence in agent.db."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import text


CHECKPOINTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runtime_checkpoints (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    interruptions_json TEXT NOT NULL,
    run_state_json TEXT NOT NULL,
    approved_arguments_json TEXT,
    argument_diff_json TEXT,
    sdk_version TEXT,
    agent_version TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    error_json TEXT
)
"""


CHECKPOINTS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_runtime_checkpoints_run
ON runtime_checkpoints(run_id, session_id, user_id, status)
"""


class RuntimeCheckpointStore:
    """Stores short-lived SDK RunState checkpoints for HITL resume."""

    def __init__(self, engine):
        self.engine = engine

    async def ensure_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(text(CHECKPOINTS_TABLE_SQL))
            await conn.execute(text(CHECKPOINTS_INDEX_SQL))

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
    ) -> dict[str, Any]:
        await self.ensure_tables()
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
                        sdk_version, agent_version,
                        expires_at, created_at, resolved_at, error_json
                    ) VALUES (
                        :id, :run_id, :session_id, :user_id, :kind, :status,
                        :interruptions_json, :run_state_json,
                        :approved_arguments_json, :argument_diff_json,
                        :sdk_version, :agent_version,
                        :expires_at, :created_at, :resolved_at, :error_json
                    )
                    """
                ),
                item,
            )
        return self._decode(item)

    async def get(self, checkpoint_id: str, user_id: str) -> dict[str, Any] | None:
        await self.ensure_tables()
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text("SELECT * FROM runtime_checkpoints WHERE id = :id AND user_id = :user_id"),
                {"id": checkpoint_id, "user_id": user_id},
            )
            row = result.mappings().first()
        return self._decode(dict(row)) if row else None

    async def mark_status(
        self,
        checkpoint_id: str,
        user_id: str,
        status: str,
        *,
        error: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        await self.ensure_tables()
        values = {
            "id": checkpoint_id,
            "user_id": user_id,
            "status": status,
            "resolved_at": datetime.utcnow().isoformat(),
            "error_json": json.dumps(error, ensure_ascii=False) if error else None,
        }
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    UPDATE runtime_checkpoints
                    SET status = :status, resolved_at = :resolved_at, error_json = :error_json
                    WHERE id = :id AND user_id = :user_id
                    """
                ),
                values,
            )
        return await self.get(checkpoint_id, user_id)

    async def save_approval_metadata(
        self,
        checkpoint_id: str,
        user_id: str,
        *,
        approved_arguments: dict[str, Any],
        argument_diff: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """保存用户编辑后的审批参数和 diff。"""
        await self.ensure_tables()
        values = {
            "id": checkpoint_id,
            "user_id": user_id,
            "approved_arguments_json": json.dumps(approved_arguments, ensure_ascii=False, default=str),
            "argument_diff_json": json.dumps(argument_diff, ensure_ascii=False, default=str),
        }
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    UPDATE runtime_checkpoints
                    SET approved_arguments_json = :approved_arguments_json,
                        argument_diff_json = :argument_diff_json
                    WHERE id = :id AND user_id = :user_id
                    """
                ),
                values,
            )
        return await self.get(checkpoint_id, user_id)

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
