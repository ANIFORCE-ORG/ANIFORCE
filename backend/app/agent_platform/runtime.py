"""
Agent Runtime

负责执行 Agent 任务，管理生命周期，推送事件流
"""

import asyncio
from typing import AsyncIterator
from uuid import uuid4
from contextlib import asynccontextmanager

from loguru import logger

from .models import AgentTask, AgentTaskEvent, AgentTaskStatus, EventType
from .repositories.base import AgentTaskRepository
from .adapters.openai_adapter import OpenAISDKAdapter
from .errors import AppError, AgentErrorCode, ErrorCategory
from .tracing import get_tracer


class AgentRuntime:
    """Agent 运行时"""
    
    def __init__(
        self,
        adapter: OpenAISDKAdapter,
        repo: AgentTaskRepository,
        session_db_path: str = "runtime/agent/sessions.db",
        enable_tracing: bool = True,
    ):
        self.adapter = adapter
        self.repo = repo
        self.session_db_path = session_db_path
        self.enable_tracing = enable_tracing
        self.tracer = get_tracer() if enable_tracing else None
        logger.info(f"AgentRuntime initialized | tracing={enable_tracing}")
    
    @asynccontextmanager
    async def _mcp_connection(self, task: AgentTask):
        """MCP 连接上下文管理器"""
        from agents.mcp import MCPServerStreamableHttp
        from app.config.settings import get_settings
        
        settings = get_settings()
        auth_token = task.context.get("auth_token", "") if task.context else ""
        
        mcp_server = None
        mcp_servers = []
        
        try:
            if auth_token:
                mcp_server = MCPServerStreamableHttp(
                    name="ANIFORCE MCP",
                    params={
                        "url": f"{settings.BACKEND_BASE_URL}/api/v1/mcp",
                        "headers": {"authorization": f"Bearer {auth_token}"}
                    }
                )
                # 连接 MCP 服务器
                await mcp_server.__aenter__()
                mcp_servers.append(mcp_server)
                logger.debug(f"[RUNTIME] MCP server connected: {settings.BACKEND_BASE_URL}/api/v1/mcp")
            else:
                logger.debug(f"[RUNTIME] No auth token, MCP disabled")
            
            yield mcp_servers
            
        finally:
            # 清理 MCP 连接
            if mcp_server:
                try:
                    await mcp_server.__aexit__(None, None, None)
                    logger.debug(f"[RUNTIME] MCP server disconnected")
                except Exception as e:
                    logger.warning(f"[RUNTIME] MCP cleanup error: {e}")
    
    async def run_task(
        self,
        task: AgentTask,
        user_input: str,
    ) -> AsyncIterator[AgentTaskEvent]:
        """
        运行任务
        
        Args:
            task: AgentTask 实例
            user_input: 用户输入
            
        Yields:
            AgentTaskEvent（实时事件流）
        """
        task_logger = logger.bind(task_id=task.task_id, user_id=task.user_id)
        
        # 开始 Trace
        trace_ctx = None
        if self.tracer:
            trace_ctx = self.tracer.trace_task(task.task_id, task.user_id, task.task_type)
            trace_ctx.__enter__()
        
        try:
            task_logger.info(f"[RUNTIME] Task started: {task.task_type}")
            
            # 1. 更新状态为 running
            await self.repo.update_status(task.task_id, AgentTaskStatus.RUNNING)
            
            # 2. 推送 runtime.started 事件
            sequence = await self.repo.count_task_events(task.task_id)
            started_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_STARTED,
                payload={"task_type": task.task_type, "user_input": user_input},
                sequence=sequence,
            )
            await self.repo.append_event(started_event)
            yield started_event
            
            # 3. 使用 MCP 连接上下文管理器
            async with self._mcp_connection(task) as mcp_servers:
                # 4. 创建 Agent（带 MCP 服务）
                agent = self.adapter.create_agent(
                    name="ANIFORCE Assistant",
                    instructions=self._get_system_prompt(task.task_type),
                    mcp_servers=mcp_servers,
                )
                
                # 5. 创建或复用 Session
                if task.session_id:
                    session = self.adapter.create_session(task.session_id, self.session_db_path)
                    task_logger.info(f"[RUNTIME] Reusing session: {task.session_id}")
                else:
                    session_id = f"session_{uuid4().hex[:16]}"
                    session = self.adapter.create_session(session_id, self.session_db_path)
                    task.session_id = session_id
                    task_logger.info(f"[RUNTIME] Created new session: {session_id}")
                
                # 6. 执行 Agent
                task_logger.info(f"[RUNTIME] Executing Agent...")
                result = await self.adapter.run_streamed(
                    agent=agent,
                    input_text=user_input,
                    session=session,
                )
                
                # 7. 流式推送事件
                async for event in self.adapter.stream_events(result, task.task_id, start_sequence=sequence):
                    await self.repo.append_event(event)
                    yield event
                    sequence = event.sequence
                    
                    if event.event_type == EventType.TOOL_CALL_STARTED:
                        tool_name = event.payload.get("tool_name", "unknown")
                        task_logger.info(f"[RUNTIME] Event[{sequence}]: tool_call | tool={tool_name}")
            
            # 8. 更新状态为 completed
            await self.repo.update_status(task.task_id, AgentTaskStatus.COMPLETED)
            
            usage = self.adapter._extract_usage(result)
            
            # 9. 推送 runtime.completed 事件
            sequence += 1
            completed_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_COMPLETED,
                payload={"final_output": getattr(result, "final_output", None), "usage": usage},
                sequence=sequence,
            )
            await self.repo.append_event(completed_event)
            yield completed_event
            
            task_logger.info(f"[RUNTIME] Task completed successfully")
        
        except asyncio.CancelledError:
            task_logger.warning(f"[RUNTIME] Task cancelled by user")
            await self.repo.update_status(task.task_id, AgentTaskStatus.ABORTED)
            
            sequence += 1
            aborted_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_ABORTED,
                payload={"message": "Task cancelled by user"},
                sequence=sequence,
            )
            await self.repo.append_event(aborted_event)
            yield aborted_event
        
        except AppError as e:
            task_logger.error(f"[RUNTIME] AppError: {e.code.value} - {e.message}")
            await self.repo.update_task_error(task.task_id, e.to_dict())
            await self.repo.update_status(task.task_id, AgentTaskStatus.ERROR)
            
            sequence += 1
            error_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_ERROR,
                payload=e.to_dict(),
                sequence=sequence,
            )
            await self.repo.append_event(error_event)
            yield error_event
        
        except Exception as e:
            task_logger.exception(f"[RUNTIME] Unexpected error: {e}")
            
            error_dict = {
                "code": AgentErrorCode.UNKNOWN_ERROR.value,
                "message": "An unexpected error occurred",
                "internal_message": str(e),
                "category": ErrorCategory.RUNTIME_ERROR.value,
            }
            
            await self.repo.update_task_error(task.task_id, error_dict)
            await self.repo.update_status(task.task_id, AgentTaskStatus.ERROR)
            
            sequence += 1
            error_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_ERROR,
                payload={"code": AgentErrorCode.UNKNOWN_ERROR.value, "message": str(e)},
                sequence=sequence,
            )
            await self.repo.append_event(error_event)
            yield error_event
        
        finally:
            # 结束 Trace
            if trace_ctx:
                trace_ctx.__exit__(None, None, None)
    
    def _get_system_prompt(self, task_type: str) -> str:
        """根据任务类型返回 system prompt"""
        if task_type == "conversation":
            return "你是 ANIFORCE 的 AI 助手。"
        elif task_type == "campaign_planning":
            return "你是广告投放专家。"
        elif task_type == "asset_review":
            return "你是素材审核专家。"
        else:
            return "你是 ANIFORCE 的 AI 助手。"
