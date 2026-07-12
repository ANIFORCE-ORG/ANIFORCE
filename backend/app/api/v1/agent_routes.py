"""Backend Agent Gateway routes."""

import asyncio
import json
from time import perf_counter

from loguru import logger

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config.database import get_db, get_session_maker
from app.repositories.factory import get_campaign_repo, get_material_repo, get_project_repo
from app.repositories.impl.sqlite_agent_session_repo import SqliteAgentSessionRepository
from app.repositories.impl.sqlite_agent_message_repo import SqliteAgentMessageRepository
from app.repositories.impl.sqlite_agent_run_event_repo import SqliteAgentRunEventRepository
from app.repositories.impl.sqlite_agent_fact_repo import SqliteAgentToolCallRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.repositories.impl.sqlite_agent_approval_repo import SqliteAgentApprovalRepository
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository
from app.services.agent_run_service import AgentRunError, AgentRunService
from app.services.agent_snapshot_service import AgentSnapshotService
from app.services.agent_approval_service import AgentApprovalError, AgentApprovalService
from app.services.agent_session_service import AgentSessionError, AgentSessionService
from app.services.agent_gateway import AgentGatewayError, AgentGatewayService
from app.services.business_context_builder import BusinessContextBuilder
from app.services.chat_event_assembler import ChatEventAssembler
from app.services.redis_run_event_stream import RedisRunEventStream

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

        )
        return await service.create_session(user_id=user_id, title=title)
    return await _with_session(callback)


async def _require_active_agent_session_short_tx(session_id: str, user_id: str) -> dict:
    async def callback(session: AsyncSession):
        service = AgentSessionService(
            session_repo=SqliteAgentSessionRepository(session),
            state_repo=SqliteSessionStateRepository(session),

        )
        return await service.require_active(session_id=session_id, user_id=user_id)
    return await _with_session(callback)


async def _touch_agent_session_short_tx(session_id: str, user_id: str) -> None:
    async def callback(session: AsyncSession):
        service = AgentSessionService(
            session_repo=SqliteAgentSessionRepository(session),
            state_repo=SqliteSessionStateRepository(session),

        )
        await service.touch(session_id=session_id, user_id=user_id)
    await _with_session(callback)


async def _update_ui_snapshot_short_tx(session_id: str, user_id: str, version: int, snapshot: dict) -> dict:
    async def callback(session: AsyncSession):
        return await SqliteSessionStateRepository(session).update_ui_snapshot(session_id, user_id, version, snapshot)
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
    execution_context: dict | None = None,
) -> tuple[dict, bool]:
    async def callback(session: AsyncSession):
        service = AgentRunService(SqliteAgentRunRepository(session))
        run, reused = await service.create_or_reuse(
            session_id=session_id,
            user_id=user_id,
            input_text=input_text,
            idempotency_key=idempotency_key,
            execution_context=execution_context,
        )
        if not reused:
            await SqliteAgentMessageRepository(session).create(
                session_id=session_id,
                user_id=user_id,
                role="user",
                content_json=ChatEventAssembler().user_message(input_text),
                run_id=run["run_id"],
            )
        return run, reused
    return await _with_session(callback)


async def _get_run_short_tx(run_id: str, user_id: str) -> dict:
    async def callback(session: AsyncSession):
        return await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, user_id)
    return await _with_session(callback)


async def _list_persisted_run_events_short_tx(
    run_id: str,
    user_id: str,
    after_sequence: int,
) -> tuple[dict, list[dict]]:
    async def callback(session: AsyncSession):
        run = await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, user_id)
        events = await SqliteAgentRunEventRepository(session).list_after(run_id, after_sequence)
        return run, events

    return await _with_session(callback)


async def _claim_approvals_short_tx(
    *,
    run_id: str,
    checkpoint_ref: str,
    user_id: str,
    decision: str,
    edited_arguments: dict | None,
    argument_diff: list | None,
    rejection_message: str | None,
    resume_payload: dict | None = None,
) -> list[dict]:
    async def callback(session: AsyncSession):
        try:
            items = await AgentApprovalService(SqliteAgentApprovalRepository(session)).claim(
                run_id=run_id,
                checkpoint_ref=checkpoint_ref,
                user_id=user_id,
                decision=decision,
                edited_arguments=edited_arguments,
                argument_diff=argument_diff,
                rejection_message=rejection_message,
                claimed_by=user_id,
            )
            if decision == "reject":
                tool_repo = SqliteAgentToolCallRepository(session)
                for item in items:
                    await tool_repo.reject_before_execution(
                        tool_call_id=str(item.get("tool_call_id") or ""),
                        reason=rejection_message,
                    )
            if resume_payload is not None:
                await AgentRunService(SqliteAgentRunRepository(session)).enqueue_resume(
                    run_id,
                    user_id,
                    resume_payload,
                )
            return items, None
        except AgentApprovalError as exc:
            if exc.code == "APPROVAL_EXPIRED":
                return [], exc
            raise

    items, error = await _with_session(callback)
    if error:
        raise error
    return items


async def _mark_approvals_status_short_tx(
    *,
    run_id: str,
    checkpoint_ref: str,
    user_id: str,
    status: str,
) -> int:
    async def callback(session: AsyncSession):
        return await SqliteAgentApprovalRepository(session).mark_checkpoint_status(
            run_id=run_id,
            checkpoint_ref=checkpoint_ref,
            user_id=user_id,
            status=status,
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
    request: Request,
    current_user: dict = Depends(get_current_user),
    service: AgentSessionService = Depends(get_agent_session_service),
):
    try:
        return await service.get_session_detail(
            session_id=session_id,
            user_id=current_user["id"],
            authorization=_authorization(request),
        )
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


@router.get("/runs/{run_id}/approvals")
async def list_run_approvals(
    run_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        run = await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, current_user["id"])
    except AgentRunError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=_error_payload(exc.code, exc.message, exc.retryable),
        ) from exc
    return await SqliteAgentApprovalRepository(session).list_for_run(
        run_id,
        current_user["id"],
    )


@router.post("/runs/{run_id}/approvals/{checkpoint_id}")
async def resolve_run_approval(
    run_id: str,
    checkpoint_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    gateway: AgentGatewayService = Depends(get_agent_gateway),
):
    body = await request.json()
    decision = body.get("decision")
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail=_error_payload("INVALID_DECISION", "decision must be approve or reject"))

    user_id = current_user["id"]
    run = await _get_run_short_tx(run_id, user_id)
    if run.get("checkpoint_ref") != checkpoint_id:
        raise HTTPException(status_code=409, detail=_error_payload("CHECKPOINT_MISMATCH", "Checkpoint does not belong to run"))

    transient_stream = RedisRunEventStream()
    resume_after_sequence = 0
    if transient_stream.enabled:
        try:
            resume_after_sequence = await transient_stream.latest_sequence(run_id)
        except Exception:
            logger.exception("Read Redis Agent event sequence failed before resume: run_id={}", run_id)
    use_transient_resume = transient_stream.enabled and resume_after_sequence > 0

    latest_state = await _get_session_state_short_tx(run["session_id"], user_id)
    latest_context = await _build_business_context_short_tx(latest_state or {}, user_id)
    resume_payload = {
        "decision": decision,
        "rejection_message": body.get("rejection_message"),
        "always": bool(body.get("always", False)),
        "edited_arguments": body.get("edited_arguments"),
        "argument_diff": body.get("argument_diff"),
        "checkpoint_id": checkpoint_id,
        "context_override": {
            "business_context_summary": latest_context,
            "ui_snapshot": (latest_state or {}).get("ui_snapshot") or {},
            "session_state": latest_state or {},
        },
    }
    try:
        await _claim_approvals_short_tx(
            run_id=run_id,
            checkpoint_ref=checkpoint_id,
            user_id=user_id,
            decision=decision,
            edited_arguments=body.get("edited_arguments"),
            argument_diff=body.get("argument_diff"),
            rejection_message=body.get("rejection_message"),
            resume_payload=resume_payload,
        )
    except AgentApprovalError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=_error_payload(exc.code, exc.message, retryable=False),
        ) from exc

    async def event_generator():
        if use_transient_resume:
            try:
                async for event in transient_stream.subscribe(run_id, resume_after_sequence):
                    yield _sse_event(event.event, event.data, event.sequence)
                    if event.event in {"runtime.completed", "runtime.error", "runtime.aborted", "runtime.requires_action"}:
                        return
                return
            except Exception:
                logger.exception("Redis Agent resume subscription failed: run_id={}", run_id)
            finally:
                await transient_stream.close()

        sequence = int(run.get("last_event_sequence") or 0)
        while True:
            current, events = await _list_persisted_run_events_short_tx(run_id, user_id, sequence)
            for event in events:
                sequence = event["sequence"]
                event_name = {
                    "run.resuming": "runtime.started",
                    "run.completed": "runtime.completed",
                    "run.error": "runtime.error",
                    "run.cancelled": "runtime.aborted",
                }.get(event["event_type"], event["event_type"])
                yield _sse_event(event_name, event["payload"], sequence)
            if current["status"] in {"completed", "error", "cancelled", "requires_action"}:
                return
            await asyncio.sleep(0.2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


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

    updated_run = await service.request_cancel(run_id, current_user["id"])
    await session.commit()
    try:
        await gateway.cancel_run(_authorization(request), run_id)
    except AgentGatewayError:
        pass
    return {"run_id": run_id, "session_id": run["session_id"], "status": updated_run["status"]}


@router.post("/runs")
async def run_agent(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Persist a queued run for execution by a database-claiming worker."""
    request_start = perf_counter()
    body = await request.json()
    body_parsed_ms = _elapsed_ms(request_start)
    prompt = body.get("prompt", "")
    requested_session_id = body.get("session_id")
    task_type = body.get("task_type", "conversation")
    context_snapshot = body.get("context_snapshot")
    user_id = current_user["id"]
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
    execution_context = {
        "task_type": task_type,
        "business_context_summary": business_context_summary,
        "ui_snapshot": context_snapshot or {},
        "session_state": state,
        "changelog_start_index": changelog_start_index,
    }
    try:
        run, reused = await _create_or_reuse_run_short_tx(
            session_id=session_id,
            user_id=user_id,
            input_text=prompt,
            idempotency_key=idempotency_key,
            execution_context=execution_context,
        )
    except AgentRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc.code, exc.message, exc.retryable, {"run": exc.run})) from exc
    run_id = run["run_id"]
    perf_log = logger.bind(run_id=run_id, session_id=session_id, user_id=user_id)
    if reused:
        return {"run_id": run_id, "session_id": session_id, "status": run["status"], "reused": True}

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

    await _touch_agent_session_short_tx(session_id, user_id)
    return {"run_id": run_id, "session_id": session_id, "status": "queued"}


@router.get("/sessions/{session_id}/snapshot")
async def get_agent_session_snapshot(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    snapshot = await AgentSnapshotService(session).build(session_id, current_user["id"])
    if snapshot is None:
        raise HTTPException(status_code=404, detail=_error_payload("SESSION_NOT_FOUND", "Session not found", False))
    return snapshot


@router.get("/runs/{run_id}/persisted-events")
async def list_persisted_run_events(
    run_id: str,
    after_sequence: int = 0,
    limit: int = 500,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        run = await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, current_user["id"])
    except AgentRunError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=_error_payload(exc.code, exc.message, exc.retryable),
        ) from exc
    events = await SqliteAgentRunEventRepository(session).list_after(
        run_id,
        max(0, after_sequence),
        min(max(1, limit), 500),
    )
    return {
        "run_id": run_id,
        "events": events,
        "last_persisted_sequence": run["last_event_sequence"],
        "terminal": run["status"] in {"completed", "error", "cancelled"},
    }


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    after_sequence: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Observe a run through standard SSE with sequence-based replay."""
    user_id = current_user["id"]
    await _get_run_short_tx(run_id, user_id)
    transient_stream = RedisRunEventStream()

    async def redis_event_generator():
        try:
            async for event in transient_stream.subscribe(run_id, max(0, after_sequence)):
                yield _sse_event(event.event, event.data, event.sequence)
                if event.event in {"runtime.completed", "runtime.error", "runtime.aborted", "runtime.requires_action"}:
                    return
        except Exception:
            logger.exception("Redis Agent event subscription failed: run_id={}", run_id)
            async for chunk in persisted_event_generator():
                yield chunk
        finally:
            await transient_stream.close()

    async def persisted_event_generator():
        sequence = max(0, after_sequence)
        while True:
            try:
                run, events = await _list_persisted_run_events_short_tx(run_id, user_id, sequence)
            except AgentRunError:
                yield _sse_event("error", _error_payload("RUN_NOT_FOUND", "Run not found", False))
                return
            event_name_map = {
                "run.started": "runtime.started",
                "run.resuming": "runtime.started",
                "run.requires_action": "runtime.requires_action",
                "run.completed": "runtime.completed",
                "run.error": "runtime.error",
                "run.cancelled": "runtime.aborted",
            }
            for event in events:
                sequence = event["sequence"]
                event_name = event_name_map.get(event["event_type"], event["event_type"])
                yield _sse_event(event_name, event["payload"], sequence)
            if run["status"] in {"completed", "error", "cancelled", "requires_action"}:
                return
            await asyncio.sleep(0.2)

    return StreamingResponse(
        redis_event_generator() if transient_stream.enabled else persisted_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
