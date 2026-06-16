"""Task 数据模型"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    ABORTED = "aborted"


@dataclass
class AgentTask:
    """Agent 任务模型"""
    task_id: str
    user_id: str
    task_type: str
    status: TaskStatus
    title: str
    session_id: Optional[str] = None
    input_data: Optional[dict] = None
    result: Optional[dict] = None
    error: Optional[dict] = None
    context: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "task_type": self.task_type,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "title": self.title,
            "session_id": self.session_id,
            "input_data": self.input_data,
            "result": self.result,
            "error": self.error,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
