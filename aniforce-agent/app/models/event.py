"""Event 数据模型"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AgentEvent:
    """Agent 事件模型"""
    event_id: str
    task_id: str
    event_type: str
    payload: dict
    sequence: int
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "sequence": self.sequence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
