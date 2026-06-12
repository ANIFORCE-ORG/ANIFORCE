"""
Agent Runtime

职责：
- 管理 Agent 执行生命周期
- 集成 SDK Adapter
- 管理 Session
- 处理异常和超时

遵循 Block 0 规范：
- 捕获 SDK 异常并转换
- 写入事件到 Repository
- 更新 Task 状态
"""

import asyncio
from typing import AsyncIterator, Optional
from pathlib import Path
from uuid import uuid4
from loguru import logger

from .adapters.openai_adapter import OpenAISDKAdapter
from .models import AgentTask, AgentTaskEvent, AgentTaskStatus, EventType
from .errors import AppError, AgentErrorCode, ErrorCategory
from .repositories.base import AgentTaskRepository
from .tracing import get_tracer


class AgentRuntime:
    """Agent Runtime"""
    
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
        
        # 确保目录存在
        Path(session_db_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"AgentRuntime initialized | tracing={enable_tracing}")
    
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
            task_logger.debug(f"[RUNTIME] Status updated: RUNNING")
            
            # 2. 推送 runtime.started 事件
            sequence = 0
            started_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_STARTED,
                payload={
                    "task_type": task.task_type,
                    "user_input": user_input,
                },
                sequence=sequence,
            )
            await self.repo.append_event(started_event)
            yield started_event
            
            task_logger.info(f"[RUNTIME] Event[{sequence}]: {EventType.RUNTIME_STARTED}")
            
            # 3. 创建 Agent
            agent = self.adapter.create_agent(
                name="ANIFORCE Assistant",
                instructions=self._get_system_prompt(task.task_type),
            )
            task_logger.debug(f"[RUNTIME] Agent created: {agent.name}")
            
            # 4. 创建或复用 Session
            session = None
            if task.session_id:
                session = self.adapter.create_session(task.session_id, self.session_db_path)
                task_logger.info(f"[RUNTIME] Reusing session: {task.session_id}")
            else:
                # 创建新 session
                session_id = f"session_{uuid4().hex[:16]}"
                session = self.adapter.create_session(session_id, self.session_db_path)
                task.session_id = session_id
                task_logger.info(f"[RUNTIME] Created new session: {session_id}")
            
            # 5. 执行 Agent
            task_logger.info(f"[RUNTIME] Executing Agent...")
            result = await self.adapter.run_streamed(
                agent=agent,
                input_text=user_input,
                session=session,
            )
            
            # 6. 流式推送事件
            task_logger.debug(f"[RUNTIME] Streaming events...")
            async for event in self.adapter.stream_events(result, task.task_id):
                await self.repo.append_event(event)
                yield event
                sequence = event.sequence
                
                # 详细日志
                if event.event_type == EventType.MESSAGE_UPDATED:
                    delta = event.payload.get("delta", "")
                    task_logger.debug(f"[RUNTIME] Event[{sequence}]: {event.event_type} | delta_len={len(delta)}")
                elif event.event_type == EventType.TOOL_CALL_STARTED:
                    tool_name = event.payload.get("tool_name", "unknown")
                    task_logger.info(f"[RUNTIME] Event[{sequence}]: {event.event_type} | tool={tool_name}")
                else:
                    task_logger.debug(f"[RUNTIME] Event[{sequence}]: {event.event_type}")
            
            # 7. 更新状态为 completed
            await self.repo.update_status(task.task_id, AgentTaskStatus.COMPLETED)
            task_logger.info(f"[RUNTIME] Status updated: COMPLETED")
            
            usage = self.adapter._extract_usage(result)

            # 8. 推送 runtime.completed 事件
            sequence += 1
            completed_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_COMPLETED,
                payload={
                    "final_output": getattr(result, "final_output", None),
                    "usage": usage,
                },
                sequence=sequence,
            )
            await self.repo.append_event(completed_event)
            yield completed_event
            
            task_logger.info(f"[RUNTIME] Event[{sequence}]: {EventType.RUNTIME_COMPLETED}")
            task_logger.info(f"[RUNTIME] Task completed successfully")
        
        except asyncio.CancelledError:
            # 用户取消
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
            # 业务异常
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
            # 未知异常
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
                payload={
                    "code": AgentErrorCode.UNKNOWN_ERROR.value,
                    "message": "An unexpected error occurred",
                },
                sequence=sequence,
            )
            await self.repo.append_event(error_event)
            yield error_event
        
        finally:
            # 结束 Trace
            if trace_ctx:
                trace_ctx.__exit__(None, None, None)
    
    def _get_system_prompt(self, task_type: str) -> str:
        """
        获取 System Prompt
        
        根据 task_type 返回不同的 instructions
        """
        if task_type == "conversation":
            return """
你是 ANIFORCE 的 AI 助手，帮助用户完成游戏广告投放相关工作。

当前阶段你只有普通对话能力，没有工具可用。

回答要清晰、简洁、专业。
"""
        
        elif task_type == "campaign_planning":
            return """
你是 ANIFORCE 的广告投放规划专家。

你的任务是帮助用户制定广告投放计划，包括：
- 目标市场分析
- 平台选择
- 预算分配
- 创意需求

请提出关键问题，收集足够信息后给出专业建议。
"""
        
        else:
            return """
你是 ANIFORCE 的 AI 助手，帮助用户完成工作。

回答要清晰、简洁、专业。
"""
