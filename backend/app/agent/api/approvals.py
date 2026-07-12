"""Agent approval HTTP and resume SSE transport routes."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.api.common import error_payload, sse_event, with_session
from app.agent.approval_commands import AgentApprovalCommands, ResolveApprovalCommand
from app.api.deps import get_current_user
from app.config.database import get_db, get_session_maker
from app.repositories.factory import get_campaign_repo, get_material_repo, get_project_repo
from app.repositories.impl.sqlite_agent_approval_repo import SqliteAgentApprovalRepository
from app.repositories.impl.sqlite_agent_run_event_repo import SqliteAgentRunEventRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository
from app.services.agent_approval_service import AgentApprovalError
from app.services.agent_run_service import AgentRunError, AgentRunService
from app.services.business_context_builder import BusinessContextBuilder
from app.services.redis_run_event_stream import RedisRunEventStream

router = APIRouter()


async def get_run(run_id: str, user_id: str) -> dict:
    async def operation(session: AsyncSession) -> dict:
        return await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, user_id)
    return await with_session(operation)


async def get_state(session_id: str, user_id: str) -> dict | None:
    async def operation(session: AsyncSession) -> dict | None:
        return await SqliteSessionStateRepository(session).get(session_id, user_id)
    return await with_session(operation)


async def build_context(state: dict, user_id: str) -> str:
    async def operation(session: AsyncSession) -> str:
        return await BusinessContextBuilder(
            project_repo=get_project_repo(session),
            campaign_repo=get_campaign_repo(session),
            material_repo=get_material_repo(session),
        ).build(state, user_id)
    return await with_session(operation)


async def list_events(run_id: str, user_id: str, after_sequence: int) -> tuple[dict, list[dict]]:
    async def operation(session: AsyncSession) -> tuple[dict, list[dict]]:
        run = await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, user_id)
        events = await SqliteAgentRunEventRepository(session).list_after(run_id, after_sequence)
        return run, events
    return await with_session(operation)


@router.get("/runs/{run_id}/approvals")
async def list_run_approvals(
    run_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, current_user["id"])
    except AgentRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=error_payload(exc.code, exc.message, exc.retryable)) from exc
    return await SqliteAgentApprovalRepository(session).list_for_run(run_id, current_user["id"])


@router.post("/runs/{run_id}/approvals/{checkpoint_id}")
async def resolve_run_approval(
    run_id: str,
    checkpoint_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    body = await request.json()
    decision = body.get("decision")
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail=error_payload("INVALID_DECISION", "decision must be approve or reject"))
    user_id = current_user["id"]
    run = await get_run(run_id, user_id)
    if run.get("checkpoint_ref") != checkpoint_id:
        raise HTTPException(status_code=409, detail=error_payload("CHECKPOINT_MISMATCH", "Checkpoint does not belong to run"))

    transient = RedisRunEventStream()
    resume_after = 0
    if transient.enabled:
        try:
            resume_after = await transient.latest_sequence(run_id)
        except Exception:
            logger.exception("Read Redis Agent event sequence failed before resume: run_id={}", run_id)
    latest_state = await get_state(run["session_id"], user_id)
    latest_context = await build_context(latest_state or {}, user_id)
    resume_payload = {
        "decision": decision,
        "rejection_message": body.get("rejection_message"),
        "always": bool(body.get("always", False)),
        "edited_arguments": body.get("edited_arguments"),
        "argument_diff": body.get("argument_diff"),
        "checkpoint_id": checkpoint_id,
        "context_override": {"business_context_summary": latest_context, "ui_snapshot": (latest_state or {}).get("ui_snapshot") or {}, "session_state": latest_state or {}},
    }
    try:
        await AgentApprovalCommands(get_session_maker()).resolve(
            ResolveApprovalCommand(
                run_id=run_id,
                checkpoint_ref=checkpoint_id,
                user_id=user_id,
                decision=decision,
                edited_arguments=body.get("edited_arguments"),
                argument_diff=body.get("argument_diff"),
                rejection_message=body.get("rejection_message"),
                resume_payload=resume_payload,
            )
        )
    except AgentApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=error_payload(exc.code, exc.message, False)) from exc

    async def generator():
        if transient.enabled and resume_after > 0:
            try:
                async for event in transient.subscribe(run_id, resume_after):
                    yield sse_event(event.event, event.data, event.sequence)
                    if event.event in {"runtime.completed", "runtime.error", "runtime.aborted", "runtime.requires_action"}:
                        return
                return
            except Exception:
                logger.exception("Redis Agent resume subscription failed: run_id={}", run_id)
            finally:
                await transient.close()
        sequence = int(run.get("last_event_sequence") or 0)
        names = {"run.resuming": "runtime.started", "run.completed": "runtime.completed", "run.error": "runtime.error", "run.cancelled": "runtime.aborted"}
        while True:
            current, events = await list_events(run_id, user_id, sequence)
            for event in events:
                sequence = event["sequence"]
                yield sse_event(names.get(event["event_type"], event["event_type"]), event["payload"], sequence)
            if current["status"] in {"completed", "error", "cancelled", "requires_action"}:
                return
            await asyncio.sleep(0.2)

    return StreamingResponse(generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})
