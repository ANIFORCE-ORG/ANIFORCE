"""Session API 端点 — 会话 CRUD"""

import logging
from typing import Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user_id
from app.config.database import get_task_db
from app.repositories.session_repo import SessionRepository
from app.repositories.task_repo import TaskRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["agent-sessions"])


class RenameRequest(BaseModel):
    title: str


class ArchiveRequest(BaseModel):
    status: str = "archived"


# ---- 依赖注入 ----

async def get_session_repo(db=Depends(get_task_db)) -> SessionRepository:
    return SessionRepository(db)


async def get_task_repo(db=Depends(get_task_db)) -> TaskRepository:
    return TaskRepository(db)


# ---- 列表 ----

@router.get("")
async def list_sessions(
    status: str = "active",
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
    session_repo: SessionRepository = Depends(get_session_repo),
):
    """列出用户会话"""
    sessions = await session_repo.list_by_user(user_id, status=status, limit=limit)
    return {"sessions": [s.to_dict() for s in sessions]}


# ---- 创建（前端新建空会话，返回 session_id） ----

@router.post("")
async def create_session(
    user_id: str = Depends(get_current_user_id),
    session_repo: SessionRepository = Depends(get_session_repo),
):
    """创建新会话，返回 session_id"""
    import uuid
    from app.models import Session
    from datetime import datetime

    session = Session(
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        title="新会话",
        status="active",
        last_active_at=datetime.utcnow(),
    )
    session = await session_repo.create(session)
    logger.info("Session created: %s, user=%s", session.session_id, user_id)
    return session.to_dict()


# ---- 单个会话详情 ----

@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    session_repo: SessionRepository = Depends(get_session_repo),
):
    """获取会话详情"""
    session = await session_repo.get_by_id(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


# ---- 该会话下的 task 列表 ----

@router.get("/{session_id}/tasks")
async def get_session_tasks(
    session_id: str,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
    session_repo: SessionRepository = Depends(get_session_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
):
    """获取会话下的所有 task"""
    session = await session_repo.get_by_id(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # task_repo 当前只支持 list_by_user(user_id, task_type, limit)
    # 需要加 session_id 过滤。先用全量拉 + 前端过滤的临时方案，
    # 后续优化 task_repo.list_by_session。
    all_tasks = await task_repo.list_by_user(user_id, limit=limit * 5)
    session_tasks = [t for t in all_tasks if t.session_id == session_id]
    # 按时间倒序
    session_tasks.sort(key=lambda t: t.created_at or "", reverse=True)
    return {"tasks": [t.to_dict() for t in session_tasks[:limit]]}


# ---- 改名 ----

@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    request: RenameRequest,
    user_id: str = Depends(get_current_user_id),
    session_repo: SessionRepository = Depends(get_session_repo),
):
    """更新会话标题"""
    updated = await session_repo.update_title(session_id, user_id, request.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    session = await session_repo.get_by_id(session_id, user_id)
    return session.to_dict()


# ---- 归档 ----

@router.delete("/{session_id}")
async def archive_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    session_repo: SessionRepository = Depends(get_session_repo),
):
    """归档会话（status=archived，不真删）"""
    archived = await session_repo.archive(session_id, user_id)
    if not archived:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "status": "archived"}
