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
from app.repositories.impl.sqlite_agent_run_event_repo import SqliteAgentRunEventRepository
from app.repositories.impl.sqlite_agent_fact_repo import SqliteAgentArtifactRepository, SqliteAgentToolCallRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.repositories.impl.sqlite_agent_approval_repo import SqliteAgentApprovalRepository
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository
from app.services.agent_run_service import AgentRunError, AgentRunService
from app.services.agent_snapshot_service import AgentSnapshotService
from app.services.agent_approval_service import AgentApprovalError, AgentApprovalService
from app.services.agent_session_service import AgentSessionError, AgentSessionService
from app.services.agent_gateway import AgentGatewayError, AgentGatewayService
from app.services.agent_run_event_bus import agent_run_event_bus
from app.services.agent_run_event_processor import AgentRunEventProcessor
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


def _unexpected_run_error(code: str = "RUN_FAILED") -> dict:
    return {
        "code": code,
        "message": "Agent run failed unexpectedly",
        "retryable": True,
        "at": datetime.utcnow().isoformat(),
    }


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


async def _settle_session_after_terminal(
    *,
    session_id: str,
    user_id: str,
    persisted_status: str | None,
    error: dict | None = None,
) -> None:
    current = await _get_session_state_short_tx(session_id, user_id)
    if not current:
        return
    if persisted_status == "error":
        await _mark_error_short_tx(
            session_id,
            user_id,
            current["version"],
            error or {"code": "RUN_FAILED", "message": "Agent run failed", "retryable": True},
        )
        return
    if persisted_status in {"completed", "cancelled", "requires_action"}:
        await _mark_active_short_tx(session_id, user_id, current["version"])


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


async def _persist_run_output_short_tx(
    *,
    run_id: str,
    session_id: str,
    user_id: str,
    events: list[tuple[str, dict]],
    error: dict | None = None,
    complete_usage: dict | None = None,
    final_output: str | None = None,
) -> dict | None:
    async def callback(session: AsyncSession):
        message_repo = SqliteAgentMessageRepository(session)
        if error:
            await message_repo.create(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content_json=ChatEventAssembler().error_message(
                    str(error.get("code") or "RUN_FAILED"),
                    str(error.get("message") or "Agent run failed"),
                ),
                run_id=run_id,
                status="error",
                error_code=str(error.get("code") or "RUN_FAILED"),
            )
            return None

        assembler = ChatEventAssembler()
        tool_repo = SqliteAgentToolCallRepository(session)
        artifact_repo = SqliteAgentArtifactRepository(session)
        for event_name, data in events:
            if event_name != "run_item_stream_event":
                continue
            sdk_type = str(data.get("type") or "")
            item = data.get("item") if isinstance(data.get("item"), dict) else {}
            if sdk_type and sdk_type != "run_item_stream_event":
                continue
            name = str(data.get("name") or "")
            if name == "tool_called":
                call_id, tool_name, arguments = assembler._tool_call_info(item)
                if call_id:
                    await tool_repo.upsert_started(
                        run_id=run_id,
                        tool_call_id=call_id,
                        tool_name=tool_name,
                        arguments=arguments,
                    )
            elif name == "tool_output":
                call_id, result = assembler._tool_output_info(item)
                if call_id:
                    await tool_repo.complete(tool_call_id=call_id, result=result)
        content = assembler.assemble_assistant_message(events)
        await message_repo.create(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content_json=content,
            run_id=run_id,
        )
        for request in [
            data
            for event_name, data in events
            if event_name == "workspace.projection" and isinstance(data, dict)
        ]:
            await artifact_repo.create_projection(
                session_id=session_id,
                run_id=run_id,
                source_tool_call_id=request.get("tool_call_id"),
                surface=str(request.get("surface") or "unknown"),
                payload=request,
            )
        if complete_usage is not None or final_output is not None:
            return await AgentRunService(SqliteAgentRunRepository(session)).mark_completed(
                run_id,
                user_id,
                usage=complete_usage,
                final_output=final_output,
            )
        return None

    return await _with_session(callback)


async def _persist_requires_action_short_tx(
    *,
    run_id: str,
    user_id: str,
    data: dict,
) -> dict | None:
    checkpoint_ref = str(data.get("checkpoint_id") or "")

    async def callback(session: AsyncSession):
        run_service = AgentRunService(SqliteAgentRunRepository(session))
        approval_repo = SqliteAgentApprovalRepository(session)
        existing = await approval_repo.list_for_checkpoint(run_id, checkpoint_ref, user_id)
        if existing:
            return await run_service.get(run_id, user_id)
        updated = await run_service.mark_requires_action(
            run_id,
            user_id,
            checkpoint_ref,
            event_payload={**data, "status": "requires_action"},
        )
        if not updated or updated.get("status") != "requires_action":
            return updated
        if not existing:
            await AgentApprovalService(approval_repo).create_for_interruption(
                run_id=run_id,
                checkpoint_ref=checkpoint_ref,
                user_id=user_id,
                interruptions=list(data.get("interruptions") or []),
                expires_at=data.get("expires_at"),
            )
        return updated

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


async def _mark_run_status_short_tx(
    run_id: str,
    user_id: str,
    status: str,
    *,
    usage: dict | None = None,
    error: dict | None = None,
    checkpoint_ref: str | None = None,
    final_output: str | None = None,
) -> dict | None:
    async def callback(session: AsyncSession):
        service = AgentRunService(SqliteAgentRunRepository(session))
        if status == "running":
            return await service.mark_running(run_id, user_id)
        if status == "completed":
            return await service.mark_completed(
                run_id,
                user_id,
                usage=usage,
                final_output=final_output,
            )
        if status == "cancelled":
            return await service.mark_cancelled(run_id, user_id)
        if status == "requires_action":
            return await service.mark_requires_action(run_id, user_id, checkpoint_ref or "")
        return await service.mark_error(run_id, user_id, error or {})
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
    checkpoint_ref = str(run.get("checkpoint_ref") or "")
    if not checkpoint_ref:
        return []
    return await SqliteAgentApprovalRepository(session).list_for_checkpoint(
        run_id,
        checkpoint_ref,
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

    try:
        await _claim_approvals_short_tx(
            run_id=run_id,
            checkpoint_ref=checkpoint_id,
            user_id=user_id,
            decision=decision,
            edited_arguments=body.get("edited_arguments"),
            argument_diff=body.get("argument_diff"),
            rejection_message=body.get("rejection_message"),
        )
    except AgentApprovalError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=_error_payload(exc.code, exc.message, retryable=False),
        ) from exc

    payload = {
        "decision": decision,
        "rejection_message": body.get("rejection_message"),
        "always": bool(body.get("always", False)),
        "auth_token": _authorization(request),
        "edited_arguments": body.get("edited_arguments"),
        "argument_diff": body.get("argument_diff"),
    }

    async def event_generator():
        stream_buffer = ""
        resolved_status = "rejected" if decision == "reject" else "resolved"

        async def settle_approval(status: str) -> None:
            await _mark_approvals_status_short_tx(
                run_id=run_id,
                checkpoint_ref=checkpoint_id,
                user_id=user_id,
                status=status,
            )
        event_processor = AgentRunEventProcessor(
            event_bus=agent_run_event_bus,
            mark_run_status=_mark_run_status_short_tx,
            persist_requires_action=_persist_requires_action_short_tx,
        )
        try:
            await _mark_run_status_short_tx(run_id, user_id, "running")
            await event_processor.publish_running(run_id=run_id)
            async for chunk in gateway.stream_checkpoint_resume(_authorization(request), checkpoint_id, payload):
                stream_buffer += chunk.decode("utf-8", errors="ignore")
                events, stream_buffer = _parse_sse_events(stream_buffer)
                terminal = False
                for event_name, data in events:
                    result = await event_processor.handle_runtime_event(
                        run_id=run_id,
                        user_id=user_id,
                        event_name=event_name,
                        data=data,
                    )
                    if result.terminal:
                        approval_status = (
                            "failed" if event_name in {"runtime.error", "runtime.aborted"} else resolved_status
                        )
                        await settle_approval(approval_status)
                        terminal = True
                        break
                yield chunk
                if terminal:
                    return

            events, stream_buffer = _parse_sse_events(stream_buffer + "\n\n")
            for event_name, data in events:
                result = await event_processor.handle_runtime_event(
                    run_id=run_id,
                    user_id=user_id,
                    event_name=event_name,
                    data=data,
                )
                if result.terminal:
                    approval_status = (
                        "failed" if event_name in {"runtime.error", "runtime.aborted"} else resolved_status
                    )
                    await settle_approval(approval_status)
                    return
            await settle_approval("failed")
        except Exception:
            logger.exception("checkpoint resume stream failed: run_id={} checkpoint_id={}", run_id, checkpoint_id)
            error = _unexpected_run_error("RESUME_FAILED")
            await _mark_approvals_status_short_tx(
                run_id=run_id,
                checkpoint_ref=checkpoint_id,
                user_id=user_id,
                status="failed",
            )
            await _mark_run_status_short_tx(run_id, user_id, "error", error=error)
            yield "event: runtime.error\n"
            yield f"data: {json.dumps({'run_id': run_id, **error}, ensure_ascii=False)}\n\n"

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

    async def event_generator():
        sequence = max(0, after_sequence)
        while True:
            try:
                run, events = await _list_persisted_run_events_short_tx(
                    run_id,
                    current_user["id"],
                    sequence,
                )
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
            if run["status"] in {"completed", "error", "cancelled"}:
                return
            if run["status"] == "requires_action":
                return
            await asyncio.sleep(0.2)

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
    event_processor = AgentRunEventProcessor(
        event_bus=agent_run_event_bus,
        mark_run_status=_mark_run_status_short_tx,
        persist_requires_action=_persist_requires_action_short_tx,
    )

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
            await event_processor.publish_running(run_id=run_id, session_id=session_id)

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
                    stream_buffer += chunk.decode("utf-8", errors="ignore")
                    events, stream_buffer = _parse_sse_events(stream_buffer)
                    for event_name, data in events:
                        sdk_data = data.get("data") if event_name == "raw_response_event" and isinstance(data, dict) else None
                        sdk_data_type = sdk_data.get("type") if isinstance(sdk_data, dict) else None
                        if not first_message_logged and sdk_data_type == "response.output_text.delta":
                            first_message_logged = True
                            perf_log.info(
                                "[PERF][agent_first_token] backend.first_message_delta total_ms={} gateway_wait_ms={} upstream_bytes_before_first_delta={}",
                                _elapsed_ms(perf_start),
                                _elapsed_ms(gateway_start),
                                upstream_bytes,
                            )
                        if not first_thinking_logged and sdk_data_type in {"response.reasoning_text.delta", "response.reasoning_summary_text.delta"}:
                            first_thinking_logged = True
                            perf_log.info(
                                "[PERF][agent_first_token] backend.first_thinking_delta total_ms={} gateway_wait_ms={} upstream_bytes_before_first_thinking={}",
                                _elapsed_ms(perf_start),
                                _elapsed_ms(gateway_start),
                                upstream_bytes,
                            )
                        persisted_events.append((event_name, data))
                        result = await event_processor.handle_runtime_event(
                            run_id=run_id,
                            user_id=user_id,
                            session_id=session_id,
                            event_name=event_name,
                            data=data,
                            complete_immediately=False,
                        )
                        if result.terminal:
                            await _settle_session_after_terminal(
                                session_id=session_id,
                                user_id=user_id,
                                persisted_status=result.persisted_status,
                                error=data if event_name == "runtime.error" else None,
                            )
                            if event_name == "runtime.error":
                                await _persist_run_output_short_tx(
                                    run_id=run_id,
                                    session_id=session_id,
                                    user_id=user_id,
                                    events=persisted_events,
                                    error=data,
                                )
                            return

                # Flush any final event if upstream did not end with a blank line.
                events, stream_buffer = _parse_sse_events(stream_buffer + "\n\n")
                for event_name, data in events:
                    persisted_events.append((event_name, data))
                    result = await event_processor.handle_runtime_event(
                        run_id=run_id,
                        user_id=user_id,
                        session_id=session_id,
                        event_name=event_name,
                        data=data,
                        complete_immediately=False,
                    )
                    if result.terminal:
                        await _settle_session_after_terminal(
                            session_id=session_id,
                            user_id=user_id,
                            persisted_status=result.persisted_status,
                            error=data if event_name == "runtime.error" else None,
                        )
                        if event_name == "runtime.error":
                            await _persist_run_output_short_tx(
                                run_id=run_id,
                                session_id=session_id,
                                user_id=user_id,
                                events=persisted_events,
                                error=data,
                            )
                        return

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
                final_output = "".join(
                    str(block.get("text") or block.get("content") or "")
                    for block in assistant_content.get("blocks", [])
                    if isinstance(block, dict) and block.get("type") == "text"
                )
                await _persist_run_output_short_tx(
                    run_id=run_id,
                    session_id=session_id,
                    user_id=user_id,
                    events=persisted_events,
                    complete_usage=assistant_content.get("usage") or {},
                    final_output=final_output or None,
                )
                await event_processor.complete_run(
                    run_id=run_id,
                    user_id=user_id,
                    session_id=session_id,
                    usage=assistant_content.get("usage"),
                    final_output=final_output or None,
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
                await _persist_run_output_short_tx(
                    run_id=run_id,
                    session_id=session_id,
                    user_id=user_id,
                    events=persisted_events,
                    error=error_payload,
                )
                await agent_run_event_bus.publish(run_id, "error", _error_payload(exc.code, exc.message, exc.retryable), terminal=True)
    except SessionBusyError:
        await _mark_run_status_short_tx(run_id, user_id, "error", error={"code": "SESSION_BUSY", "message": "当前会话正在执行，请稍后再试"})
        await agent_run_event_bus.publish(run_id, "error", _error_payload("SESSION_BUSY", "当前会话正在执行，请稍后再试", True), terminal=True)
    except Exception:
        perf_log.exception("backend background run failed")
        error = _unexpected_run_error()
        current = await _get_session_state_short_tx(session_id, user_id)
        if current:
            await _mark_error_short_tx(session_id, user_id, current["version"], error)
        await _mark_run_status_short_tx(run_id, user_id, "error", error=error)
        await _persist_run_output_short_tx(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            events=[],
            error=error,
        )
        await agent_run_event_bus.publish(
            run_id,
            "error",
            _error_payload(error["code"], error["message"], error["retryable"]),
            terminal=True,
        )


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
