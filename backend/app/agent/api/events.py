"""Agent Run event replay and SSE transport routes."""

import asyncio

from loguru import logger
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.api.common import error_payload, sse_event, with_session
from app.api.deps import get_current_user
from app.config.database import get_db
from app.repositories.impl.sqlite_agent_run_event_repo import SqliteAgentRunEventRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.agent.services.run import AgentRunError, AgentRunService
from app.agent.event_stream import RedisRunEventStream

router = APIRouter()


async def get_run(run_id: str, user_id: str) -> dict:
    async def operation(session: AsyncSession) -> dict:
        return await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, user_id)
    return await with_session(operation)


async def list_events(run_id: str, user_id: str, after_sequence: int) -> tuple[dict, list[dict]]:
    async def operation(session: AsyncSession) -> tuple[dict, list[dict]]:
        run = await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, user_id)
        events = await SqliteAgentRunEventRepository(session).list_after(run_id, after_sequence)
        return run, events
    return await with_session(operation)


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
        raise HTTPException(status_code=exc.status_code, detail=error_payload(exc.code, exc.message, exc.retryable)) from exc
    events = await SqliteAgentRunEventRepository(session).list_after(run_id, max(0, after_sequence), min(max(1, limit), 500))
    return {"run_id": run_id, "events": events, "last_persisted_sequence": run["last_event_sequence"], "terminal": run["status"] in {"completed", "error", "cancelled"}}


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    after_sequence: int = 0,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    await get_run(run_id, user_id)
    transient_stream = RedisRunEventStream()

    async def persisted_generator():
        sequence = max(0, after_sequence)
        while True:
            try:
                run, events = await list_events(run_id, user_id, sequence)
            except AgentRunError:
                yield sse_event("error", error_payload("RUN_NOT_FOUND", "Run not found", False))
                return
            names = {"run.started": "runtime.started", "run.resuming": "runtime.started", "run.requires_action": "runtime.requires_action", "run.completed": "runtime.completed", "run.error": "runtime.error", "run.cancelled": "runtime.aborted"}
            for event in events:
                sequence = event["sequence"]
                yield sse_event(names.get(event["event_type"], event["event_type"]), event["payload"], sequence)
            if run["status"] in {"completed", "error", "cancelled", "requires_action"}:
                return
            await asyncio.sleep(0.2)

    async def redis_generator():
        try:
            async for event in transient_stream.subscribe(run_id, max(0, after_sequence)):
                yield sse_event(event.event, event.data, event.sequence)
                if event.event in {"runtime.completed", "runtime.error", "runtime.aborted", "runtime.requires_action"}:
                    return
        except Exception:
            logger.exception("Redis Agent event subscription failed: run_id={}", run_id)
            async for chunk in persisted_generator():
                yield chunk
        finally:
            await transient_stream.close()

    return StreamingResponse(
        redis_generator() if transient_stream.enabled else persisted_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
