"""
Agent Task Service

业务编排层，负责：
- 任务创建和管理
- 权限校验
- 事件流订阅

遵循 Block 0 规范：
- 从 API 接收 user_id，传给 Repository
- 不从全局上下文获取 user_id
- 权限校验在 Repository 层完成
"""

import asyncio
from typing import Optional, List, AsyncIterator
from datetime import datetime
from uuid import uuid4
from loguru import logger

from app.models.agent_platform_models import AgentTask, AgentTaskEvent, AgentTaskStatus, EventType, AgentSession, AgentSessionStatus
from app.core.errors import AppError, AgentErrorCode, ErrorCategory
from app.repositories.base import AgentTaskRepository
from app.agent.runtime import AgentRuntime


class AgentTaskService:
    """Agent Task Service"""
    
    def __init__(self, repo: AgentTaskRepository, runtime: Optional[AgentRuntime] = None):
        self._repo = repo
        self._runtime = runtime
        self._session_locks: dict[str, asyncio.Lock] = {}

    @staticmethod
    def _is_default_session_title(title: str | None) -> bool:
        if not title:
            return True
        return (
            title == "新对话"
            or title.startswith("Agent Session ")
            or title.startswith("日常对话")
            or title.startswith("项目管理")
        )

    async def _display_session(self, user_id: str, session: AgentSession) -> AgentSession:
        if not self._is_default_session_title(session.title):
            return session
        first_title = await self._repo.get_first_session_task_title(user_id, session.session_id)
        if first_title:
            session.title = first_title[:50]
        return session
    
    async def create_session(
        self,
        user_id: str,
        title: str = "新对话",
    ) -> AgentSession:
        """创建用户会话元数据。"""
        session = AgentSession(
            session_id=f"session_{uuid4().hex[:16]}",
            user_id=user_id,
            title=title or "新对话",
            status=AgentSessionStatus.ACTIVE,
        )
        await self._repo.create_session(session)
        logger.bind(session_id=session.session_id, user_id=user_id).info("Session created")
        return session

    async def list_sessions(
        self,
        user_id: str,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentSession]:
        """列出用户会话。"""
        sessions = await self._repo.list_user_sessions(user_id, limit=limit, offset=offset)
        if not include_archived:
            sessions = [s for s in sessions if s.status == AgentSessionStatus.ACTIVE]
        return [await self._display_session(user_id, session) for session in sessions]

    async def get_active_session(self, user_id: str, session_id: str) -> AgentSession:
        """获取 active session，并校验归属。"""
        session = await self._repo.get_user_session(user_id, session_id)
        if not session or session.status != AgentSessionStatus.ACTIVE:
            raise AppError(
                code=AgentErrorCode.TASK_NOT_FOUND,
                message="Session not found or access denied",
                category=ErrorCategory.TASK_ERROR,
            )
        return session

    async def rename_session(self, user_id: str, session_id: str, title: str) -> AgentSession:
        """重命名用户会话。"""
        title = title.strip()[:80]
        if not title:
            raise AppError(
                code=AgentErrorCode.TASK_STATUS_INVALID,
                message="Session title cannot be empty",
                category=ErrorCategory.VALIDATION_ERROR,
            )
        await self.get_active_session(user_id, session_id)
        updated = await self._repo.update_user_session_title(user_id, session_id, title)
        if not updated:
            raise AppError(
                code=AgentErrorCode.TASK_NOT_FOUND,
                message="Session not found or access denied",
                category=ErrorCategory.TASK_ERROR,
            )
        session = await self.get_active_session(user_id, session_id)
        logger.bind(session_id=session_id, user_id=user_id).info("Session renamed")
        return session

    async def archive_session(self, user_id: str, session_id: str) -> None:
        """归档用户会话。"""
        await self.get_active_session(user_id, session_id)
        archived = await self._repo.archive_user_session(user_id, session_id)
        if not archived:
            raise AppError(
                code=AgentErrorCode.TASK_NOT_FOUND,
                message="Session not found or access denied",
                category=ErrorCategory.TASK_ERROR,
            )
        logger.bind(session_id=session_id, user_id=user_id).info("Session archived")

    async def create_task(
        self,
        user_id: str,
        task_type: str,
        title: str,
        input_data: Optional[dict] = None,
        session_id: Optional[str] = None,
    ) -> AgentTask:
        """
        创建任务
        
        Args:
            user_id: 用户 ID（从 JWT 获取）
            task_type: 任务类型
            title: 任务标题
            input_data: 任务输入
            session_id: OpenAI SDK Session ID（续接对话时传入）
        """
        task_id = f"task_{uuid4().hex[:16]}"
        
        task = AgentTask(
            task_id=task_id,
            user_id=user_id,
            task_type=task_type,
            title=title,
            input=input_data,
            session_id=session_id,
            status=AgentTaskStatus.PENDING,
        )
        
        await self._repo.create(task)
        
        logger.bind(task_id=task_id, user_id=user_id).info(
            f"Task created: {task_type}"
        )
        
        return task
    
    async def get_task(self, user_id: str, task_id: str) -> AgentTask:
        """
        获取任务详情（含权限校验）
        
        Args:
            user_id: 用户 ID（从 JWT 获取）
            task_id: 任务 ID
        """
        task = await self._repo.get_user_task(user_id, task_id)
        if not task:
            raise AppError(
                code=AgentErrorCode.TASK_NOT_FOUND,
                message="Task not found or access denied",
                category=ErrorCategory.TASK_ERROR,
            )
        return task
    
    async def list_tasks(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        task_type: Optional[str] = None,
        status: Optional[AgentTaskStatus] = None,
    ) -> tuple[List[AgentTask], int]:
        """
        查询任务列表
        
        Returns:
            (tasks, total)
        """
        tasks = await self._repo.list_user_tasks(
            user_id=user_id,
            limit=limit,
            offset=offset,
            task_type=task_type,
            status=status,
        )
        total = await self._repo.count_user_tasks(
            user_id=user_id,
            task_type=task_type,
            status=status,
        )
        return tasks, total
    
    async def cancel_task(self, user_id: str, task_id: str) -> None:
        """
        取消任务
        
        Args:
            user_id: 用户 ID（从 JWT 获取）
            task_id: 任务 ID
        """
        # 先校验归属
        task = await self.get_task(user_id, task_id)
        
        # 校验状态
        if task.status not in [AgentTaskStatus.PENDING, AgentTaskStatus.RUNNING]:
            raise AppError(
                code=AgentErrorCode.TASK_STATUS_INVALID,
                message=f"Cannot cancel task in {task.status} status",
                category=ErrorCategory.TASK_ERROR,
            )
        
        # 更新状态
        await self._repo.update_status(task_id, AgentTaskStatus.ABORTED)
        
        # 写入事件
        event = AgentTaskEvent(
            event_id=f"event_{uuid4().hex[:16]}",
            task_id=task_id,
            event_type=EventType.RUNTIME_ABORTED,
            payload={"message": "Task cancelled by user"},
            sequence=await self._get_next_sequence(task_id),
        )
        await self._repo.append_event(event)
        
        logger.bind(task_id=task_id, user_id=user_id).info("Task cancelled")
    
    async def list_task_events(
        self,
        user_id: str,
        task_id: str,
        after_sequence: Optional[int] = None,
    ) -> List[AgentTaskEvent]:
        """
        查询任务事件（含权限校验）
        
        Args:
            user_id: 用户 ID（从 JWT 获取）
            task_id: 任务 ID
            after_sequence: 只返回序号大于此值的事件
        """
        return await self._repo.list_user_task_events(
            user_id=user_id,
            task_id=task_id,
            after_sequence=after_sequence,
        )
    
    async def get_session_history(
        self,
        user_id: str,
        session_id: str,
    ) -> List[dict]:
        """
        从 session 的事件流重建消息历史。

        重建规则：
        - 用户消息：每个 task 的 user_input（从 task 表取）
        - assistant 消息：累积 MESSAGE_UPDATED delta + THINKING_UPDATED delta + TOOL_CALL 事件
        - 按 task 创建时间排序
        """
        events = await self._repo.list_session_events(user_id, session_id)

        messages: List[dict] = []
        current_assistant: Optional[dict] = None
        # 跟踪当前 block 的开始时间（用于计算 thinking duration）
        current_block_start: Optional[str] = None
        current_block_type: Optional[str] = None

        def finalize_current_block():
            """当前 block 结束时，如果是 thinking，计算 duration"""
            nonlocal current_block_start, current_block_type
            if current_block_start and current_block_type == "thinking" and current_assistant:
                blocks = current_assistant.get("content", [])
                if blocks and isinstance(blocks[-1], dict) and blocks[-1].get("type") == "thinking":
                    # duration 由前端根据 timestamp 算，这里先存 start_ms
                    pass
            current_block_start = None
            current_block_type = None

        def ensure_assistant(created_at: str | None = None) -> dict:
            nonlocal current_assistant
            if not current_assistant:
                current_assistant = {
                    "role": "assistant",
                    "content": [],
                    "timestamp": created_at,
                    "provider": "openai-compatible",
                    "model": "deepseek/deepseek-v4-pro",
                }
            return current_assistant

        def append_delta_block(block_type: str, field: str, delta: str, created_at: str | None = None) -> None:
            nonlocal current_block_start, current_block_type
            assistant = ensure_assistant(created_at)
            blocks = assistant.setdefault("content", [])
            if blocks and isinstance(blocks[-1], dict) and blocks[-1].get("type") == block_type:
                blocks[-1][field] = str(blocks[-1].get(field, "")) + delta
            else:
                # 新 block 开始：先结算上一个 block
                finalize_current_block()
                new_block = {"type": block_type, field: delta}
                if block_type == "thinking" and created_at:
                    new_block["_start_at"] = created_at
                blocks.append(new_block)
                current_block_start = created_at
                current_block_type = block_type

        def flush_assistant():
            nonlocal current_assistant, current_block_start, current_block_type
            finalize_current_block()
            if current_assistant:
                # 计算 thinking block 的 duration（秒）
                content = current_assistant.get("content", [])
                for i, block in enumerate(content):
                    if isinstance(block, dict) and block.get("type") == "thinking" and block.get("_start_at"):
                        # duration = 下一个 block 的 timestamp - 本 block start
                        # 或 message timestamp - start
                        end_at = None
                        if i + 1 < len(content) and isinstance(content[i + 1], dict):
                            end_at = content[i + 1].get("_start_at") or current_assistant.get("timestamp")
                        else:
                            end_at = current_assistant.get("timestamp")
                        if end_at:
                            try:
                                from datetime import datetime
                                start_dt = datetime.fromisoformat(block["_start_at"].replace("Z", "+00:00"))
                                end_dt = datetime.fromisoformat(end_at.replace("Z", "+00:00"))
                                duration = int((end_dt - start_dt).total_seconds())
                                if duration > 0:
                                    block["duration"] = duration
                            except Exception:
                                pass
                        block.pop("_start_at", None)
                if content:
                    messages.append(current_assistant)
                current_assistant = None
                current_block_start = None
                current_block_type = None

        for event in events:
            et = event.event_type
            payload = event.payload or {}

            if et == EventType.RUNTIME_STARTED:
                # 新 task 开始：先 flush 上一个 assistant，再加用户消息
                flush_assistant()
                user_input = payload.get("user_input") or payload.get("prompt") or ""
                if user_input:
                    messages.append({
                        "role": "user",
                        "content": user_input,
                        "timestamp": event.created_at,
                    })
                current_assistant = {
                    "role": "assistant",
                    "content": [],
                    "timestamp": event.created_at,
                }

            elif et == EventType.MESSAGE_UPDATED:
                delta = payload.get("delta", "")
                if delta:
                    append_delta_block("text", "text", delta, event.created_at)

            elif et == EventType.THINKING_UPDATED:
                delta = payload.get("delta", "")
                if delta:
                    append_delta_block("thinking", "thinking", delta, event.created_at)

            elif et == EventType.MESSAGE_COMPLETED:
                assistant = ensure_assistant(event.created_at)
                usage = payload.get("usage")
                if usage:
                    assistant["usage"] = usage
                flush_assistant()

            elif et == EventType.TOOL_CALL_STARTED:
                assistant = ensure_assistant(event.created_at)
                assistant.setdefault("content", []).append({
                    "type": "toolCall",
                    "toolCallId": payload.get("tool_call_id"),
                    "toolName": payload.get("tool_name"),
                    "input": payload.get("arguments", {}),
                })

            elif et == EventType.TOOL_CALL_COMPLETED:
                if current_assistant:
                    tool_call_id = payload.get("tool_call_id")
                    for block in current_assistant.get("content", []):
                        if isinstance(block, dict) and block.get("type") == "toolCall" and block.get("toolCallId") == tool_call_id:
                            block["result"] = payload.get("result")
                            break

            elif et == EventType.RUNTIME_COMPLETED:
                flush_assistant()

        flush_assistant()
        # 规范化时间戳：后端用的是 utcnow().isoformat()（naive，无时区），
        # 前端 new Date() 会当本地时间解析导致时区错误。统一加 'Z' 后缀标记为 UTC。
        for msg in messages:
            ts = msg.get("timestamp")
            if isinstance(ts, str) and not ts.endswith("Z") and not ts.endswith("+00:00"):
                msg["timestamp"] = ts + "Z"
        return messages

    async def run_task(
        self,
        user_id: str,
        task_id: str,
        user_input: str,
        context: dict = None,  # ⭐ 新增
    ) -> AsyncIterator[AgentTaskEvent]:
        """
        运行任务（实时执行）
        
        Args:
            user_id: 用户 ID（从 JWT 获取）
            task_id: 任务 ID
            user_input: 用户输入
            context: 任务上下文（如 auth_token）
            
        Yields:
            AgentTaskEvent（实时事件流）
        """
        # 校验 task 归属
        task = await self.get_task(user_id, task_id)
        
        # 设置 context
        if context:
            task.context = context
        
        if not self._runtime:
            raise AppError(
                code=AgentErrorCode.SDK_ERROR,
                message="Runtime not initialized",
                category=ErrorCategory.RUNTIME_ERROR,
            )
        
        session_key = task.session_id or task.task_id
        lock = self._session_locks.setdefault(session_key, asyncio.Lock())

        async with lock:
            try:
                async for event in self._runtime.run_task(task, user_input):
                    yield event
            finally:
                if task.session_id:
                    await self._repo.touch_session(user_id, task.session_id)
    
    async def stream_task_events(
        self,
        user_id: str,
        task_id: str,
        after_sequence: Optional[int] = None,
    ) -> AsyncIterator[AgentTaskEvent]:
        """
        流式推送任务事件（SSE）
        
        用于断点续传：先推送历史事件，再推送实时事件（如果任务在运行中）
        
        Args:
            user_id: 用户 ID（从 JWT 获取）
            task_id: 任务 ID
            after_sequence: 从此序号之后开始推送
        """
        # 先校验 task 归属
        task = await self.get_task(user_id, task_id)
        
        # 1. 先推送历史事件
        history = await self.list_task_events(user_id, task_id, after_sequence)
        for event in history:
            yield event
        
        # 2. 如果任务未完成，推送实时事件
        # TODO: 需要实现 Runtime 的实时事件订阅机制
        # 目前只返回历史事件
    
    async def _get_next_sequence(self, task_id: str) -> int:
        """获取下一个事件序号"""
        return await self._repo.count_task_events(task_id)
