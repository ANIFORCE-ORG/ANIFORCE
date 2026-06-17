"""Task Output 数据模型"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class OutputType(str, Enum):
    """任务产物类型"""

    INSIGHT = "insight"
    RECOMMENDATION = "recommendation"
    ALERT = "alert"
    REPORT = "report"
    ARTIFACT = "artifact"
    TEXT = "text"
    HITL_REQUEST = "hitl_request"


class OutputStatus(str, Enum):
    """任务产物状态"""

    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    OUTDATED = "outdated"
    CONFLICTED = "conflicted"


@dataclass
class TaskOutput:
    """Agent 任务结构化产物"""

    output_id: str
    task_id: str
    output_type: OutputType
    category: Optional[str]
    content: dict
    confidence: Optional[float] = None
    importance: Optional[str] = None
    actionable: bool = False
    requires_review: bool = False
    status: OutputStatus = OutputStatus.PENDING_REVIEW
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "output_id": self.output_id,
            "task_id": self.task_id,
            "type": self.output_type.value if isinstance(self.output_type, OutputType) else self.output_type,
            "category": self.category,
            "content": self.content,
            "confidence": self.confidence,
            "importance": self.importance,
            "actionable": self.actionable,
            "requires_review": self.requires_review,
            "status": self.status.value if isinstance(self.status, OutputStatus) else self.status,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
