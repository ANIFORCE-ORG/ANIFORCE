"""New Agent run execution and SDK event streaming."""

import asyncio
from time import perf_counter
from typing import AsyncIterator
from uuid import uuid4

from loguru import logger

from app.agent.lifecycle_hooks import WorkspaceRunHooks
from app.agent.prompts import workspace_instructions
from app.agent.workspace_context import WorkspaceRunContext
from app.core.errors import AppError, AgentErrorCode, unexpected_error_payload
from app.core.metrics import AGENT_RUN_DURATION, AGENT_RUNS, observe_tokens
from app.runtime.mcp_context import mcp_connection
from app.runtime.sessions import RuntimeSessionOwnerMismatch, RuntimeSessionStore
from app.runtime.workspace_tool import request_workspace_projection


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


class RunExecutorMixin:
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

        try:
            run_logger.bind(event="agent.run.started").info(
                "Agent run started: task_type={}", task_type
            )
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

                trace_context = {
                    "workflow_name": "aniforce.agent.run",
                    "session_id": effective_session_id,
                    "user_id": user_id,
                    "tags": ["aniforce", task_type, "initial"],
                    "metadata": {
                        "run_id": run_id,
                        "session_id": effective_session_id,
                        "task_type": task_type,
                        "execution_kind": "initial",
                        "model": self.adapter.model,
                        "api_mode": self.adapter.api_mode,
                    },
                }
                with self.adapter.trace_scope(trace_context):
                    run_logger.debug("[RUNTIME] Executing Agent...")
                    run_streamed_start = perf_counter()
                    result = await self.adapter.run_streamed(
                        agent=agent,
                        input_text=user_input,
                        session=session,
                        context=workspace_context,
                        hooks=WorkspaceRunHooks(),
                        trace_context=trace_context,
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
                AGENT_RUNS.labels("initial", task_type, "requires_action").inc()
                AGENT_RUN_DURATION.labels("initial", task_type).observe(perf_counter() - run_start)
                run_logger.bind(
                    event="agent.run.requires_action",
                    checkpoint_id=checkpoint["id"],
                ).info(
                    "Agent run requires action: duration_ms={}", _elapsed_ms(run_start)
                )
                return

            usage = self.adapter._extract_usage(result) if result else {}
            sequence += 1
            yield {
                "event": "runtime.completed",
                "data": {"final_output": getattr(result, "final_output", None), "usage": usage},
                "sequence": sequence,
            }
            AGENT_RUNS.labels("initial", task_type, "completed").inc()
            AGENT_RUN_DURATION.labels("initial", task_type).observe(perf_counter() - run_start)
            observe_tokens("initial", usage)
            run_logger.bind(event="agent.run.completed", **usage).info(
                "Agent run completed: duration_ms={} total_tokens={}",
                _elapsed_ms(run_start),
                usage.get("totalTokens", 0),
            )

        except asyncio.CancelledError:
            AGENT_RUNS.labels("initial", task_type, "cancelled").inc()
            AGENT_RUN_DURATION.labels("initial", task_type).observe(perf_counter() - run_start)
            run_logger.bind(event="agent.run.cancelled").warning("Agent run cancelled")
            sequence += 1
            yield {
                "event": "runtime.aborted",
                "data": {"message": "Run cancelled by user"},
                "sequence": sequence,
            }

        except RuntimeSessionOwnerMismatch:
            AGENT_RUNS.labels("initial", task_type, "owner_mismatch").inc()
            AGENT_RUN_DURATION.labels("initial", task_type).observe(perf_counter() - run_start)
            run_logger.bind(event="agent.run.owner_mismatch").warning(
                "Agent run session ownership mismatch"
            )
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
            AGENT_RUNS.labels("initial", task_type, "failed").inc()
            AGENT_RUN_DURATION.labels("initial", task_type).observe(perf_counter() - run_start)
            run_logger.bind(event="agent.run.failed", error_code=e.code.value).error(
                "Agent run failed: {}", e.message
            )
            sequence += 1
            yield {
                "event": "runtime.error",
                "data": e.to_dict(),
                "sequence": sequence,
            }

        except Exception as e:
            AGENT_RUNS.labels("initial", task_type, "failed").inc()
            AGENT_RUN_DURATION.labels("initial", task_type).observe(perf_counter() - run_start)
            run_logger.bind(event="agent.run.failed").exception(
                "Agent run failed unexpectedly: {}", e
            )
            sequence += 1
            yield {
                "event": "runtime.error",
                "data": unexpected_error_payload(),
                "sequence": sequence,
            }

