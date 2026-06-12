from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AgentHealthResponse(BaseModel):
    status: str = "ok"
    provider: str
    model: str
    streaming: bool = True


class AgentChatSessionCreateRequest(BaseModel):
    title: str | None = None


class AgentChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class AgentUsage(BaseModel):
    input: int = 0
    output: int = 0
    totalTokens: int = 0


class AgentChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    provider: str | None = None
    model: str | None = None
    usage: AgentUsage | None = None


class AgentChatSessionDetailResponse(BaseModel):
    session: AgentChatSessionResponse
    messages: list[AgentChatMessage]


class AgentChatStreamRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
