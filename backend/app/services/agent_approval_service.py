"""Application service for Agent approval facts and CAS transitions."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.repositories.impl.sqlite_agent_approval_repo import SqliteAgentApprovalRepository


class AgentApprovalError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AgentApprovalService:
    def __init__(self, repo: SqliteAgentApprovalRepository):
        self.repo = repo

    async def create_for_interruption(
        self,
        *,
        run_id: str,
        checkpoint_ref: str,
        user_id: str,
        interruptions: list[dict],
        expires_at: str | None,
    ) -> list[dict]:
        normalized = []
        for item in interruptions:
            call_id = str(item.get("call_id") or "").strip()
            tool_name = str(item.get("tool_name") or "").strip()
            if not call_id or not tool_name:
                raise AgentApprovalError(
                    "APPROVAL_BINDING_INVALID",
                    "Approval interruption is missing tool identity",
                    422,
                )
            arguments = item.get("arguments")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"raw": arguments}
            normalized.append({"call_id": call_id, "tool_name": tool_name, "arguments": arguments or {}})
        if not normalized:
            raise AgentApprovalError("APPROVAL_REQUIRED", "No approval interruptions found", 422)
        expiry = self._parse_expiry(expires_at)
        return await self.repo.create_many(
            run_id=run_id,
            checkpoint_ref=checkpoint_ref,
            user_id=user_id,
            interruptions=normalized,
            expires_at=expiry,
        )

    async def claim(
        self,
        *,
        run_id: str,
        checkpoint_ref: str,
        user_id: str,
        decision: str,
        edited_arguments: dict | None,
        argument_diff: list | None,
        rejection_message: str | None,
    ) -> list[dict]:
        outcome, items = await self.repo.claim_checkpoint(
            run_id=run_id,
            checkpoint_ref=checkpoint_ref,
            user_id=user_id,
            decision=decision,
            edited_arguments=edited_arguments,
            argument_diff=argument_diff,
            rejection_message=rejection_message,
        )
        if outcome == "not_found":
            raise AgentApprovalError("APPROVAL_NOT_FOUND", "Approval not found", 404)
        if outcome == "expired":
            raise AgentApprovalError("APPROVAL_EXPIRED", "Approval has expired", 410)
        if outcome != "claimed":
            raise AgentApprovalError("APPROVAL_CONFLICT", "Approval is already being resolved", 409)
        return items

    @staticmethod
    def _parse_expiry(value: str | None) -> datetime:
        if not value:
            return datetime.utcnow() + timedelta(hours=24)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError as exc:
            raise AgentApprovalError("APPROVAL_EXPIRY_INVALID", "Approval expiry is invalid", 422) from exc
