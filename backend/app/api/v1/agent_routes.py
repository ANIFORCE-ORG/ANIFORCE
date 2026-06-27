"""Backend Agent Gateway routes."""

import asyncio
import json
from datetime import datetime
from time import perf_counter
from uuid import uuid4

from loguru import logger

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config.database import get_db, get_session_maker
from app.repositories.factory import get_campaign_repo, get_material_repo, get_project_repo
from app.repositories.impl.sqlite_agent_session_repo import SqliteAgentSessionRepository
from app.repositories.impl.sqlite_agent_message_repo import SqliteAgentMessageRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository
from app.services.agent_message_service import AgentMessageService
from app.services.agent_run_service import AgentRunError, AgentRunService
from app.services.agent_session_service import AgentSessionError, AgentSessionService
from app.services.agent_gateway import AgentGatewayError, AgentGatewayService
from app.services.agent_run_event_bus import agent_run_event_bus
from app.services.business_context_builder import BusinessContextBuilder
from app.services.chat_event_assembler import ChatEventAssembler
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


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


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


def get_agent_session_service(session: AsyncSession = Depends(get_db)) -> AgentSessionService:
    return AgentSessionService(
        session_repo=SqliteAgentSessionRepository(session),
        state_repo=SqliteSessionStateRepository(session),
        message_repo=SqliteAgentMessageRepository(session),
    )


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


async def _create_agent_session_short_tx(user_id: str, title: str | None = None) -> dict:
    async def callback(session: AsyncSession):
        service = AgentSessionService(
            session_repo=SqliteAgentSessionRepository(session),
            state_repo=SqliteSessionStateRepository(session),
            message_repo=SqliteAgentMessageRepository(session),
        )
        return await service.create_session(user_id=user_id, title=title)
    return await _with_session(callback)


async def _require_active_agent_session_short_tx(session_id: str, user_id: str) -> dict:
    async def callback(session: AsyncSession):
        service = AgentSessionService(
            session_repo=SqliteAgentSessionRepository(session),
            state_repo=SqliteSessionStateRepository(session),
            message_repo=SqliteAgentMessageRepository(session),
        )
        return await service.require_active(session_id=session_id, user_id=user_id)
    return await _with_session(callback)


async def _touch_agent_session_short_tx(session_id: str, user_id: str) -> None:
    async def callback(session: AsyncSession):
        service = AgentSessionService(
            session_repo=SqliteAgentSessionRepository(session),
            state_repo=SqliteSessionStateRepository(session),
            message_repo=SqliteAgentMessageRepository(session),
        )
        await service.touch(session_id=session_id, user_id=user_id)
    await _with_session(callback)


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


async def _create_or_reuse_run_short_tx(
    *,
    session_id: str,
    user_id: str,
    input_text: str,
    idempotency_key: str | None,
) -> tuple[dict, bool]:
    async def callback(session: AsyncSession):
        service = AgentRunService(SqliteAgentRunRepository(session))
        return await service.create_or_reuse(
            session_id=session_id,
            user_id=user_id,
            input_text=input_text,
            idempotency_key=idempotency_key,
        )
    return await _with_session(callback)


async def _get_run_short_tx(run_id: str, user_id: str) -> dict:
    async def callback(session: AsyncSession):
        return await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, user_id)
    return await _with_session(callback)


async def _mark_run_status_short_tx(
    run_id: str,
    user_id: str,
    status: str,
    *,
    usage: dict | None = None,
    error: dict | None = None,
) -> dict | None:
    async def callback(session: AsyncSession):
        service = AgentRunService(SqliteAgentRunRepository(session))
        if status == "running":
            return await service.mark_running(run_id, user_id)
        if status == "completed":
            return await service.mark_completed(run_id, user_id, usage=usage)
        if status == "cancelled":
            return await service.mark_cancelled(run_id, user_id)
        return await service.mark_error(run_id, user_id, error or {})
    return await _with_session(callback)


async def _append_agent_message_short_tx(
    *,
    session_id: str,
    user_id: str,
    role: str,
    content_json: dict,
    run_id: str | None = None,
) -> dict:
    async def callback(session: AsyncSession):
        service = AgentMessageService(SqliteAgentMessageRepository(session))
        return await service.append(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content_json=content_json,
            run_id=run_id,
        )
    return await _with_session(callback)


@router.get("/health")
async def agent_health(gateway: AgentGatewayService = Depends(get_agent_gateway)):
    try:
        return await gateway.health()
    except AgentGatewayError as exc:
        raise HTTPException(status_code=503, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc


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
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc


@router.get("/sessions/{session_id}")
async def get_agent_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        return await service.get_session_detail(session_id=session_id, user_id=current_user["id"])
    except AgentSessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc


@router.post("/sessions")
async def create_agent_session(
    request: Request,
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        body = await request.json() if request.headers.get("content-length") else {}
        return await service.create_session(user_id=current_user["id"], title=body.get("title"))
    except AgentSessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc


@router.patch("/sessions/{session_id}")
async def update_agent_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        body = await request.json()
        return await service.rename_session(session_id=session_id, user_id=current_user["id"], title=body.get("title"))
    except AgentSessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc


@router.delete("/sessions/{session_id}")
async def delete_agent_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        return await service.archive_session(session_id=session_id, user_id=current_user["id"])
    except AgentSessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc


@router.post("/sessions/{session_id}/archive")
async def archive_agent_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        return await service.archive_session(session_id=session_id, user_id=current_user["id"])
    except AgentSessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc


@router.post("/tasks/{task_id}/cancel")
async def cancel_agent_task(task_id: str, current_user: dict = Depends(get_current_user)):
    raise HTTPException(
        status_code=410,
        detail=_error_payload(
            "TASK_CANCEL_REMOVED",
            "Task cancellation has moved to /api/v1/agent/runs/{run_id}/cancel",
            retryable=False,
            details={"task_id": task_id, "user_id": current_user["id"]},
        ),
    )


@router.get("/runs/{run_id}")
async def get_agent_run(
    run_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        return await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, current_user["id"])
    except AgentRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc


@router.post("/runs/{run_id}/cancel")
async def cancel_agent_run(
    run_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    gateway: AgentGatewayService = Depends(get_agent_gateway),
):
    service = AgentRunService(SqliteAgentRunRepository(session))
    try:
        run = await service.get(run_id, current_user["id"])
    except AgentRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc

    updated_run = await service.mark_cancelled(run_id, current_user["id"])
    await session.commit()
    current = await _get_session_state_short_tx(run["session_id"], current_user["id"])
    if current:
        await _mark_active_short_tx(run["session_id"], current_user["id"], current["version"])
    if updated_run and updated_run["status"] == "cancelled":
        try:
            await gateway.cancel_run(_authorization(request), run_id)
        except AgentGatewayError:
            # Runtime cancellation is best-effort; backend run status is already cancelled.
            pass
    return {"run_id": run_id, "session_id": run["session_id"], "status": (updated_run or run)["status"]}


@router.post("/runs")
async def run_agent(
    request: Request,
    current_user: dict = Depends(get_current_user),
    gateway: AgentGatewayService = Depends(get_agent_gateway),
):
    """Start an Agent run and return run metadata.

    Run execution continues in a backend background task. Clients observe the run
    through GET /api/v1/agent/runs/{run_id}/events.
    """
    request_start = perf_counter()
    body = await request.json()
    body_parsed_ms = _elapsed_ms(request_start)
    prompt = body.get("prompt", "")
    requested_session_id = body.get("session_id")
    task_type = body.get("task_type", "conversation")
    context_snapshot = body.get("context_snapshot")
    user_id = current_user["id"]
    authorization = _authorization(request)
    idempotency_key = body.get("idempotency_key") or request.headers.get("Idempotency-Key")
    if requested_session_id:
        try:
            await _require_active_agent_session_short_tx(requested_session_id, user_id)
        except AgentSessionError as exc:
            raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable)) from exc
        session_id = requested_session_id
    else:
        created_session = await _create_agent_session_short_tx(user_id, prompt[:50] if prompt else "新对话")
        session_id = created_session["session_id"]
    try:
        run, reused = await _create_or_reuse_run_short_tx(
            session_id=session_id,
            user_id=user_id,
            input_text=prompt,
            idempotency_key=idempotency_key,
        )
    except AgentRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable, {"run": exc.run})) from exc
    run_id = run["run_id"]
    perf_log = logger.bind(run_id=run_id, session_id=session_id, user_id=user_id)
    if reused:
        return {"run_id": run_id, "session_id": session_id, "status": run["status"], "reused": True}

    state_start = perf_counter()
    state = await _get_or_create_session_state(session_id, user_id)
    state_ms = _elapsed_ms(state_start)
    changelog_start_index = len(state.get("changelog") or [])

    ui_snapshot_ms = 0
    if context_snapshot is not None:
        ui_snapshot_start = perf_counter()
        state = await _update_ui_snapshot_short_tx(session_id, user_id, state["version"], context_snapshot)
        ui_snapshot_ms = _elapsed_ms(ui_snapshot_start)

    business_context_start = perf_counter()
    business_context_summary = await _build_business_context_short_tx(state, user_id)
    business_context_ms = _elapsed_ms(business_context_start)
    perf_log.info(
        "[PERF][agent_first_token] backend.run_start total_ms={} body_parse_ms={} state_ms={} ui_snapshot_ms={} business_context_ms={} prompt_chars={} context_chars={}",
        _elapsed_ms(request_start),
        body_parsed_ms,
        state_ms,
        ui_snapshot_ms,
        business_context_ms,
        len(prompt),
        len(business_context_summary or ""),
    )

    await agent_run_event_bus.create_run(run_id=run_id, session_id=session_id, user_id=user_id)
    await _append_agent_message_short_tx(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content_json=ChatEventAssembler().user_message(prompt),
        run_id=run_id,
    )
    await _touch_agent_session_short_tx(session_id, user_id)

    agent_payload = {
        "run_id": run_id,
        "prompt": prompt,
        "session_id": session_id,
        "user_id": user_id,
        "task_type": task_type,
        "auth_token": authorization or "",
        "business_context_summary": business_context_summary,
        "run_meta": {"run_id": run_id, "user_id": user_id},
        "context": {"auth_token": (authorization or "").removeprefix("Bearer ")},
    }

    asyncio.create_task(
        _consume_agent_run_background(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            authorization=authorization,
            agent_payload=agent_payload,
            changelog_start_index=changelog_start_index,
            gateway=gateway,
            perf_start=request_start,
        )
    )

    return {"run_id": run_id, "session_id": session_id, "status": "running"}


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    after_sequence: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Observe a run through standard SSE with sequence-based replay."""

    async def event_generator():
        try:
            async for event in agent_run_event_bus.subscribe(run_id, current_user["id"], after_sequence=after_sequence):
                yield _sse_event(event.event, event.data, event.sequence)
        except KeyError:
            yield _sse_event("error", _error_payload("RUN_NOT_FOUND", "Run not found", False))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _consume_agent_run_background(
    *,
    run_id: str,
    session_id: str,
    user_id: str,
    authorization: str | None,
    agent_payload: dict,
    changelog_start_index: int,
    gateway: AgentGatewayService,
    perf_start: float,
) -> None:
    perf_log = logger.bind(run_id=run_id, session_id=session_id, user_id=user_id)
    latest_state = await _get_session_state_short_tx(session_id, user_id)
    if latest_state is None:
        await agent_run_event_bus.publish(run_id, "error", _error_payload("SESSION_NOT_FOUND", "Session State not found", False), terminal=True)
        return

    first_agent_chunk_logged = False
    first_thinking_logged = False
    first_message_logged = False
    upstream_bytes = 0
    stream_buffer = ""

    try:
        lock_start = perf_counter()
        async with session_lock_manager.acquire(session_id):
            lock_wait_ms = _elapsed_ms(lock_start)
            mark_running_start = perf_counter()
            await _mark_running_short_tx(session_id, user_id, latest_state["version"])
            mark_running_ms = _elapsed_ms(mark_running_start)
            perf_log.info(
                "[PERF][agent_first_token] backend.background_start total_ms={} lock_wait_ms={} mark_running_ms={}",
                _elapsed_ms(perf_start),
                lock_wait_ms,
                mark_running_ms,
            )
            current_run = await _mark_run_status_short_tx(run_id, user_id, "running")
            if current_run and current_run["status"] in {"completed", "error", "cancelled"}:
                current = await _get_session_state_short_tx(session_id, user_id)
                if current:
                    await _mark_active_short_tx(session_id, user_id, current["version"])
                await agent_run_event_bus.publish(
                    run_id,
                    "run_status",
                    {"run_id": run_id, "session_id": session_id, "status": current_run["status"]},
                    terminal=True,
                )
                return
            await agent_run_event_bus.publish(run_id, "run_status", {"run_id": run_id, "session_id": session_id, "status": "running"})

            gateway_start = perf_counter()
            persisted_events: list[tuple[str, dict]] = []
            try:
                async for chunk in gateway.stream_run(authorization, agent_payload):
                    upstream_bytes += len(chunk)
                    if not first_agent_chunk_logged:
                        first_agent_chunk_logged = True
                        perf_log.info(
                            "[PERF][agent_first_token] backend.first_agent_chunk total_ms={} gateway_wait_ms={} bytes={}",
                            _elapsed_ms(perf_start),
                            _elapsed_ms(gateway_start),
                            len(chunk),
                        )
                    if not first_message_logged and b"event: message.updated" in chunk:
                        first_message_logged = True
                        perf_log.info(
                            "[PERF][agent_first_token] backend.first_message_delta total_ms={} gateway_wait_ms={} upstream_bytes_before_first_delta={}",
                            _elapsed_ms(perf_start),
                            _elapsed_ms(gateway_start),
                            upstream_bytes,
                        )
                    stream_buffer += chunk.decode("utf-8", errors="ignore")
                    events, stream_buffer = _parse_sse_events(stream_buffer)
                    for event_name, data in events:
                        if not first_thinking_logged and event_name == "thinking.updated":
                            first_thinking_logged = True
                            perf_log.info(
                                "[PERF][agent_first_token] backend.first_thinking_delta total_ms={} gateway_wait_ms={} upstream_bytes_before_first_thinking={}",
                                _elapsed_ms(perf_start),
                                _elapsed_ms(gateway_start),
                                upstream_bytes,
                            )
                        persisted_events.append((event_name, data))
                        await agent_run_event_bus.publish(run_id, event_name, data)

                # Flush any final event if upstream did not end with a blank line.
                events, stream_buffer = _parse_sse_events(stream_buffer + "\n\n")
                for event_name, data in events:
                    persisted_events.append((event_name, data))
                    await agent_run_event_bus.publish(run_id, event_name, data)

                perf_log.info(
                    "[PERF][agent_first_token] backend.agent_stream_done total_ms={} gateway_total_ms={} upstream_bytes={} first_delta_seen={}",
                    _elapsed_ms(perf_start),
                    _elapsed_ms(gateway_start),
                    upstream_bytes,
                    first_message_logged,
                )
                current = await _get_session_state_short_tx(session_id, user_id)
                if current:
                    new_changelog = (current.get("changelog") or [])[changelog_start_index:]
                    for side_effect in SideEffectService().from_changelog_entries(new_changelog):
                        await agent_run_event_bus.publish(run_id, "side_effect", side_effect.model_dump())
                    await _mark_active_short_tx(session_id, user_id, current["version"])

                latest_run = await _get_run_short_tx(run_id, user_id)
                if latest_run["status"] == "cancelled":
                    await agent_run_event_bus.publish(
                        run_id,
                        "run_status",
                        {"run_id": run_id, "session_id": session_id, "status": "cancelled"},
                        terminal=True,
                    )
                    return

                assistant_content = ChatEventAssembler().assemble_assistant_message(persisted_events)
                if assistant_content.get("blocks"):
                    await _append_agent_message_short_tx(
                        session_id=session_id,
                        user_id=user_id,
                        role="assistant",
                        content_json=assistant_content,
                        run_id=run_id,
                    )
                await _mark_run_status_short_tx(run_id, user_id, "completed", usage=assistant_content.get("usage"))
                await agent_run_event_bus.publish(
                    run_id,
                    "run_status",
                    {"run_id": run_id, "session_id": session_id, "status": "completed"},
                    terminal=True,
                )
            except AgentGatewayError as exc:
                current = await _get_session_state_short_tx(session_id, user_id)
                if current:
                    await _mark_error_short_tx(
                        session_id,
                        user_id,
                        current["version"],
                        {"code": exc.code, "message": exc.message, "retryable": exc.retryable, "at": datetime.utcnow().isoformat()},
                    )
                error_payload = {"code": exc.code, "message": exc.message, "retryable": exc.retryable, "at": datetime.utcnow().isoformat()}
                await _mark_run_status_short_tx(run_id, user_id, "error", error=error_payload)
                await _append_agent_message_short_tx(
                    session_id=session_id,
                    user_id=user_id,
                    role="assistant",
                    content_json=ChatEventAssembler().error_message(exc.code, exc.message),
                    run_id=run_id,
                )
                await agent_run_event_bus.publish(run_id, "error", _error_payload(exc.code, exc.message, exc.retryable), terminal=True)
    except SessionBusyError:
        await _mark_run_status_short_tx(run_id, user_id, "error", error={"code": "SESSION_BUSY", "message": "当前会话正在执行，请稍后再试"})
        await agent_run_event_bus.publish(run_id, "error", _error_payload("SESSION_BUSY", "当前会话正在执行，请稍后再试", True), terminal=True)
    except Exception as exc:
        perf_log.exception("backend background run failed")
        current = await _get_session_state_short_tx(session_id, user_id)
        if current:
            await _mark_error_short_tx(
                session_id,
                user_id,
                current["version"],
                {"code": "RUN_FAILED", "message": str(exc), "retryable": True, "at": datetime.utcnow().isoformat()},
            )
        await _mark_run_status_short_tx(run_id, user_id, "error", error={"code": "RUN_FAILED", "message": str(exc), "retryable": True, "at": datetime.utcnow().isoformat()})
        await agent_run_event_bus.publish(run_id, "error", _error_payload("RUN_FAILED", str(exc), True), terminal=True)


def _parse_sse_events(buffer: str) -> tuple[list[tuple[str, dict]], str]:
    events: list[tuple[str, dict]] = []
    while "\n\n" in buffer:
        raw, buffer = buffer.split("\n\n", 1)
        event_name = "message"
        data_lines: list[str] = []
        for line in raw.splitlines():
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        data_text = "\n".join(data_lines)
        if not data_text:
            data: dict = {}
        else:
            try:
                parsed = json.loads(data_text)
                data = parsed if isinstance(parsed, dict) else {"value": parsed}
            except json.JSONDecodeError:
                data = {"message": data_text}
        events.append((event_name, data))
    return events, buffer
