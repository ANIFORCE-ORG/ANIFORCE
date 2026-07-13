"""Checkpoint resume execution and SDK event streaming."""

from time import perf_counter
from typing import AsyncIterator

from agents import RunState
from loguru import logger

from app.agent.business_skills.loader_tool import load_business_skill, update_business_skill_state
from app.agent.business_skills.state import build_task_state
from app.agent.lifecycle_hooks import WorkspaceRunHooks
from app.agent.prompts import workspace_instructions
from app.agent.workspace_context import WorkspaceRunContext
from app.core.errors import AppError, AgentErrorCode, unexpected_error_payload
from app.config.settings import get_settings
from app.core.metrics import AGENT_RUN_DURATION, AGENT_RUNS, observe_tokens
from app.runtime.checkpoints.service import RuntimeCheckpointService
from app.runtime.mcp_context import mcp_connection
from app.runtime.workspace_tool import request_workspace_projection


class ResumeExecutorMixin:
    async def resume_checkpoint(
        self,
        *,
        checkpoint_id: str,
        user_id: str,
        decision: str,
        auth_token: str = "",
        rejection_message: str | None = None,
        always: bool = False,
        edited_arguments: dict | None = None,
        argument_diff: list | None = None,
        claimed_checkpoint: dict | None = None,
        claimed_by: str | None = None,
        context_override: dict | None = None,
    ) -> AsyncIterator[dict]:
        """Resume a paused SDK HITL checkpoint."""
        engine = self.adapter._get_agent_db_engine(self.agent_runtime_db_url)
        store = RuntimeCheckpointService(engine).store
        checkpoint = claimed_checkpoint or await self.claim_checkpoint_for_resume(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            edited_arguments=edited_arguments,
            argument_diff=argument_diff,
            claimed_by=claimed_by,
        )

        safe_context = checkpoint["run_state"].get("context", {}).get("value") or {}
        latest_context = context_override or {}
        # 构建 approved_arguments_by_call_id：用 interruption 的 call_id 关联
        approved_args_by_call_id: dict[str, dict] = {}
        if edited_arguments:
            for interruption in checkpoint.get("interruptions", []):
                call_id = interruption.get("call_id")
                if call_id:
                    approved_args_by_call_id[call_id] = edited_arguments

        workspace_context = WorkspaceRunContext(
            user_id=checkpoint["user_id"],
            session_id=checkpoint["session_id"],
            run_id=checkpoint["run_id"],
            auth_token=auth_token,
            business_context_summary=latest_context.get("business_context_summary", safe_context.get("business_context_summary", "")),
            ui_snapshot=latest_context.get("ui_snapshot", safe_context.get("ui_snapshot")) or {},
            session_state=latest_context.get("session_state", safe_context.get("session_state")) or {},
            task_type=safe_context.get("task_type", "conversation"),
            approved_arguments_by_call_id=approved_args_by_call_id,
            argument_diff=argument_diff or [],
            selected_skill_ids=list(safe_context.get("selected_skill_ids") or []),
            selected_skill_versions=dict(safe_context.get("selected_skill_versions") or {}),
            skill_slots=dict(safe_context.get("skill_slots") or {}),
            skill_load_reason=safe_context.get("skill_load_reason"),
            skill_status=safe_context.get("skill_status"),
            skill_missing_slots=list(safe_context.get("skill_missing_slots") or []),
            skill_pending_question=safe_context.get("skill_pending_question"),
        )

        tool_call_ids_by_name: dict[str, str] = {}
        ambiguous_tool_names: set[str] = set()
        for interruption in checkpoint.get("interruptions", []):
            tool_name = str(interruption.get("tool_name") or "")
            call_id = str(interruption.get("call_id") or "")
            if not tool_name or not call_id:
                continue
            if tool_name in tool_call_ids_by_name:
                ambiguous_tool_names.add(tool_name)
            else:
                tool_call_ids_by_name[tool_name] = call_id
        for tool_name in ambiguous_tool_names:
            tool_call_ids_by_name.pop(tool_name, None)

        sequence = 0
        resume_start = perf_counter()
        run_logger = logger.bind(user_id=user_id, session_id=checkpoint["session_id"], run_id=checkpoint["run_id"], checkpoint_id=checkpoint_id)
        run_logger.bind(event="agent.run.resume_started").info(
            "Agent run resume started: decision={}", decision
        )
        try:
            async with mcp_connection(
                auth_token=auth_token,
                session_id=checkpoint["session_id"],
                run_id=checkpoint["run_id"],
                user_id=user_id,
                checkpoint_id=checkpoint_id,
                tool_call_ids_by_name=tool_call_ids_by_name,
            ) as mcp_servers:
                local_tools = [request_workspace_projection]
                if get_settings().ENABLE_BUSINESS_SKILLS:
                    local_tools.extend([load_business_skill, update_business_skill_state])
                agent = self.adapter.create_agent(
                    name="ANIFORCE Assistant",
                    instructions=workspace_instructions,
                    mcp_servers=mcp_servers,
                    tools=local_tools,
                )
                session = self.adapter.create_session(checkpoint["session_id"], self.agent_runtime_db_url)
                state = await RunState.from_json(
                    agent,
                    checkpoint["run_state"],
                    context_override=workspace_context,
                    strict_context=True,
                )
                for item in state.get_interruptions():
                    if decision == "approve":
                        state.approve(item, always_approve=always)
                    elif decision == "reject":
                        state.reject(item, rejection_message=rejection_message, always_reject=always)
                    else:
                        raise AppError(AgentErrorCode.UNKNOWN_ERROR, "decision must be approve or reject")

                trace_context = {
                    "workflow_name": "aniforce.agent.resume",
                    "session_id": checkpoint["session_id"],
                    "user_id": user_id,
                    "tags": ["aniforce", workspace_context.task_type, "resume"],
                    "metadata": {
                        "run_id": checkpoint["run_id"],
                        "session_id": checkpoint["session_id"],
                        "checkpoint_id": checkpoint_id,
                        "task_type": workspace_context.task_type,
                        "execution_kind": "resume",
                        "model": self.adapter.model,
                        "api_mode": self.adapter.api_mode,
                    },
                }
                with self.adapter.trace_scope(trace_context):
                    result = await self.adapter.run_streamed(
                        agent=agent,
                        input_text=state,
                        session=session,
                        hooks=WorkspaceRunHooks(),
                        trace_context=trace_context,
                    )
                    async for sdk_event in self.adapter.stream_events(result):
                        sequence += 1
                        yield {
                            "event": str(sdk_event.get("type") or "sdk.event"),
                            "data": sdk_event,
                            "sequence": sequence,
                        }

                if getattr(result, "interruptions", None):
                    new_checkpoint = await self._create_hitl_checkpoint(
                        result=result,
                        workspace_context=workspace_context,
                        session_id=checkpoint["session_id"],
                        user_id=user_id,
                        run_id=checkpoint["run_id"],
                    )
                    await store.mark_status(
                        checkpoint_id, user_id, "completed", expected_status="resuming", claimed_by=claimed_by
                    )
                    sequence += 1
                    AGENT_RUNS.labels("resume", workspace_context.task_type, "requires_action").inc()
                    AGENT_RUN_DURATION.labels("resume", workspace_context.task_type).observe(
                        perf_counter() - resume_start
                    )
                    yield {
                        "event": "runtime.requires_action",
                        "data": {
                            "run_id": checkpoint["run_id"],
                            "session_id": checkpoint["session_id"],
                            "checkpoint_id": new_checkpoint["id"],
                            "interruptions": new_checkpoint["interruptions"],
                            "expires_at": new_checkpoint["expires_at"],
                            "task_state": build_task_state(workspace_context, terminal_status="executing"),
                        },
                        "sequence": sequence,
                    }
                    return

                await store.mark_status(
                    checkpoint_id, user_id, "completed", expected_status="resuming", claimed_by=claimed_by
                )
                usage = self.adapter._extract_usage(result)
                sequence += 1
                yield {
                    "event": "runtime.completed",
                    "data": {
                        "final_output": getattr(result, "final_output", None),
                        "usage": usage,
                        "task_state": build_task_state(workspace_context, terminal_status="completed"),
                    },
                    "sequence": sequence,
                }
                AGENT_RUNS.labels("resume", workspace_context.task_type, "completed").inc()
                AGENT_RUN_DURATION.labels("resume", workspace_context.task_type).observe(
                    perf_counter() - resume_start
                )
                observe_tokens("resume", usage)
                run_logger.bind(event="agent.run.resume_completed", **usage).info(
                    "Agent run resume completed: total_tokens={}",
                    usage.get("totalTokens", 0),
                )
        except Exception:
            AGENT_RUNS.labels("resume", workspace_context.task_type, "failed").inc()
            AGENT_RUN_DURATION.labels("resume", workspace_context.task_type).observe(
                perf_counter() - resume_start
            )
            run_logger.bind(event="agent.run.resume_failed").exception(
                "Agent run checkpoint resume failed"
            )
            await store.mark_status(
                checkpoint_id,
                user_id,
                "failed",
                error=unexpected_error_payload(message="Checkpoint resume failed"),
                expected_status="resuming",
                claimed_by=claimed_by,
            )
            raise

