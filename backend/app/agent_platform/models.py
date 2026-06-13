"""
Agent Platform 核心模型定义

遵循 Block 0 规范：
- Task 是唯一模型
- 事件驱动架构
- 状态机清晰
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class AgentTaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"           # 已创建，等待执行
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 成功完成
    ERROR = "error"               # 失败
    ABORTED = "aborted"           # 用户取消
    REQUIRES_ACTION = "requires_action"  # 等待用户动作


class AgentTaskEvent(BaseModel):
    """任务事件"""
    event_id: str = Field(..., description="事件 ID")
    task_id: str = Field(..., description="归属任务 ID")
    event_type: str = Field(..., description="事件类型")
    payload: dict = Field(default_factory=dict, description="事件载荷")
    sequence: int = Field(..., description="序号（从 0 开始）")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentTask(BaseModel):
    """Agent 任务"""
    task_id: str = Field(..., description="任务 ID")
    user_id: str = Field(..., description="用户 ID")
    task_type: str = Field(..., description="任务类型：conversation / campaign_planning / asset_review")
    status: AgentTaskStatus = Field(default=AgentTaskStatus.PENDING, description="任务状态")
    session_id: Optional[str] = Field(None, description="OpenAI SDK Session ID")
    title: str = Field(..., description="任务标题")
    input: Optional[dict] = Field(None, description="任务输入")
    result: Optional[dict] = Field(None, description="结构化结果")
    error: Optional[dict] = Field(None, description="错误详情")
    context: Optional[dict] = Field(default_factory=dict, description="任务上下文（如 auth_token）")  # ⭐ 新增
    rating: Optional[int] = Field(None, ge=1, le=5, description="用户评分")
    rating_comment: Optional[str] = Field(None, description="评分评论")
    public_share_token: Optional[str] = Field(None, description="公开分享 token")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# 核心事件类型常量
class EventType:
    """事件类型定义"""
    # Runtime 事件
    RUNTIME_STARTED = "runtime.started"
    RUNTIME_COMPLETED = "runtime.completed"
    RUNTIME_ERROR = "runtime.error"
    RUNTIME_ABORTED = "runtime.aborted"
    
    # 消息事件
    MESSAGE_STARTED = "message.started"
    MESSAGE_UPDATED = "message.updated"
    MESSAGE_COMPLETED = "message.completed"
    
    # 工具调用事件
    TOOL_CALL_STARTED = "tool_call.started"
    TOOL_CALL_COMPLETED = "tool_call.completed"
    TOOL_CALL_ERROR = "tool_call.error"
    
    # 其他事件
    HANDOFF = "handoff"
    GUARDRAIL_TRIGGERED = "guardrail.triggered"
