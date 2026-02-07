from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.repositories.factory import get_chat_repo
from app.repositories.protocols import ChatRepository
from app.services.chat_service import ChatService
from app.schemas.chat import AnalyzeRequest, MessageRequest
from app.schemas.base import ResponseBase

router = APIRouter(prefix="/chat", tags=["AI 对话"])


def _get_service(chat_repo: ChatRepository = Depends(get_chat_repo)) -> ChatService:
    return ChatService(chat_repo)


@router.post("/analyze", response_model=ResponseBase)
async def analyze_game(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user),
    service: ChatService = Depends(_get_service),
):
    """AI 分析游戏 — 返回市场热点和推荐方向"""
    result = await service.analyze_game(user["id"], request.game_description, request.game_type)
    return ResponseBase(data=result)


@router.post("/{session_id}/message", response_model=ResponseBase)
async def send_message(
    session_id: str,
    request: MessageRequest,
    user: dict = Depends(get_current_user),
    service: ChatService = Depends(_get_service),
):
    """发送消息"""
    result = await service.send_message(session_id, user["id"], request.content)
    return ResponseBase(data=result)


@router.get("/{session_id}/history", response_model=ResponseBase)
async def get_history(
    session_id: str,
    service: ChatService = Depends(_get_service),
):
    """获取对话历史"""
    result = await service.get_history(session_id)
    return ResponseBase(data=result)
