"""Session 数据模型"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Session:
    """Agent 会话模型

    一个会话对应一段连续对话，包含 N 个 task。
    session_id 同时是 Claude SDK 的 session_id（resume 用）。
    """
    session_id: str
    user_id: str
    title: str
    status: str = "active"           # active / archived
    last_task_id: Optional[str] = None
    last_active_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "status": self.status,
            "last_task_id": self.last_task_id,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
