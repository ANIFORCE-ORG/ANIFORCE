"""SQLite repository for backend-owned Agent approvals."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentApproval


class SqliteAgentApprovalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _loads(value: str | None, default: Any) -> Any:
        return json.loads(value) if value else default

    def _to_dict(self, item: AgentApproval) -> dict:
        return {
            "approval_id": item.approval_id,
            "checkpoint_ref": item.checkpoint_ref,
            "run_id": item.run_id,
            "tool_call_id": item.tool_call_id,
            "tool_name": item.tool_name,
            "user_id": item.user_id,
            "status": item.status,
            "decision": item.decision,
            "original_arguments": self._loads(item.original_arguments_json, {}),
            "edited_arguments": self._loads(item.edited_arguments_json, None),
            "argument_diff": self._loads(item.argument_diff_json, []),
            "preconditions": self._loads(item.preconditions_json, {}),
            "rejection_message": item.rejection_message,
            "expires_at": item.expires_at.isoformat(),
            "claimed_by": item.claimed_by,
            "claimed_at": item.claimed_at.isoformat() if item.claimed_at else None,
            "resolved_by": item.resolved_by,
            "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
            "version": item.version,
            "created_at": item.created_at.isoformat(),
        }

    async def create_many(
        self,
        *,
        run_id: str,
        checkpoint_ref: str,
        user_id: str,
        interruptions: list[dict],
        expires_at: datetime,
    ) -> list[dict]:
        now = datetime.utcnow()
        items = [
            AgentApproval(
                approval_id=f"approval_{uuid4().hex}",
                checkpoint_ref=checkpoint_ref,
                run_id=run_id,
                tool_call_id=item["call_id"],
                tool_name=item["tool_name"],
                user_id=user_id,
                status="pending",
                original_arguments_json=json.dumps(item.get("arguments") or {}, ensure_ascii=False),
                expires_at=expires_at,
                version=1,
                created_at=now,
                updated_at=now,
            )
            for item in interruptions
        ]
        self.session.add_all(items)
        await self.session.flush()
        return [self._to_dict(item) for item in items]

    async def list_for_checkpoint(
        self,
        run_id: str,
        checkpoint_ref: str,
        user_id: str,
    ) -> list[dict]:
        result = await self.session.execute(
            select(AgentApproval)
            .where(
                AgentApproval.run_id == run_id,
                AgentApproval.checkpoint_ref == checkpoint_ref,
                AgentApproval.user_id == user_id,
            )
            .order_by(AgentApproval.created_at, AgentApproval.approval_id)
        )
        return [self._to_dict(item) for item in result.scalars()]

    async def list_for_run(self, run_id: str, user_id: str) -> list[dict]:
        result = await self.session.execute(
            select(AgentApproval)
            .where(AgentApproval.run_id == run_id, AgentApproval.user_id == user_id)
            .order_by(AgentApproval.created_at, AgentApproval.approval_id)
        )
        return [self._to_dict(item) for item in result.scalars()]

    async def claim_checkpoint(
        self,
        *,
        run_id: str,
        checkpoint_ref: str,
        user_id: str,
        decision: str,
        edited_arguments: dict | None,
        argument_diff: list | None,
        rejection_message: str | None,
        claimed_by: str | None = None,
    ) -> tuple[str, list[dict]]:
        now = datetime.utcnow()
        count_result = await self.session.execute(
            select(func.count(AgentApproval.approval_id)).where(
                AgentApproval.run_id == run_id,
                AgentApproval.checkpoint_ref == checkpoint_ref,
                AgentApproval.user_id == user_id,
            )
        )
        total = int(count_result.scalar_one())
        if total == 0:
            return "not_found", []

        await self.session.execute(
            update(AgentApproval)
            .where(
                AgentApproval.run_id == run_id,
                AgentApproval.checkpoint_ref == checkpoint_ref,
                AgentApproval.user_id == user_id,
                AgentApproval.status == "pending",
                AgentApproval.expires_at <= now,
            )
            .values(status="expired", resolved_at=now, updated_at=now, version=AgentApproval.version + 1)
        )
        result = await self.session.execute(
            update(AgentApproval)
            .where(
                AgentApproval.run_id == run_id,
                AgentApproval.checkpoint_ref == checkpoint_ref,
                AgentApproval.user_id == user_id,
                AgentApproval.status == "pending",
                AgentApproval.expires_at > now,
            )
            .values(
                status="resuming",
                decision=decision,
                edited_arguments_json=(
                    json.dumps(edited_arguments, ensure_ascii=False) if edited_arguments is not None else None
                ),
                argument_diff_json=json.dumps(argument_diff or [], ensure_ascii=False),
                rejection_message=rejection_message,
                claimed_by=claimed_by,
                claimed_at=now,
                updated_at=now,
                version=AgentApproval.version + 1,
            )
        )
        items = await self.list_for_checkpoint(run_id, checkpoint_ref, user_id)
        if any(item["status"] == "expired" for item in items):
            return "expired", items
        if result.rowcount != total:
            return "conflict", items
        return "claimed", items

    async def mark_checkpoint_status(
        self,
        *,
        run_id: str,
        checkpoint_ref: str,
        user_id: str,
        status: str,
        expected_status: str = "resuming",
    ) -> int:
        now = datetime.utcnow()
        result = await self.session.execute(
            update(AgentApproval)
            .where(
                AgentApproval.run_id == run_id,
                AgentApproval.checkpoint_ref == checkpoint_ref,
                AgentApproval.user_id == user_id,
                AgentApproval.status == expected_status,
            )
            .values(
                status=status,
                resolved_at=now,
                updated_at=now,
                version=AgentApproval.version + 1,
            )
        )
        return int(result.rowcount or 0)
