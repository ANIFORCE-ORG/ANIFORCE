"""Agent run execution log service."""

from uuid import uuid4

from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository

ACTIVE_RUN_STATUSES = {"queued", "running", "requires_action"}
TERMINAL_RUN_STATUSES = {"completed", "error", "cancelled"}


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
        )
        return run, False

    async def get(self, run_id: str, user_id: str) -> dict:
        run = await self.repo.get(run_id, user_id)
        if not run:
            raise AgentRunError("RUN_NOT_FOUND", "Run not found", status_code=404)
        return run

    async def mark_running(self, run_id: str, user_id: str) -> dict | None:
        run = await self.get(run_id, user_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            return run
        return await self.repo.mark_status(run_id, user_id, "running")

    async def mark_completed(self, run_id: str, user_id: str, usage: dict | None = None) -> dict | None:
        run = await self.get(run_id, user_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            return run
        return await self.repo.mark_status(run_id, user_id, "completed", usage=usage)

    async def mark_requires_action(self, run_id: str, user_id: str, checkpoint_ref: str) -> dict | None:
        run = await self.get(run_id, user_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            return run
        return await self.repo.mark_status(run_id, user_id, "requires_action", checkpoint_ref=checkpoint_ref)

    async def mark_error(self, run_id: str, user_id: str, error: dict) -> dict | None:
        run = await self.get(run_id, user_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            return run
        return await self.repo.mark_status(run_id, user_id, "error", error=error)

    async def mark_cancelled(self, run_id: str, user_id: str) -> dict | None:
        run = await self.get(run_id, user_id)
        if run["status"] not in ACTIVE_RUN_STATUSES:
            return run
        return await self.repo.mark_status(run_id, user_id, "cancelled")
