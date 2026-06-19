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
        if include_archived:
            return sessions
        return [s for s in sessions if s.status == AgentSessionStatus.ACTIVE]

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
