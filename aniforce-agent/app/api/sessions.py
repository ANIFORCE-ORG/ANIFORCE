"""Session 管理 API"""

from fastapi import APIRouter, Depends, Request

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
    request: Request,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """创建新 session"""
    body = await request.json() if request.headers.get("content-length") else {}
    title = str(body.get("title") or "新对话")
    session = await service.create_session(user_id=user["id"], title=title)
    return {
        "session_id": session.session_id,
        "title": session.title,
        "status": session.status,
        "created_at": session.created_at,
    }


@router.get("/{session_id}")
async def get_session_detail(
    session_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """获取 session 详情和消息历史"""
    sessions = await service.list_sessions(user_id=user["id"])
    session = next((s for s in sessions if s.session_id == session_id), None)
    if not session:
        return {
            "session_id": session_id,
            "title": session_id,
            "messages": [],
        }
    messages = await service.get_session_history(user_id=user["id"], session_id=session_id)
    return {
        "session_id": session.session_id,
        "title": session.title,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "archived_at": session.archived_at,
        "messages": messages,
    }


@router.patch("/{session_id}")
async def rename_session(
    session_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """重命名 session"""
    body = await request.json()
    session = await service.rename_session(user_id=user["id"], session_id=session_id, title=str(body.get("title") or ""))
    return {
        "session_id": session.session_id,
        "title": session.title,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "archived_at": session.archived_at,
    }


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """删除/归档 session"""
    await service.archive_session(user_id=user["id"], session_id=session_id)
    return {"status": "archived", "session_id": session_id}


@router.post("/{session_id}/archive")
async def archive_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """归档 session"""
    await service.archive_session(user_id=user["id"], session_id=session_id)
    return {"status": "archived", "session_id": session_id}

