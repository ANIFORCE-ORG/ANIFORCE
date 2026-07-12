"""Facade for Agent run, resume, checkpoint, control, and history operations."""

from app.agent.openai_adapter import OpenAISDKAdapter
from app.agent.workspace_context import WorkspaceRunContext
from app.core.tracing import get_tracer
from app.runtime.checkpoints.service import RuntimeCheckpointService
from app.runtime.controls import RuntimeRunControlStore
from app.runtime.history import RuntimeHistoryReader
from app.runtime.resume_executor import ResumeExecutorMixin
from app.runtime.run_executor import RunExecutorMixin


class AgentRuntime(RunExecutorMixin, ResumeExecutorMixin):
    """Stable API facade over the Runtime execution components."""

    def __init__(
        self,
        adapter: OpenAISDKAdapter,
        agent_runtime_db_url: str = "sqlite+aiosqlite:///runtime/agent/agent.db",
        enable_tracing: bool = True,
    ) -> None:
        self.adapter = adapter
        self.agent_runtime_db_url = agent_runtime_db_url
        self.enable_tracing = enable_tracing
        self.tracer = get_tracer() if enable_tracing else None

    def run_control_store(self) -> RuntimeRunControlStore:
        engine = self.adapter._get_agent_db_engine(self.agent_runtime_db_url)
        return RuntimeRunControlStore(engine)

    async def _create_hitl_checkpoint(
        self,
        *,
        result,
        workspace_context: WorkspaceRunContext,
        session_id: str,
        user_id: str,
        run_id: str,
    ) -> dict:
        engine = self.adapter._get_agent_db_engine(self.agent_runtime_db_url)
        return await RuntimeCheckpointService(engine).create(
            result=result,
            workspace_context=workspace_context,
            session_id=session_id,
            user_id=user_id,
            run_id=run_id,
        )

    async def claim_checkpoint_for_resume(
        self,
        *,
        checkpoint_id: str,
        user_id: str,
        edited_arguments: dict | None = None,
        argument_diff: list | None = None,
        claimed_by: str | None = None,
    ) -> dict:
        engine = self.adapter._get_agent_db_engine(self.agent_runtime_db_url)
        return await RuntimeCheckpointService(engine).claim(
            checkpoint_id,
            user_id,
            edited_arguments=edited_arguments,
            argument_diff=argument_diff,
            claimed_by=claimed_by,
        )

    async def get_session_history(self, session_id: str, user_id: str) -> list[dict]:
        return await RuntimeHistoryReader(self.adapter, self.agent_runtime_db_url).read(session_id, user_id)
