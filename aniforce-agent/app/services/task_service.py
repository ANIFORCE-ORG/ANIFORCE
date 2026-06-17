"""
Task Service - 任务业务逻辑层

核心职责：
- 创建和管理 Agent 任务
- 调用 AgentRuntime 执行任务
- 记录事件流到数据库
- 处理任务取消和错误
"""

import uuid
import asyncio
from typing import Optional, AsyncGenerator
import logging

from app.models.task import AgentTask, TaskStatus
from app.models.event import AgentEvent
from app.repositories.task_repo import TaskRepository
from app.repositories.event_repo import EventRepository
from app.agent.runtime import AgentRuntime

logger = logging.getLogger(__name__)


class TaskService:
    """任务服务"""

    def __init__(
        self,
        task_repo: TaskRepository,
        event_repo: EventRepository,
        agent_runtime: AgentRuntime,
    ):
        self.task_repo = task_repo
        self.event_repo = event_repo
        self.agent_runtime = agent_runtime

    async def create_task(
        self,
        *,
        user_id: str,
        task_type: str,
        title: str,
        input_data: Optional[dict] = None,
        session_id: Optional[str] = None,
    ) -> AgentTask:
        """
        创建任务

        Args:
            user_id: 用户 ID
            task_type: 任务类型
            title: 任务标题
            input_data: 输入数据
            session_id: 会话 ID（可选）

        Returns:
            创建的任务
        """
        task = AgentTask(
            task_id=f"task_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            title=title,
            input_data=input_data,
            session_id=session_id,
        )

        await self.task_repo.create(task)
        logger.info(f"Task created: {task.task_id}, user={user_id}, type={task_type}")

        return task

    async def run_task(
        self,
        *,
        task_id: str,
        user_id: str,
        prompt: str,
        session_id: str,  # 必须提供 session_id（ClaudeSDKClient 架构）
        model: Optional[str] = None,
        max_turns: int = 20,
        allowed_tools: Optional[list[str]] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        运行任务（流式返回事件）

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            prompt: 用户输入
            session_id: 会话 ID（必须，用于 ClaudeSDKClient 实例管理）
            model: Claude 模型
            max_turns: 最大轮数

        Yields:
            事件字典
        """
        # 注意：不在生成器内访问 self.task_repo/self.event_repo
        # 因为数据库连接可能已关闭（FastAPI 依赖注入问题）

        # 事件序号
        sequence = 0

        try:
            # 执行 Agent（通过 ClaudeSDKClient）
            async for message in self.agent_runtime.query(
                session_id=session_id,
                user_id=user_id,
                task_id=task_id,
                prompt=prompt,
                model=model,
                max_turns=max_turns,
                allowed_tools=allowed_tools,
            ):
                # 直接流式返回 SDK 消息（不转换为事件）
                yield message

                sequence += 1

            logger.info(f"Task completed: {task_id}, total_messages={sequence}")

        except asyncio.CancelledError:
            logger.warning(f"Task cancelled: {task_id}")
            raise
        except Exception as e:
            logger.error(f"Task error: {task_id}, error={e}", exc_info=True)
            raise

    async def cancel_task(self, task_id: str, user_id: str):
        """
        取消任务

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
        """
        # 检查权限
        task = await self.task_repo.get_by_id(task_id, user_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # 使用 ClaudeSDKClient 的 interrupt 能力
        if task.session_id:
            client = self.agent_runtime._clients.get(task.session_id)
            if client:
                try:
                    await client.interrupt()
                    logger.info(f"Task interrupted: {task_id}")
                except Exception as e:
                    logger.error(f"Error interrupting task: {e}", exc_info=True)
            else:
                logger.warning(f"No active client for session: {task.session_id}")
        else:
            logger.warning(f"Task has no session_id: {task_id}")

        # 更新状态
        await self.task_repo.update_status(task_id, user_id, TaskStatus.ABORTED)

    async def get_task(self, task_id: str, user_id: str) -> Optional[AgentTask]:
        """
        获取任务详情

        Args:
            task_id: 任务 ID
            user_id: 用户 ID

        Returns:
            任务对象
        """
        return await self.task_repo.get_by_id(task_id, user_id)

    async def list_tasks(
        self, user_id: str, task_type: Optional[str] = None, limit: int = 50
    ) -> list[AgentTask]:
        """
        列出用户任务

        Args:
            user_id: 用户 ID
            task_type: 任务类型过滤
            limit: 最多返回数量

        Returns:
            任务列表
        """
        return await self.task_repo.list_by_user(user_id, task_type, limit)

    async def get_task_events(
        self, task_id: str, user_id: str, after_sequence: Optional[int] = None
    ) -> list[AgentEvent]:
        """
        获取任务事件流

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            after_sequence: 起始序号（断点续传）

        Returns:
            事件列表
        """
        # 检查权限
        task = await self.task_repo.get_by_id(task_id, user_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        return await self.event_repo.list_by_task(task_id, after_sequence)

