"""Agent Session HTTP transport routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.api.common import authorization, error_payload
from app.api.deps import get_current_user
from app.config.database import get_db
from app.repositories.impl.sqlite_agent_message_repo import SqliteAgentMessageRepository
from app.repositories.impl.sqlite_agent_session_repo import SqliteAgentSessionRepository
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository
from app.services.agent_gateway import AgentGatewayError, AgentGatewayService
from app.services.agent_session_service import AgentSessionError, AgentSessionService
from app.services.agent_snapshot_service import AgentSnapshotService

router = APIRouter()


def get_agent_gateway() -> AgentGatewayService:
    return AgentGatewayService()


def get_agent_session_service(
    session: AsyncSession = Depends(get_db),
    gateway: AgentGatewayService = Depends(get_agent_gateway),
) -> AgentSessionService:
    return AgentSessionService(
        session_repo=SqliteAgentSessionRepository(session),
        state_repo=SqliteSessionStateRepository(session),
        gateway=gateway,
        message_repo=SqliteAgentMessageRepository(session),
    )


@router.get("/health")
async def agent_health(gateway: AgentGatewayService = Depends(get_agent_gateway)):
    try:
        return await gateway.health()
    except AgentGatewayError as exc:
        raise HTTPException(
            status_code=503,
            detail=error_payload(exc.code, exc.message, exc.retryable),
        ) from exc


@router.get("/sessions")
async def list_agent_sessions(
    include_archived: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        return await service.list_sessions(
            user_id=current_user["id"],
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        )
    except AgentSessionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_payload(exc.code, exc.message, exc.retryable),
        ) from exc


@router.get("/sessions/{session_id}")
async def get_agent_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        return await service.get_session_detail(
            session_id=session_id,
            user_id=current_user["id"],
            authorization=authorization(request),
        )
    except AgentSessionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_payload(exc.code, exc.message, exc.retryable),
        ) from exc


@router.post("/sessions")
async def create_agent_session(
    request: Request,
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        body = await request.json() if request.headers.get("content-length") else {}
        return await service.create_session(
            user_id=current_user["id"],
            title=body.get("title"),
        )
    except AgentSessionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_payload(exc.code, exc.message, exc.retryable),
        ) from exc


@router.patch("/sessions/{session_id}")
async def update_agent_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        body = await request.json()
        return await service.rename_session(
            session_id=session_id,
            user_id=current_user["id"],
            title=body.get("title"),
        )
    except AgentSessionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_payload(exc.code, exc.message, exc.retryable),
        ) from exc


@router.delete("/sessions/{session_id}")
@router.post("/sessions/{session_id}/archive")
async def archive_agent_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        return await service.archive_session(
            session_id=session_id,
            user_id=current_user["id"],
        )
    except AgentSessionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_payload(exc.code, exc.message, exc.retryable),
        ) from exc


@router.get("/sessions/{session_id}/snapshot")
async def get_agent_session_snapshot(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    snapshot = await AgentSnapshotService(session).build(session_id, current_user["id"])
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail=error_payload("SESSION_NOT_FOUND", "Session not found", False),
        )
    return snapshot
