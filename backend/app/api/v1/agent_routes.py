"""Backend Agent Gateway routes."""

import json
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config.database import get_db, get_session_maker
from app.repositories.factory import get_campaign_repo, get_material_repo, get_project_repo
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository
from app.services.agent_gateway import AgentGatewayError, AgentGatewayService
from app.services.business_context_builder import BusinessContextBuilder
from app.services.session_lock import SessionBusyError, session_lock_manager
from app.services.side_effect_service import SideEffectService

router = APIRouter(prefix="/agent", tags=["agent"])


def _authorization(request: Request) -> str | None:
    value = request.headers.get("Authorization")
    return value if value else None


def _error_payload(code: str, message: str, retryable: bool, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "retryable": retryable, "details": details or {}}}


def _sse_event(event: str, data: dict, event_id: str | int | None = None) -> bytes:
    parts = []
    if event_id is not None:
        parts.append(f"id: {event_id}")
    parts.append(f"event: {event}")
    parts.append(f"data: {json.dumps(data, ensure_ascii=False, default=str)}")
    return ("\n".join(parts) + "\n\n").encode("utf-8")


def _single_sse_response(event: str, data: dict) -> StreamingResponse:
    async def generator():
        yield _sse_event(event, data)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def get_agent_gateway() -> AgentGatewayService:
    return AgentGatewayService()


def get_session_state_repo(session: AsyncSession = Depends(get_db)) -> SqliteSessionStateRepository:
    return SqliteSessionStateRepository(session)


def get_business_context_builder(session: AsyncSession = Depends(get_db)) -> BusinessContextBuilder:
    return BusinessContextBuilder(
        project_repo=get_project_repo(session),
        campaign_repo=get_campaign_repo(session),
        material_repo=get_material_repo(session),
    )


async def _with_session(callback):
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            result = await callback(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


async def _get_session_state_short_tx(session_id: str, user_id: str) -> dict | None:
    async def callback(session: AsyncSession):
        return await SqliteSessionStateRepository(session).get(session_id, user_id)
    return await _with_session(callback)


async def _get_or_create_session_state(session_id: str, user_id: str) -> dict:
    async def callback(session: AsyncSession):
        repo = SqliteSessionStateRepository(session)
        state = await repo.get(session_id, user_id)
        if state:
            return state
        return await repo.create(session_id=session_id, user_id=user_id)
    return await _with_session(callback)


async def _update_ui_snapshot_short_tx(session_id: str, user_id: str, version: int, snapshot: dict) -> dict:
    async def callback(session: AsyncSession):
        return await SqliteSessionStateRepository(session).update_ui_snapshot(session_id, user_id, version, snapshot)
    return await _with_session(callback)


async def _mark_running_short_tx(session_id: str, user_id: str, version: int) -> dict:
    async def callback(session: AsyncSession):
        return await SqliteSessionStateRepository(session).mark_running(session_id, user_id, version)
    return await _with_session(callback)


async def _mark_active_short_tx(session_id: str, user_id: str, version: int) -> dict:
    async def callback(session: AsyncSession):
        return await SqliteSessionStateRepository(session).mark_active(session_id, user_id, version)
    return await _with_session(callback)


async def _mark_error_short_tx(session_id: str, user_id: str, version: int, error: dict) -> dict:
    async def callback(session: AsyncSession):
        return await SqliteSessionStateRepository(session).mark_error(session_id, user_id, version, error)
    return await _with_session(callback)


async def _build_business_context_short_tx(state: dict, user_id: str) -> str:
    async def callback(session: AsyncSession):
        builder = BusinessContextBuilder(
            project_repo=get_project_repo(session),
            campaign_repo=get_campaign_repo(session),
            material_repo=get_material_repo(session),
        )
        return await builder.build(state, user_id)
    return await _with_session(callback)


@router.get("/health")
async def agent_health(gateway: AgentGatewayService = Depends(get_agent_gateway)):
    try:
        return await gateway.health()
    except AgentGatewayError as exc:
        raise HTTPException(status_code=503, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc


@router.get("/sessions")
async def list_agent_sessions(
    request: Request,
    current_user: dict = Depends(get_current_user),
    gateway: AgentGatewayService = Depends(get_agent_gateway),
):
    try:
        return await gateway.list_sessions(_authorization(request))
    except AgentGatewayError as exc:
        raise HTTPException(status_code=503, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc


@router.post("/sessions")
async def create_agent_session(
    request: Request,
    current_user: dict = Depends(get_current_user),
    gateway: AgentGatewayService = Depends(get_agent_gateway),
    state_repo: SqliteSessionStateRepository = Depends(get_session_state_repo),
):
    try:
        session = await gateway.create_session(_authorization(request))
    except AgentGatewayError as exc:
        raise HTTPException(status_code=503, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc

    session_id = session.get("session_id") or session.get("id")
    if not session_id:
        raise HTTPException(status_code=502, detail=_error_payload("AGENT_BAD_RESPONSE", "Agent session response missing session_id", False))

    existing = await state_repo.get(session_id, current_user["id"])
    if not existing:
        await state_repo.create(session_id=session_id, user_id=current_user["id"])
    return session


@router.post("/runs")
async def run_agent(
    request: Request,
    current_user: dict = Depends(get_current_user),
    gateway: AgentGatewayService = Depends(get_agent_gateway),
):
    body = await request.json()
    prompt = body.get("prompt", "")
    session_id = body.get("session_id") or f"sess_{uuid4().hex}"
    task_type = body.get("task_type", "conversation")
    context_snapshot = body.get("context_snapshot")
    run_id = f"run_{uuid4().hex}"

    state = await _get_or_create_session_state(session_id, current_user["id"])
    if state.get("status") == "running":
        return _single_sse_response("error", _error_payload("SESSION_BUSY", "当前会话正在执行，请稍后再试", True))

    changelog_start_index = len(state.get("changelog") or [])

    if context_snapshot is not None:
        state = await _update_ui_snapshot_short_tx(session_id, current_user["id"], state["version"], context_snapshot)

    business_context_summary = await _build_business_context_short_tx(state, current_user["id"])

    async def stream_generator():
        latest_state = await _get_session_state_short_tx(session_id, current_user["id"])
        if latest_state is None:
            yield _sse_event("error", _error_payload("SESSION_NOT_FOUND", "Session State not found", False))
            return

        try:
            async with session_lock_manager.acquire(session_id):
                await _mark_running_short_tx(session_id, current_user["id"], latest_state["version"])
                yield _sse_event(
                    "run_status",
                    {"run_id": run_id, "session_id": session_id, "status": "running"},
                )
                agent_payload = {
                    "prompt": prompt,
                    "session_id": session_id,
                    "task_type": task_type,
                    "business_context_summary": business_context_summary,
                    "run_meta": {"run_id": run_id, "user_id": current_user["id"]},
                    "context": {"auth_token": (_authorization(request) or "").removeprefix("Bearer ")},
                }
                try:
                    async for chunk in gateway.stream_run(_authorization(request), agent_payload):
                        yield chunk
                    current = await _get_session_state_short_tx(session_id, current_user["id"])
                    if current:
                        new_changelog = (current.get("changelog") or [])[changelog_start_index:]
                        for side_effect in SideEffectService().from_changelog_entries(new_changelog):
                            yield _sse_event("side_effect", side_effect.model_dump())
                        await _mark_active_short_tx(session_id, current_user["id"], current["version"])
                    yield _sse_event(
                        "run_status",
                        {"run_id": run_id, "session_id": session_id, "status": "completed"},
                    )
                except AgentGatewayError as exc:
                    current = await _get_session_state_short_tx(session_id, current_user["id"])
                    if current:
                        await _mark_error_short_tx(
                            session_id,
                            current_user["id"],
                            current["version"],
                            {"code": exc.code, "message": exc.message, "retryable": exc.retryable, "at": datetime.utcnow().isoformat()},
                        )
                    yield _sse_event("error", _error_payload(exc.code, exc.message, exc.retryable))
        except SessionBusyError:
            yield _sse_event("error", _error_payload("SESSION_BUSY", "当前会话正在执行，请稍后再试", True))

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
