"""
Agent Task Repository 抽象接口

遵循 Block 0 规范：
- Repository 显式接收 user_id
- 查询时过滤 user_id
- 不允许无用户过滤的查询
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from ..models import AgentTask, AgentTaskEvent, AgentTaskStatus


class AgentTaskRepository(ABC):
    """Agent Task Repository 抽象接口"""
    
    @abstractmethod
    async def create(self, task: AgentTask) -> AgentTask:
        """创建任务（task 已包含 user_id）"""
        pass
    
    @abstractmethod
    async def get_user_task(self, user_id: str, task_id: str) -> Optional[AgentTask]:
        """
        查询用户任务（必须同时匹配 user_id 和 task_id）
        
        如果 task 不存在或不属于该用户，返回 None
        """
        pass
    
    @abstractmethod
    async def list_user_tasks(
        self, 
        user_id: str, 
        limit: int = 20,
        offset: int = 0,
        task_type: Optional[str] = None,
        status: Optional[AgentTaskStatus] = None,
    ) -> List[AgentTask]:
        """查询用户任务列表"""
        pass
    
    @abstractmethod
    async def update_status(
        self, 
        task_id: str, 
        status: AgentTaskStatus,
        updated_at: Optional[datetime] = None,
    ) -> None:
        """更新任务状态"""
        pass
    
    @abstractmethod
    async def update_task_error(
        self, 
        task_id: str, 
        error: dict,
    ) -> None:
        """更新任务错误信息"""
        pass
    
    @abstractmethod
    async def update_task_result(
        self, 
        task_id: str, 
        result: dict,
    ) -> None:
        """更新任务结果"""
        pass
    
    @abstractmethod
    async def append_event(self, event: AgentTaskEvent) -> None:
        """
        追加事件
        
        注意：调用方应先校验 task 归属
        """
        pass
    
    @abstractmethod
    async def list_user_task_events(
        self, 
        user_id: str,
        task_id: str,
        after_sequence: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[AgentTaskEvent]:
        """
        查询用户任务事件（含权限校验）
        
        Args:
            user_id: 用户 ID
            task_id: 任务 ID
            after_sequence: 只返回序号大于此值的事件（用于增量查询）
            limit: 最大返回数量
        """
        pass
    
    @abstractmethod
    async def count_user_tasks(
        self, 
        user_id: str,
        task_type: Optional[str] = None,
        status: Optional[AgentTaskStatus] = None,
    ) -> int:
        """统计用户任务数量"""
        pass
    
    @abstractmethod
    async def list_timeout_tasks(
        self,
        timeout_ms: int,
        status: AgentTaskStatus = AgentTaskStatus.RUNNING,
    ) -> List[AgentTask]:
        """
        查询超时任务（用于定时任务恢复）
        
        Args:
            timeout_ms: 超时毫秒数
            status: 要查询的状态
            
        Returns:
            超时任务列表（updated_at < now - timeout_ms）
        """
        pass
