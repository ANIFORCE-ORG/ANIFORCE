"""Runtime checkpoint API for SDK HITL approvals."""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.agent.runtime import AgentRuntime
from app.auth import get_current_user

router = APIRouter(prefix="/runtime/checkpoints", tags=["runtime-checkpoints"])


def get_runtime() -> AgentRuntime:
    from app.main import _runtime
    return _runtime


@router.post("/{checkpoint_id}/resume")
async def resume_checkpoint(
    checkpoint_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
    runtime: AgentRuntime = Depends(get_runtime),
):
    body = await request.json()
    decision = body.get("decision")
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail={"code": "INVALID_DECISION", "message": "decision must be approve or reject"})
    auth_token = str(body.get("auth_token") or "").removeprefix("Bearer ")
    rejection_message = body.get("rejection_message")
    always = bool(body.get("always", False))
    edited_arguments = body.get("edited_arguments")
    argument_diff = body.get("argument_diff")

    async def event_generator():
        try:
            async for event in runtime.resume_checkpoint(
                checkpoint_id=checkpoint_id,
                user_id=user["id"],
                decision=decision,
                auth_token=auth_token,
                rejection_message=rejection_message,
                always=always,
                edited_arguments=edited_arguments,
                argument_diff=argument_diff,
            ):
                sequence = int(event.get("sequence") or 0)
                event_name = str(event.get("event") or "sdk.event")
                payload = dict(event.get("data") or {})
                yield f"id: {sequence}\n"
                yield f"event: {event_name}\n"
                yield f"data: {json.dumps(payload, default=str, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield "event: runtime.error\n"
            yield f"data: {json.dumps({'checkpoint_id': checkpoint_id, 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Agent-Stream-Protocol": "sdk-native-envelope-v1",
        },
    )
