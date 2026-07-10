"""
Agent Runtime

负责执行 Agent 任务，管理生命周期，推送 SDK 原生事件流
"""

import asyncio
import json
from time import perf_counter
from typing import Annotated, AsyncIterator, Optional
from uuid import uuid4
from contextlib import asynccontextmanager

from loguru import logger
from agents import RunContextWrapper, RunState, function_tool

from app.agent.openai_adapter import OpenAISDKAdapter
from app.agent.workspace_context import WorkspaceRunContext
from app.agent.lifecycle_hooks import WorkspaceRunHooks
from app.agent.prompts import workspace_instructions
from app.agent.checkpoints import (
    RuntimeCheckpointStore,
    interruption_to_dict,
    serialize_workspace_context_for_checkpoint,
)
from app.agent.runtime_sessions import RuntimeSessionOwnerMismatch, RuntimeSessionStore
from app.core.errors import AppError, AgentErrorCode, unexpected_error_payload
from app.core.tracing import get_tracer


APPROVAL_REQUIRED_TOOL_NAMES = [
    # 项目管理
    "create_project",
    "update_project",
    "delete_project",
    # 广告计划管理
    "create_campaign",
    "update_campaign",
    "update_campaign_status",
    "delete_campaign",
    # 素材管理
    "create_material",
    "update_material",
    "delete_material",
    # 关联/解绑操作（P0 修复：增加审批）
    "add_material_to_campaign",
    "remove_material_from_campaign",
    "add_material_to_project",
    "remove_material_from_project",
]


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


@function_tool
async def request_workspace_projection(
    ctx: RunContextWrapper[WorkspaceRunContext],
    surface: Annotated[str, "必须匹配刚刚查询结果的 Workspace surface：project.list、project.detail、campaign.list、campaign.detail、campaign.materials、material.list、material.detail、material.image"],
    reason: Annotated[str, "为什么用户需要在右侧 Workspace 查看这个结果"],
) -> str:
    """请求把刚刚查询到的业务结果展示到右侧 Workspace。

    浏览、查看、列出、打开业务对象时，在完成对应查询工具后必须调用本工具。
    surface 映射：
    - 项目：list_projects -> project.list, get_project_detail -> project.detail
    - 广告计划：list_campaigns -> campaign.list, get_campaign_detail -> campaign.detail, get_campaign_materials -> campaign.materials
    - 素材：list_materials -> material.list, get_material_detail -> material.detail, get_material_image -> material.image, list_available_images -> material.list

    当前没有 task 专用 surface；任务/执行状态类问题不要调用本工具。
    分析、诊断、对比、多上下文任务不要调用本工具，除非用户明确要求把某个结果放到右侧查看。
    审批类操作（包括关联/解绑）会自动投影，不需要调用本工具。
    """
    allowed_surfaces = {"project.list", "project.detail", "campaign.list", "campaign.detail", "campaign.materials", "material.list", "material.detail", "material.image"}
    if surface not in allowed_surfaces:
        return json.dumps(
            {
                "accepted": False,
                "surface": surface,
                "reason": "unsupported_surface",
                "message": "当前 Workspace 不支持该投影类型。",
            },
            ensure_ascii=False,
        )

    request = {
        "surface": surface,
        "reason": reason,
        "run_id": ctx.context.run_id,
        "session_id": ctx.context.session_id,
    }
    ctx.context.workspace_projection_requests.append(request)
    return json.dumps({"accepted": True, **request}, ensure_ascii=False)


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
    
    @asynccontextmanager
    async def _mcp_connection(
        self,
        *,
        auth_token: str,
        session_id: str,
        run_id: str,
        user_id: str,
    ):
        """MCP 连接上下文管理器（连本进程 /mcp + 多租户隔离）。"""
        from agents.mcp import MCPServerStreamableHttp, MCPToolMetaContext
        from app.config.settings import get_settings

        settings = get_settings()
        mcp_url = f"http://127.0.0.1:{settings.PORT}/mcp"
        jwt_token = auth_token

        def _meta_resolver(ctx: MCPToolMetaContext) -> dict[str, str] | None:
            """每次 MCP 工具调用前注入 jwt_token 和 run/session 元信息"""
            meta: dict[str, str] = {}
            if jwt_token:
                meta["jwt_token"] = jwt_token
            if session_id:
                meta["session_id"] = session_id
            if run_id:
                meta["run_id"] = run_id
            if user_id:
                meta["user_id"] = user_id
            return meta or None

        mcp_server = None
        mcp_servers = []
        mcp_start = perf_counter()
        perf_log = logger.bind(
            session_id=session_id,
            user_id=user_id,
            run_id=run_id,
        )

        try:
            mcp_server = MCPServerStreamableHttp(
                name="ANIFORCE Tools",
                params={
                    "url": mcp_url,
                    "timeout": 30,
                },
                cache_tools_list=True,
                max_retry_attempts=2,
                require_approval={
                    "always": {"tool_names": APPROVAL_REQUIRED_TOOL_NAMES},
                },
                tool_meta_resolver=_meta_resolver,
            )
            await mcp_server.__aenter__()
            mcp_servers.append(mcp_server)
            logger.debug(f"[RUNTIME] MCP server connected: {mcp_url} (jwt={'<present>' if jwt_token else '<missing>'})")
            perf_log.debug(
                "[PERF][agent_first_token] runtime.mcp_connected mcp_connect_ms={}",
                _elapsed_ms(mcp_start),
            )

            yield mcp_servers

        finally:
            if mcp_server:
                try:
                    await mcp_server.__aexit__(None, None, None)
                    logger.debug(f"[RUNTIME] MCP server disconnected")
                except Exception as e:
                    logger.warning(f"[RUNTIME] MCP cleanup error: {e}")
    
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

            async with self._mcp_connection(
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

    async def _create_hitl_checkpoint(
        self,
        *,
        result,
        workspace_context: WorkspaceRunContext,
        session_id: str,
        user_id: str,
        run_id: str,
    ) -> dict:
        state = result.to_state()
        run_state = state.to_json(
            context_serializer=serialize_workspace_context_for_checkpoint,
            strict_context=True,
        )
        interruptions = [interruption_to_dict(item) for item in (getattr(result, "interruptions", []) or [])]
        engine = self.adapter._get_agent_db_engine(self.agent_runtime_db_url)
        store = RuntimeCheckpointStore(engine)
        return await store.create(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            interruptions=interruptions,
            run_state=run_state,
        )

    async def claim_checkpoint_for_resume(
        self,
        *,
        checkpoint_id: str,
        user_id: str,
        edited_arguments: dict | None = None,
        argument_diff: list | None = None,
    ) -> dict:
        engine = self.adapter._get_agent_db_engine(self.agent_runtime_db_url)
        return await RuntimeCheckpointStore(engine).claim_or_raise(
            checkpoint_id,
            user_id,
            approved_arguments=edited_arguments,
            argument_diff=argument_diff,
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
    ) -> AsyncIterator[dict]:
        """Resume a paused SDK HITL checkpoint."""
        engine = self.adapter._get_agent_db_engine(self.agent_runtime_db_url)
        store = RuntimeCheckpointStore(engine)
        checkpoint = claimed_checkpoint or await self.claim_checkpoint_for_resume(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            edited_arguments=edited_arguments,
            argument_diff=argument_diff,
        )

        safe_context = checkpoint["run_state"].get("context", {}).get("value") or {}
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
            business_context_summary=safe_context.get("business_context_summary", ""),
            ui_snapshot=safe_context.get("ui_snapshot") or {},
            session_state=safe_context.get("session_state") or {},
            task_type=safe_context.get("task_type", "conversation"),
            approved_arguments_by_call_id=approved_args_by_call_id,
            argument_diff=argument_diff or [],
        )

        sequence = 0
        run_logger = logger.bind(user_id=user_id, session_id=checkpoint["session_id"], run_id=checkpoint["run_id"], checkpoint_id=checkpoint_id)
        try:
            async with self._mcp_connection(
                auth_token=auth_token,
                session_id=checkpoint["session_id"],
                run_id=checkpoint["run_id"],
                user_id=user_id,
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
                    await store.mark_status(checkpoint_id, user_id, "completed", expected_status="resuming")
                    sequence += 1
                    yield {
                        "event": "runtime.requires_action",
                        "data": {
                            "run_id": checkpoint["run_id"],
                            "session_id": checkpoint["session_id"],
                            "checkpoint_id": new_checkpoint["id"],
                            "interruptions": new_checkpoint["interruptions"],
                        },
                        "sequence": sequence,
                    }
                    return

                await store.mark_status(checkpoint_id, user_id, "completed", expected_status="resuming")
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
            )
            raise

    async def get_session_history(self, session_id: str, user_id: str) -> list[dict]:
        """从 agent.db SQLAlchemySession 读取当前用户的 SDK 原生对话历史。"""
        from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession

        sdk_session_id = session_id
        if self.adapter.api_mode == "chat_completions":
            sdk_session_id = f"chat_completions:{session_id}"

        engine = self.adapter._get_agent_db_engine(self.agent_runtime_db_url)
        await RuntimeSessionStore(engine).require_owner(session_id, user_id)
        session = SQLAlchemySession(sdk_session_id, engine=engine, create_tables=False)
        items = await session.get_items()
        return [item if isinstance(item, dict) else dict(item) for item in items]

