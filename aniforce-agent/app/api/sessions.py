"""Session 管理 API"""

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.services.agent_task_service import AgentTaskService

router = APIRouter(prefix="/sessions", tags=["sessions"])


def get_service() -> AgentTaskService:
    from app.main import _service
    return _service


@router.get("")
async def list_sessions(
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """列出用户的对话 session"""
    sessions = await service.list_sessions(user_id=user["id"])
    return [
        {
            "session_id": s.session_id,
            "title": s.title,
            "status": s.status,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "archived_at": s.archived_at,
        }
        for s in sessions
    ]


@router.post("")
async def create_session(
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """创建新 session"""
    session = await service.create_session(user_id=user["id"], title="新对话")
    return {
        "session_id": session.session_id,
        "title": session.title,
        "status": session.status,
        "created_at": session.created_at,
    }


@router.post("/{session_id}/archive")
async def archive_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """归档 session"""
    await service.archive_session(user_id=user["id"], session_id=session_id)
    return {"status": "archived", "session_id": session_id}
