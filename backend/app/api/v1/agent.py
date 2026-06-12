from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.runtime import agent_runtime
from app.schemas.agent import (
    AgentChatSessionCreateRequest,
    AgentChatSessionDetailResponse,
    AgentChatSessionResponse,
    AgentChatStreamRequest,
    AgentHealthResponse,
)

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.get("/health", response_model=AgentHealthResponse)
async def health() -> dict:
    return agent_runtime.health()


@router.post("/chat/sessions", response_model=AgentChatSessionResponse)
async def create_chat_session(req: AgentChatSessionCreateRequest) -> AgentChatSessionResponse:
    return agent_runtime.create_session(req.title)


@router.get("/chat/sessions", response_model=list[AgentChatSessionResponse])
async def list_chat_sessions() -> list[AgentChatSessionResponse]:
    return agent_runtime.list_sessions()


@router.get("/chat/sessions/{session_id}", response_model=AgentChatSessionDetailResponse)
async def get_chat_session(session_id: str) -> AgentChatSessionDetailResponse:
    session = agent_runtime.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return AgentChatSessionDetailResponse(
        session=session,
        messages=agent_runtime.get_messages(session_id),
    )


@router.post("/chat/sessions/{session_id}/stream")
async def stream_chat(session_id: str, req: AgentChatStreamRequest) -> StreamingResponse:
    return StreamingResponse(
        agent_runtime.stream_chat(session_id, req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
