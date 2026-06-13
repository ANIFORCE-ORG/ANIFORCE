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
    """
    事件类型定义（兼容 OpenAI SDK 和 AG-UI 协议）
    
    内部事件（OpenAI SDK）：runtime.*, message.*, tool_call.*
    AG-UI 事件：TEXT_MESSAGE_*, TOOL_CALL_*, STATE_SNAPSHOT, CUSTOM
    """
    # ==================== 内部 Runtime 事件 ====================
    RUNTIME_STARTED = "runtime.started"
    RUNTIME_COMPLETED = "runtime.completed"
    RUNTIME_ERROR = "runtime.error"
    RUNTIME_ABORTED = "runtime.aborted"
    
    # ==================== 内部消息事件 ====================
    MESSAGE_STARTED = "message.started"
    MESSAGE_UPDATED = "message.updated"
    MESSAGE_COMPLETED = "message.completed"
    
    # ==================== 内部工具调用事件 ====================
    TOOL_CALL_STARTED = "tool_call.started"
    TOOL_CALL_COMPLETED = "tool_call.completed"
    TOOL_CALL_ERROR = "tool_call.error"
    
    # ==================== AG-UI 协议事件 ====================
    # Text Message Events
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"
    
    # Tool Call Events
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"
    
    # State & Control Events
    STATE_SNAPSHOT = "STATE_SNAPSHOT"  # Shared State 同步
    CUSTOM = "CUSTOM"  # 自定义事件（HITL、Plan、Todo 等）
    
    # ==================== Plan-Execute 事件（通过 CUSTOM 传递）====================
    # 这些是 CUSTOM 事件的 subtype
    PLAN_CREATED = "plan.created"
    PLAN_UPDATED = "plan.updated"
    TODO_STARTED = "todo.started"
    TODO_COMPLETED = "todo.completed"
    TODO_FAILED = "todo.failed"
    TODO_SKIPPED = "todo.skipped"
    
    # ==================== HITL 事件（通过 CUSTOM 传递）====================
    HITL_CONFIRMATION_REQUEST = "hitl.confirmation_request"
    HITL_CONFIRMATION_RESPONSE = "hitl.confirmation_response"
    
    # ==================== 其他内部事件 ====================
    HANDOFF = "handoff"
    GUARDRAIL_TRIGGERED = "guardrail.triggered"


# ==================== Plan-Execute 数据模型 ====================

class TodoStatus(str, Enum):
    """Todo 状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    SKIPPED = "skipped"      # 跳过


class TodoItem(BaseModel):
    """Todo 项"""
    id: str = Field(..., description="Todo ID")
    title: str = Field(..., description="Todo 标题")
    description: Optional[str] = Field(None, description="详细描述")
    status: TodoStatus = Field(default=TodoStatus.PENDING, description="状态")
    result: Optional[dict] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    dependencies: List[str] = Field(default_factory=list, description="依赖的 Todo ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExecutionPlan(BaseModel):
    """执行计划"""
    plan_id: str = Field(..., description="计划 ID")
    task_id: str = Field(..., description="归属任务 ID")
    todos: List[TodoItem] = Field(default_factory=list, description="Todo 列表")
    current_todo_index: int = Field(default=0, description="当前执行的 Todo 索引")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ==================== AG-UI 协议数据模型 ====================

class AGUISharedState(BaseModel):
    """
    AG-UI Shared State（前后端共享状态）
    
    用于：
    - Agent 知道用户当前在哪个页面/上下文
    - 前端展示 Agent 操作的目标对象
    """
    current_project_id: Optional[str] = Field(None, description="当前项目 ID")
    current_campaign_id: Optional[str] = Field(None, description="当前广告计划 ID")
    user_preferences: dict = Field(default_factory=dict, description="用户偏好设置")
    pending_confirmations: List[str] = Field(default_factory=list, description="待确认的操作 ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if isinstance(v, datetime) else v
        }


class HITLConfirmationRequest(BaseModel):
    """
    Human-in-the-Loop 确认请求
    
    用于：
    - 高风险操作确认（删除、批量修改）
    - 需要用户决策的场景
    """
    operation_id: str = Field(..., description="操作 ID")
    operation_type: str = Field(..., description="操作类型：delete / batch_update / etc")
    title: str = Field(..., description="确认标题")
    description: str = Field(..., description="详细说明")
    details: dict = Field(default_factory=dict, description="操作详情")
    risk_level: str = Field(..., description="风险等级：low / medium / high")
    require_explicit_confirm: bool = Field(default=True, description="是否需要显式确认")
    timeout_seconds: int = Field(default=300, description="超时时间（秒）")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HITLConfirmationResponse(BaseModel):
    """HITL 确认响应"""
    operation_id: str = Field(..., description="操作 ID")
    confirmed: bool = Field(..., description="是否确认")
    user_comment: Optional[str] = Field(None, description="用户备注")
    responded_at: datetime = Field(default_factory=datetime.utcnow, description="响应时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
