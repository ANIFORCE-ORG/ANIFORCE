"""Agent run state machine service."""

from uuid import uuid4

from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository

ACTIVE_RUN_STATUSES = {"queued", "resume_queued", "running", "requires_action", "cancel_requested"}
TERMINAL_RUN_STATUSES = {"completed", "error", "cancelled", "expired"}


class AgentRunError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, retryable: bool = False, run: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.run = run
        super().__init__(message)


class AgentRunService:
    def __init__(self, repo: SqliteAgentRunRepository):
        self.repo = repo

    async def create_or_reuse(
        self,
        *,
        session_id: str,
        user_id: str,
        input_text: str,
        idempotency_key: str | None,
        execution_context: dict | None = None,
    ) -> tuple[dict, bool]:
        existing = await self.repo.get_by_idempotency(user_id, session_id, idempotency_key)
        if existing:
            return existing, True
        active = await self.repo.get_active_for_session(user_id, session_id)
        if active:
            raise AgentRunError(
                "SESSION_RUN_IN_PROGRESS",
                "Session has a run in progress",
                status_code=409,
                retryable=True,
                run=active,
            )
        run = await self.repo.create(
            run_id=f"run_{uuid4().hex}",
            session_id=session_id,
            user_id=user_id,
            input_text=input_text,
            idempotency_key=idempotency_key,
            status="queued",
            execution_context=execution_context,
        )
        return run, False

    async def get(self, run_id: str, user_id: str) -> dict:
        run = await self.repo.get(run_id, user_id)
        if not run:
            raise AgentRunError("RUN_NOT_FOUND", "Run not found", status_code=404)
        return run

    async def mark_running(self, run_id: str, user_id: str) -> dict | None:
        run = await self.get(run_id, user_id)
        if run["status"] in TERMINAL_RUN_STATUSES or run["status"] == "running":
            return run
        event_type = "run.resuming" if run["status"] in {"requires_action", "resume_queued"} else "run.started"
        return await self.repo.transition_with_event(
            run_id, user_id, "running", event_type=event_type,
            payload={"run_id": run_id, "status": "running"}, is_terminal=False,
        )

    async def mark_completed(
        self,
        run_id: str,
        user_id: str,
        usage: dict | None = None,
        final_output: str | None = None,
        lease_owner: str | None = None,
    ) -> dict | None:
        run = await self.get(run_id, user_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            return run
        return await self.repo.transition_with_event(
            run_id, user_id, "completed", event_type="run.completed",
            payload={"run_id": run_id, "status": "completed", "usage": usage or {}, "final_output": final_output},
            is_terminal=True, usage=usage, checkpoint_ref="", lease_owner=lease_owner,
        )

    async def mark_requires_action(
        self,
        run_id: str,
        user_id: str,
        checkpoint_ref: str,
        event_payload: dict | None = None,
        lease_owner: str | None = None,
    ) -> dict | None:
        run = await self.get(run_id, user_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            return run
        return await self.repo.transition_with_event(
            run_id, user_id, "requires_action", event_type="run.requires_action",
            payload=event_payload or {"run_id": run_id, "status": "requires_action", "checkpoint_ref": checkpoint_ref},
            is_terminal=False, checkpoint_ref=checkpoint_ref, lease_owner=lease_owner,
        )

    async def mark_error(
        self,
        run_id: str,
        user_id: str,
        error: dict,
        lease_owner: str | None = None,
    ) -> dict | None:
        run = await self.get(run_id, user_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            return run
        return await self.repo.transition_with_event(
            run_id, user_id, "error", event_type="run.error",
            payload={"run_id": run_id, "status": "error", "error": error},
            is_terminal=True, error=error, checkpoint_ref="", lease_owner=lease_owner,
        )

    async def mark_cancelled(
        self,
        run_id: str,
        user_id: str,
        lease_owner: str | None = None,
    ) -> dict | None:
        run = await self.get(run_id, user_id)
        if run["status"] not in ACTIVE_RUN_STATUSES:
            return run
        return await self.repo.transition_with_event(
            run_id, user_id, "cancelled", event_type="run.cancelled",
            payload={"run_id": run_id, "status": "cancelled"},
            is_terminal=True, checkpoint_ref="", lease_owner=lease_owner,
        )

    async def enqueue_resume(self, run_id: str, user_id: str, payload: dict) -> dict:
        run = await self.repo.enqueue_resume(run_id, user_id, payload)
        if not run or run["status"] != "resume_queued":
            raise AgentRunError("RUN_RESUME_CONFLICT", "Run cannot be queued for resume", 409)
        return run

    async def request_cancel(self, run_id: str, user_id: str) -> dict:
        run = await self.repo.request_cancel(run_id, user_id)
        if not run:
            raise AgentRunError("RUN_NOT_FOUND", "Run not found", 404)
        return run
