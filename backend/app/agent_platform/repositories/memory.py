"""
Agent Task Repository 内存实现

仅用于开发和测试，生产环境应使用 PostgreSQL 实现。

遵循 Block 0 规范：
- 显式接收 user_id
- 查询时过滤 user_id
- 严格权限隔离
"""

from typing import Optional, List, Dict
from datetime import datetime, timedelta
from uuid import uuid4

from .base import AgentTaskRepository
from ..models import AgentTask, AgentTaskEvent, AgentTaskStatus


class MemoryAgentTaskRepository(AgentTaskRepository):
    """内存版 Repository（开发/测试用）"""
    
    def __init__(self):
        self._tasks: Dict[str, AgentTask] = {}
        self._events: Dict[str, List[AgentTaskEvent]] = {}  # task_id -> events
    
    async def create(self, task: AgentTask) -> AgentTask:
        """创建任务"""
        self._tasks[task.task_id] = task
        self._events[task.task_id] = []
        return task
    
    async def get_user_task(self, user_id: str, task_id: str) -> Optional[AgentTask]:
        """查询用户任务（含权限校验）"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        # 关键：校验归属
        if task.user_id != user_id:
            return None
        return task
    
    async def list_user_tasks(
        self, 
        user_id: str, 
        limit: int = 20,
        offset: int = 0,
        task_type: Optional[str] = None,
        status: Optional[AgentTaskStatus] = None,
    ) -> List[AgentTask]:
        """查询用户任务列表"""
        # 关键：只返回该用户的任务
        user_tasks = [
            task for task in self._tasks.values()
            if task.user_id == user_id
        ]
        
        # 过滤
        if task_type:
            user_tasks = [t for t in user_tasks if t.task_type == task_type]
        if status:
            user_tasks = [t for t in user_tasks if t.status == status]
        
        # 排序（最新在前）
        user_tasks = sorted(
            user_tasks, 
            key=lambda t: t.created_at, 
            reverse=True
        )
        
        # 分页
        return user_tasks[offset:offset + limit]
    
    async def update_status(
        self, 
        task_id: str, 
        status: AgentTaskStatus,
        updated_at: Optional[datetime] = None,
    ) -> None:
        """更新任务状态"""
        task = self._tasks.get(task_id)
        if not task:
            return
        task.status = status
        task.updated_at = updated_at or datetime.utcnow()
    
    async def update_task_error(
        self, 
        task_id: str, 
        error: dict,
    ) -> None:
        """更新任务错误信息"""
        task = self._tasks.get(task_id)
        if not task:
            return
        task.error = error
        task.updated_at = datetime.utcnow()
    
    async def update_task_result(
        self, 
        task_id: str, 
        result: dict,
    ) -> None:
        """更新任务结果"""
        task = self._tasks.get(task_id)
        if not task:
            return
        task.result = result
        task.updated_at = datetime.utcnow()
    
    async def append_event(self, event: AgentTaskEvent) -> None:
        """追加事件"""
        if event.task_id not in self._events:
            self._events[event.task_id] = []
        self._events[event.task_id].append(event)
        
        # 更新 task 的 updated_at
        task = self._tasks.get(event.task_id)
        if task:
            task.updated_at = datetime.utcnow()
    
    async def list_user_task_events(
        self, 
        user_id: str,
        task_id: str,
        after_sequence: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[AgentTaskEvent]:
        """查询用户任务事件（含权限校验）"""
        # 先校验 task 归属
        task = await self.get_user_task(user_id, task_id)
        if not task:
            return []
        
        events = self._events.get(task_id, [])
        
        # 过滤 sequence
        if after_sequence is not None:
            events = [e for e in events if e.sequence > after_sequence]
        
        # 限制数量
        if limit:
            events = events[:limit]
        
        return events
    
    async def count_user_tasks(
        self, 
        user_id: str,
        task_type: Optional[str] = None,
        status: Optional[AgentTaskStatus] = None,
    ) -> int:
        """统计用户任务数量"""
        user_tasks = [
            task for task in self._tasks.values()
            if task.user_id == user_id
        ]
        
        if task_type:
            user_tasks = [t for t in user_tasks if t.task_type == task_type]
        if status:
            user_tasks = [t for t in user_tasks if t.status == status]
        
        return len(user_tasks)
    
    async def list_timeout_tasks(
        self,
        timeout_ms: int,
        status: AgentTaskStatus = AgentTaskStatus.RUNNING,
    ) -> List[AgentTask]:
        """查询超时任务"""
        timeout_date = datetime.utcnow() - timedelta(milliseconds=timeout_ms)
        
        timeout_tasks = [
            task for task in self._tasks.values()
            if task.status == status and task.updated_at < timeout_date
        ]
        
        return timeout_tasks
