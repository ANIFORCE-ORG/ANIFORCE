"""
Agent Runtime

负责执行 Agent 任务，管理生命周期，推送 SDK 原生事件流
"""

import asyncio
from time import perf_counter
from typing import AsyncIterator, Optional
from uuid import uuid4

from loguru import logger
from agents import RunState

from app.agent.openai_adapter import OpenAISDKAdapter
from app.agent.workspace_context import WorkspaceRunContext
from app.agent.lifecycle_hooks import WorkspaceRunHooks
from app.agent.prompts import workspace_instructions
from app.runtime.sessions import RuntimeSessionOwnerMismatch, RuntimeSessionStore
from app.runtime.controls import RuntimeRunControlStore
from app.core.errors import AppError, AgentErrorCode, unexpected_error_payload
from app.core.tracing import get_tracer
from app.runtime.checkpoints.service import RuntimeCheckpointService
from app.runtime.history import RuntimeHistoryReader
from app.runtime.mcp_context import mcp_connection
from app.runtime.workspace_tool import request_workspace_projection


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


class AgentRuntime:
    """Agent 运行时"""
    
    def __init__(
        self,
        adapter: OpenAISDKAdapter,
        agent_runtime_db_url: str = "sqlite+aiosqlite:///runtime/agent/agent.db",
        enable_tracing: bool = True,
    ):
        self.adapter = adapter
        self.agent_runtime_db_url = agent_runtime_db_url
        self.enable_tracing = enable_tracing
        self.tracer = get_tracer() if enable_tracing else None
    
    async def run(
        self,
        *,
        user_input: str,
        session_id: str,
        user_id: str,
        task_type: str = "conversation",
        auth_token: str = "",
        business_context_summary: str = "",
        ui_snapshot: dict | None = None,
        session_state: dict | None = None,
        run_id: str = "",
    ) -> AsyncIterator[dict]:
        """运行 WorkspaceAgent，直接输出 SDK 原生事件 envelope。"""
        run_start = perf_counter()
        run_logger = logger.bind(user_id=user_id, session_id=session_id, run_id=run_id)
        sequence = 0
        result = None

        trace_ctx = None
        if self.tracer:
            trace_ctx = self.tracer.trace_task(run_id or session_id, user_id, task_type)
            trace_ctx.__enter__()

        try:
            run_logger.debug("[RUNTIME] Run started: {}", task_type)
            yield {
                "event": "runtime.started",
                "data": {"task_type": task_type, "user_input": user_input},
                "sequence": sequence,
            }

            session_start = perf_counter()
            effective_session_id = session_id or f"session_{uuid4().hex[:16]}"
            engine = self.adapter._get_agent_db_engine(self.agent_runtime_db_url)
            await RuntimeSessionStore(engine).register_or_validate(effective_session_id, user_id)
            session = self.adapter.create_session(effective_session_id, self.agent_runtime_db_url)
            run_logger.debug(
                "[PERF][agent_first_token] runtime.session_ready total_ms={} session_create_ms={}",
                _elapsed_ms(run_start),
                _elapsed_ms(session_start),
            )

            async with mcp_connection(
                auth_token=auth_token,
                session_id=effective_session_id,
                run_id=run_id,
                user_id=user_id,
            ) as mcp_servers:
                agent_create_start = perf_counter()
                workspace_context = WorkspaceRunContext(
                    user_id=user_id,
                    session_id=effective_session_id,
                    run_id=run_id,
                    auth_token=auth_token,
                    business_context_summary=business_context_summary,
                    ui_snapshot=ui_snapshot or {},
                    session_state=session_state or {},
                    task_type=task_type,
                )
                agent = self.adapter.create_agent(
                    name="ANIFORCE Assistant",
                    instructions=workspace_instructions,
                    mcp_servers=mcp_servers,
                    tools=[request_workspace_projection],
                )
                run_logger.debug(
                    "[PERF][agent_first_token] runtime.agent_ready total_ms={} agent_create_ms={}",
                    _elapsed_ms(run_start),
                    _elapsed_ms(agent_create_start),
                )

                run_logger.debug("[RUNTIME] Executing Agent...")
                run_streamed_start = perf_counter()
                result = await self.adapter.run_streamed(
                    agent=agent,
                    input_text=user_input,
                    session=session,
                    context=workspace_context,
                    hooks=WorkspaceRunHooks(),
                )
                run_logger.debug(
                    "[PERF][agent_first_token] runtime.run_streamed_returned total_ms={} run_streamed_wait_ms={}",
                    _elapsed_ms(run_start),
                    _elapsed_ms(run_streamed_start),
                )

                first_event_seen = False
                stream_events_start = perf_counter()
                async for sdk_event in self.adapter.stream_events(result):
                    sequence += 1
                    if not first_event_seen:
                        first_event_seen = True
                        run_logger.debug(
                            "[PERF][agent_first_token] runtime.first_sdk_event total_ms={} stream_events_wait_ms={} event_type={}",
                            _elapsed_ms(run_start),
                            _elapsed_ms(stream_events_start),
                            sdk_event.get("type", "unknown"),
                        )
                    yield {
                        "event": str(sdk_event.get("type") or "sdk.event"),
                        "data": sdk_event,
                        "sequence": sequence,
                    }

            interruptions = list(getattr(result, "interruptions", []) or []) if result else []
            if interruptions:
                checkpoint = await self._create_hitl_checkpoint(
                    result=result,
                    workspace_context=workspace_context,
                    session_id=effective_session_id,
                    user_id=user_id,
                    run_id=run_id,
                )
                sequence += 1
                yield {
                    "event": "runtime.requires_action",
                    "data": {
                        "run_id": run_id,
                        "session_id": effective_session_id,
                        "checkpoint_id": checkpoint["id"],
                        "interruptions": checkpoint["interruptions"],
                        "expires_at": checkpoint["expires_at"],
                    },
                    "sequence": sequence,
                }
                run_logger.debug("[RUNTIME] Run requires action: checkpoint={}", checkpoint["id"])
                return

            usage = self.adapter._extract_usage(result) if result else {}
            sequence += 1
            yield {
                "event": "runtime.completed",
                "data": {"final_output": getattr(result, "final_output", None), "usage": usage},
                "sequence": sequence,
            }
            run_logger.debug("[RUNTIME] Run completed successfully")

        except asyncio.CancelledError:
            run_logger.warning("[RUNTIME] Run cancelled")
            sequence += 1
            yield {
                "event": "runtime.aborted",
                "data": {"message": "Run cancelled by user"},
                "sequence": sequence,
            }

        except RuntimeSessionOwnerMismatch:
            run_logger.warning("[RUNTIME] Session ownership mismatch")
            sequence += 1
            yield {
                "event": "runtime.error",
                "data": AppError(
                    AgentErrorCode.TASK_PERMISSION_DENIED,
                    "Session does not belong to current user",
                ).to_dict(),
                "sequence": sequence,
            }

        except AppError as e:
            run_logger.error("[RUNTIME] AppError: {} - {}", e.code.value, e.message)
            sequence += 1
            yield {
                "event": "runtime.error",
                "data": e.to_dict(),
                "sequence": sequence,
            }

        except Exception as e:
            run_logger.exception("[RUNTIME] Unexpected error: {}", e)
            sequence += 1
            yield {
                "event": "runtime.error",
                "data": unexpected_error_payload(),
                "sequence": sequence,
            }

        finally:
            if trace_ctx:
                trace_ctx.__exit__(None, None, None)

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
        run_logger = logger.bind(user_id=user_id, session_id=checkpoint["session_id"], run_id=checkpoint["run_id"], checkpoint_id=checkpoint_id)
        try:
            async with mcp_connection(
                auth_token=auth_token,
                session_id=checkpoint["session_id"],
                run_id=checkpoint["run_id"],
                user_id=user_id,
                checkpoint_id=checkpoint_id,
                tool_call_ids_by_name=tool_call_ids_by_name,
            ) as mcp_servers:
                agent = self.adapter.create_agent(
                    name="ANIFORCE Assistant",
                    instructions=workspace_instructions,
                    mcp_servers=mcp_servers,
                    tools=[request_workspace_projection],
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

                result = await self.adapter.run_streamed(
                    agent=agent,
                    input_text=state,
                    session=session,
                    hooks=WorkspaceRunHooks(),
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
                    yield {
                        "event": "runtime.requires_action",
                        "data": {
                            "run_id": checkpoint["run_id"],
                            "session_id": checkpoint["session_id"],
                            "checkpoint_id": new_checkpoint["id"],
                            "interruptions": new_checkpoint["interruptions"],
                            "expires_at": new_checkpoint["expires_at"],
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
                    "data": {"final_output": getattr(result, "final_output", None), "usage": usage},
                    "sequence": sequence,
                }
                run_logger.debug("[RUNTIME] Checkpoint resumed")
        except Exception:
            run_logger.exception("[RUNTIME] Checkpoint resume failed")
            await store.mark_status(
                checkpoint_id,
                user_id,
                "failed",
                error=unexpected_error_payload(message="Checkpoint resume failed"),
                expected_status="resuming",
                claimed_by=claimed_by,
            )
            raise

    async def get_session_history(self, session_id: str, user_id: str) -> list[dict]:
        return await RuntimeHistoryReader(self.adapter, self.agent_runtime_db_url).read(session_id, user_id)

