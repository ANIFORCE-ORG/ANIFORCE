"""
Agent API schemas (Request/Response)

遵循 Block 0 规范：
- Request 不包含 user_id（从 JWT 获取）
- Response 包含完整信息
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from ..agent_platform.models import AgentTaskStatus


# ============ Request Schemas ============

class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    task_type: str = Field(..., description="任务类型：conversation / campaign_planning / asset_review")
    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    input: Optional[dict] = Field(None, description="任务输入")
    session_id: Optional[str] = Field(None, description="OpenAI SDK Session ID（续接对话时传入）")


class ListTasksRequest(BaseModel):
    """查询任务列表请求"""
    limit: int = Field(20, ge=1, le=100, description="每页数量")
    offset: int = Field(0, ge=0, description="偏移量")
    task_type: Optional[str] = Field(None, description="过滤任务类型")
    status: Optional[AgentTaskStatus] = Field(None, description="过滤任务状态")


# ============ Response Schemas ============

class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    user_id: str
    task_type: str
    status: AgentTaskStatus
    session_id: Optional[str]
    title: str
    input: Optional[dict]
    result: Optional[dict]
    error: Optional[dict]
    rating: Optional[int]
    rating_comment: Optional[str]
    public_share_token: Optional[str]
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse]
    total: int
    limit: int
    offset: int


class EventResponse(BaseModel):
    """事件响应"""
    event_id: str
    task_id: str
    event_type: str
    payload: dict
    sequence: int
    created_at: datetime


class EventListResponse(BaseModel):
    """事件列表响应"""
    events: List[EventResponse]
    task_id: str
    total: int


# ============ 兼容层 Schemas（当前前端 API）============

class AgentChatSessionCreateRequest(BaseModel):
    """创建对话请求（兼容当前前端）"""
    title: Optional[str] = Field(None, description="对话标题")


class AgentChatSessionResponse(BaseModel):
    """对话响应（兼容当前前端）"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class AgentChatMessageResponse(BaseModel):
    """消息响应（兼容当前前端）"""
    id: str
    role: str  # user / assistant
    content: str
    created_at: datetime
    provider: Optional[str] = None
    model: Optional[str] = None


class AgentChatSessionDetailResponse(BaseModel):
    """对话详情响应（兼容当前前端）"""
    session: AgentChatSessionResponse
    messages: List[AgentChatMessageResponse]
