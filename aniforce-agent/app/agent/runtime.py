"""
Agent Runtime

负责执行 Agent 任务，管理生命周期，推送 SDK 原生事件流
"""

import asyncio
from time import perf_counter
from typing import AsyncIterator, Optional
from uuid import uuid4
from contextlib import asynccontextmanager

from loguru import logger

from app.agent.openai_adapter import OpenAISDKAdapter
from app.core.errors import AppError, AgentErrorCode
from app.core.tracing import get_tracer
from app.agent.prompts import SystemPromptManager


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
                instructions = self._get_system_prompt(business_context_summary)
                agent = self.adapter.create_agent(
                    name="ANIFORCE Assistant",
                    instructions=instructions,
                    mcp_servers=mcp_servers,
                )
                run_logger.debug(
                    "[PERF][agent_first_token] runtime.agent_ready total_ms={} agent_create_ms={} prompt_chars={}",
                    _elapsed_ms(run_start),
                    _elapsed_ms(agent_create_start),
                    len(instructions),
                )

                run_logger.debug("[RUNTIME] Executing Agent...")
                run_streamed_start = perf_counter()
                result = await self.adapter.run_streamed(
                    agent=agent,
                    input_text=user_input,
                    session=session,
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
                "data": {"code": AgentErrorCode.UNKNOWN_ERROR.value, "message": str(e)},
                "sequence": sequence,
            }

        finally:
            if trace_ctx:
                trace_ctx.__exit__(None, None, None)

    def _get_system_prompt(self, business_context_summary: str = "") -> str:
        """返回 LLM 可见的 system prompt。"""
        available_mcp_tools = [
            "list_projects",
            "create_project",
            "get_project_detail",
            "update_project",
            "delete_project",
            "list_campaigns",
            "create_campaign",
            "get_campaign_detail",
            "update_campaign",
            "delete_campaign",
        ]
        base_prompt = SystemPromptManager.get_plan_execute_prompt(
            available_mcp_tools=available_mcp_tools
        )
        if not business_context_summary:
            return base_prompt
        return (
            f"{base_prompt}\n\n"
            "---\n"
            "# Backend Business Context\n"
            "以下内容由 backend Session State Manager 构建，用于说明当前业务现场。"
            "backend DB 是业务事实源；如需修改业务数据，必须通过 MCP 工具调用 backend REST。\n\n"
            f"{business_context_summary}\n"
            "---"
        )
