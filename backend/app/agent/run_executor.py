"""Consume Agent Runtime events and persist run outcomes without HTTP dependencies."""

from __future__ import annotations

from datetime import datetime
from time import perf_counter

from loguru import logger

from app.agent.run_execution_store import AgentRunExecutionStore
from app.agent.runtime_event_protocol import is_client_stream_event, parse_sse_events
from app.agent.gateway import AgentGatewayError, AgentGatewayService
from app.agent.event_reducer import AgentRunEventProcessor
from app.agent.services.message_assembler import ChatEventAssembler
from app.agent.event_stream import RedisRunEventStream
from app.agent.services.side_effect import SideEffectService


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


def _error_payload(code: str, message: str, retryable: bool) -> dict:
    return {"error": {"code": code, "message": message, "retryable": retryable, "details": {}}}


def _unexpected_run_error() -> dict:
    return {
        "code": "RUN_FAILED",
        "message": "Agent run failed unexpectedly",
        "retryable": True,
        "at": datetime.utcnow().isoformat(),
    }


async def execute_agent_run(
    *,
    run_id: str,
    session_id: str,
    user_id: str,
    authorization: str | None,
    agent_payload: dict,
    changelog_start_index: int,
    gateway: AgentGatewayService,
    perf_start: float,
    lease_owner: str | None = None,
    resume_payload: dict | None = None,
    transient_stream: RedisRunEventStream | None = None,
    store: AgentRunExecutionStore,
) -> None:
    perf_log = logger.bind(run_id=run_id, session_id=session_id, user_id=user_id)

    async def publish_transient(event_name: str, data: dict) -> None:
        if transient_stream is not None:
            await transient_stream.publish(run_id, event_name, data)
    latest_state = await store.get_session_state(session_id, user_id)
    if latest_state is None:
        await publish_transient(
            "runtime.error",
            _error_payload("SESSION_NOT_FOUND", "Session State not found", False),
        )
        return

    first_agent_chunk_logged = False
    first_thinking_logged = False
    first_message_logged = False
    upstream_bytes = 0
    stream_buffer = ""
    event_processor = AgentRunEventProcessor()

    async def apply_terminal_event(event_name: str, data: dict) -> str | None:
        outcome = event_processor.reduce(event_name, data)
        if not outcome.terminal or outcome.transition == "completed":
            return None
        if outcome.transition == "requires_action":
            updated = await store.require_action(
                run_id=run_id,
                user_id=user_id,
                data=data,
                lease_owner=lease_owner,
            )
        elif outcome.transition == "cancelled":
            updated = await store.cancel(run_id, user_id, lease_owner=lease_owner)
        else:
            updated = await store.fail(
                run_id,
                user_id,
                outcome.error or {},
                lease_owner=lease_owner,
            )
        persisted_status = updated.get("status") if updated else None
        await store.settle_session(
            session_id=session_id,
            user_id=user_id,
            run_status=persisted_status,
            error=data if event_name == "runtime.error" else None,
        )
        await publish_transient(event_name, data)
        return persisted_status

    try:
            mark_running_start = perf_counter()
            await store.mark_session_running(session_id, user_id, latest_state["version"])
            mark_running_ms = _elapsed_ms(mark_running_start)
            perf_log.info(
                "[PERF][agent_first_token] backend.background_start total_ms={} mark_running_ms={}",
                _elapsed_ms(perf_start),
                mark_running_ms,
            )
            current_run = await store.mark_running(run_id, user_id)
            if current_run and current_run["status"] in {"completed", "error", "cancelled"}:
                current = await store.get_session_state(session_id, user_id)
                if current:
                    await store.settle_session(session_id=session_id, user_id=user_id, run_status="completed")
                return
            await publish_transient(
                "runtime.started",
                {"run_id": run_id, "session_id": session_id, "status": "running"},
            )

            gateway_start = perf_counter()
            persisted_events: list[tuple[str, dict]] = []
            try:
                stream = (
                    gateway.stream_checkpoint_resume(
                        authorization,
                        str((resume_payload or {}).get("checkpoint_id") or ""),
                        resume_payload or {},
                    )
                    if resume_payload is not None
                    else gateway.stream_run(authorization, agent_payload)
                )
                async for chunk in stream:
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
                    events, stream_buffer = parse_sse_events(stream_buffer)
                    for event_name, data in events:
                        if is_client_stream_event(event_name, data):
                            await publish_transient(event_name, data)
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
                        persisted_status = await apply_terminal_event(event_name, data)
                        if persisted_status:
                            if event_name == "runtime.error":
                                await store.persist_output(
                                    run_id=run_id,
                                    session_id=session_id,
                                    user_id=user_id,
                                    events=persisted_events,
                                    error=data,
                                )
                            return

                # Flush any final event if upstream did not end with a blank line.
                events, stream_buffer = parse_sse_events(stream_buffer + "\n\n")
                for event_name, data in events:
                    if is_client_stream_event(event_name, data):
                        await publish_transient(event_name, data)
                    persisted_events.append((event_name, data))
                    persisted_status = await apply_terminal_event(event_name, data)
                    if persisted_status:
                        if event_name == "runtime.error":
                            await store.persist_output(
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
                current = await store.get_session_state(session_id, user_id)
                if current:
                    new_changelog = (current.get("changelog") or [])[changelog_start_index:]
                    for side_effect in SideEffectService().from_changelog_entries(new_changelog):
                        await publish_transient("side_effect", side_effect.model_dump())
                    await store.settle_session(session_id=session_id, user_id=user_id, run_status="completed")

                latest_run = await store.get_run(run_id, user_id)
                if latest_run["status"] == "cancel_requested":
                    await store.cancel(run_id, user_id, lease_owner=lease_owner)
                    await store.settle_session(
                        session_id=session_id,
                        user_id=user_id,
                        run_status="cancelled",
                    )
                    await publish_transient(
                        "runtime.aborted",
                        {"run_id": run_id, "session_id": session_id, "status": "cancelled"},
                    )
                    return
                if latest_run["status"] == "cancelled":
                    await publish_transient(
                        "runtime.aborted",
                        {"run_id": run_id, "session_id": session_id, "status": "cancelled"},
                    )
                    return

                assistant_content = ChatEventAssembler().assemble_assistant_message(persisted_events)
                final_output = "".join(
                    str(block.get("text") or block.get("content") or "")
                    for block in assistant_content.get("blocks", [])
                    if isinstance(block, dict) and block.get("type") == "text"
                )
                completion = await store.persist_output(
                    run_id=run_id,
                    session_id=session_id,
                    user_id=user_id,
                    events=persisted_events,
                    complete_usage=assistant_content.get("usage") or {},
                    final_output=final_output or None,
                    lease_owner=lease_owner,
                )
                if completion and completion.get("status") == "completed":
                    await store.settle_session(
                        session_id=session_id,
                        user_id=user_id,
                        run_status="completed",
                    )
                    await publish_transient(
                        "runtime.completed",
                        {
                            "run_id": run_id,
                            "session_id": session_id,
                            "status": "completed",
                            "usage": assistant_content.get("usage") or {},
                            "final_output": final_output or "",
                        },
                    )
            except AgentGatewayError as exc:
                current = await store.get_session_state(session_id, user_id)
                if current:
                    await store.settle_session(session_id=session_id, user_id=user_id, run_status="error", error={"code": exc.code, "message": exc.message, "retryable": exc.retryable, "at": datetime.utcnow().isoformat()},
                    )
                error_payload = {"code": exc.code, "message": exc.message, "retryable": exc.retryable, "at": datetime.utcnow().isoformat()}
                await store.fail(run_id, user_id, error_payload, lease_owner=lease_owner)
                await store.persist_output(
                    run_id=run_id,
                    session_id=session_id,
                    user_id=user_id,
                    events=persisted_events,
                    error=error_payload,
                )
                error_event = _error_payload(exc.code, exc.message, exc.retryable)
                await publish_transient("runtime.error", error_event)
    except Exception:
        perf_log.exception("backend background run failed")
        error = _unexpected_run_error()
        current = await store.get_session_state(session_id, user_id)
        if current:
            await store.settle_session(session_id=session_id, user_id=user_id, run_status="error", error=error)
        await store.fail(run_id, user_id, error, lease_owner=lease_owner)
        await store.persist_output(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            events=[],
            error=error,
        )
        error_event = _error_payload(error["code"], error["message"], error["retryable"])
        await publish_transient("runtime.error", error_event)
