"""Claude SDK → ANIFORCE 业务事件适配器"""

import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Optional

import aiosqlite
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from app.models.event import AgentEvent
from app.models.output import OutputStatus, OutputType, TaskOutput
from app.repositories.event_repo import EventRepository
from app.repositories.output_repo import OutputRepository

logger = logging.getLogger(__name__)

EVT_SDK_RAW = "sdk_raw_event"
EVT_TASK_CREATED = "TaskCreated"
EVT_TASK_PROGRESS_UPDATED = "TaskProgressUpdated"
EVT_TASK_OUTPUT_DELTA = "TaskOutputDelta"
EVT_TASK_OUTPUT_PRODUCED = "TaskOutputProduced"
EVT_TASK_STATUS_CHANGED = "TaskStatusChanged"
EVT_TASK_COMPLETED = "TaskCompleted"


class BusinessEventAdapter:
    """Claude SDK 消息流到 ANIFORCE 通用业务事件流的适配器"""

    @staticmethod
    async def stream_business_events(
        *,
        task_id: str,
        user_id: str,
        task_type: str,
        prompt: str,
        session_id: str,
        sdk_messages: AsyncGenerator[Any, None],
        db: aiosqlite.Connection,
        include_raw_events: bool = False,
    ) -> AsyncGenerator[str, None]:
        """将 SDK 消息流转换为业务 SSE 事件，并写入事件/产物表"""
        sequence = 0
        started_at = time.monotonic()
        assistant_text_parts: list[str] = []
        streamed_chars = 0
        last_progress_phase: Optional[str] = None
        tool_names: dict[str, str] = {}
        runtime_meta: dict[str, Any] = {
            "model": None,
            "sessionId": session_id,
            "tools": [],
            "skills": [],
        }
        telemetry: dict[str, Any] = {
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "charPerSecond": None,
            "durationMs": None,
            "costUsd": None,
        }

        event_repo = EventRepository(db)
        output_repo = OutputRepository(db)

        def enrich(payload: dict[str, Any]) -> dict[str, Any]:
            enriched = dict(payload)
            enriched.setdefault("runtime", dict(runtime_meta))
            enriched.setdefault("telemetry", dict(telemetry))
            return enriched

        async def emit(event_type: str, payload: dict[str, Any], *, persist: bool = True) -> str:
            nonlocal sequence
            payload = enrich(payload)
            if persist:
                await event_repo.append(
                    AgentEvent(
                        event_id=f"event_{uuid.uuid4().hex[:16]}",
                        task_id=task_id,
                        event_type=event_type,
                        payload=payload,
                        sequence=sequence,
                    )
                )
                sequence += 1
            return BusinessEventAdapter._format_sse(event_type, payload)

        async def update_task_status(status: str, error: Optional[str] = None) -> None:
            await db.execute(
                """
                UPDATE tasks
                SET status = ?, error = COALESCE(?, error), updated_at = datetime('now')
                WHERE task_id = ? AND user_id = ?
                """,
                (status, json.dumps({"error": error}, ensure_ascii=False) if error else None, task_id, user_id),
            )
            await db.commit()

        yield await emit(
            EVT_TASK_CREATED,
            {
                "taskId": task_id,
                "taskType": task_type,
                "sessionId": session_id,
                "goal": prompt,
                "targets": {"type": "conversation", "ids": []},
                "userId": user_id,
            },
        )
        await update_task_status("running")
        yield await emit(
            EVT_TASK_STATUS_CHANGED,
            {"taskId": task_id, "status": "running"},
        )

        try:
            async for message in sdk_messages:
                logger.info(f"[Task {task_id}] SDK Message: {type(message).__name__}")

                if include_raw_events:
                    yield BusinessEventAdapter._format_sse(
                        EVT_SDK_RAW,
                        BusinessEventAdapter._serialize_sdk_message(message),
                    )

                phase = BusinessEventAdapter._infer_progress_phase(message)
                if phase and phase != last_progress_phase:
                    last_progress_phase = phase
                    yield await emit(
                        EVT_TASK_PROGRESS_UPDATED,
                        {
                            "taskId": task_id,
                            "progress": {
                                "phase": phase,
                                "currentStep": BusinessEventAdapter._phase_step(phase),
                                "totalSteps": 4,
                                "percentage": BusinessEventAdapter._phase_percentage(phase),
                                "message": phase,
                            },
                        },
                    )

                if isinstance(message, StreamEvent):
                    text_delta = BusinessEventAdapter._extract_stream_text_delta(message)
                    if text_delta:
                        assistant_text_parts.append(text_delta)
                        streamed_chars += len(text_delta)
                        elapsed = max(time.monotonic() - started_at, 0.001)
                        telemetry["charPerSecond"] = round(streamed_chars / elapsed, 2)
                        yield await emit(
                            EVT_TASK_OUTPUT_DELTA,
                            {
                                "taskId": task_id,
                                "outputType": "text",
                                "category": "assistant_response",
                                "delta": text_delta,
                            },
                            persist=False,
                        )
                    continue

                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock) and not assistant_text_parts:
                            assistant_text_parts.append(block.text)
                        elif isinstance(block, ToolUseBlock):
                            tool_names[block.id] = block.name
                            logger.info(f"[Task {task_id}] Tool Call: {block.name}({block.input})")
                            yield await emit(
                                EVT_TASK_PROGRESS_UPDATED,
                                {
                                    "taskId": task_id,
                                    "progress": {
                                        "phase": "工具调用",
                                        "currentStep": 2,
                                        "totalSteps": 4,
                                        "percentage": 50,
                                        "message": f"调用工具 {block.name}",
                                        "tool": {
                                            "id": block.id,
                                            "name": block.name,
                                            "input": block.input,
                                        },
                                    },
                                },
                            )
                    continue

                if isinstance(message, UserMessage):
                    for block in BusinessEventAdapter._iter_tool_results(message):
                        tool_name = tool_names.get(block.tool_use_id, block.tool_use_id)
                        result_preview = str(block.content)[:200] if block.content else "(empty)"
                        logger.info(f"[Task {task_id}] Tool Result: {tool_name} -> {result_preview}")
                        yield await emit(
                            EVT_TASK_PROGRESS_UPDATED,
                            {
                                "taskId": task_id,
                                "progress": {
                                    "phase": "工具结果",
                                    "currentStep": 3,
                                    "totalSteps": 4,
                                    "percentage": 75,
                                    "message": f"工具 {tool_name} 返回结果",
                                    "toolResult": {
                                        "toolUseId": block.tool_use_id,
                                        "toolName": tool_name,
                                        "isError": bool(block.is_error),
                                    },
                                },
                            },
                        )
                    continue

                if isinstance(message, SystemMessage):
                    logger.debug("SDK system message: subtype=%s", message.subtype)
                    if message.subtype == "init":
                        data = message.data or {}
                        runtime_meta["model"] = data.get("model") or runtime_meta["model"]
                        runtime_meta["tools"] = data.get("tools") or runtime_meta["tools"]
                        runtime_meta["skills"] = data.get("skills") or runtime_meta["skills"]
                        yield await emit(
                            EVT_TASK_PROGRESS_UPDATED,
                            {
                                "taskId": task_id,
                                "progress": {
                                    "phase": "运行环境",
                                    "currentStep": 1,
                                    "totalSteps": 4,
                                    "percentage": 15,
                                    "message": "Agent 运行环境已初始化",
                                },
                            },
                        )
                    continue

                if isinstance(message, ResultMessage):
                    telemetry.update(BusinessEventAdapter._extract_result_telemetry(message, streamed_chars, started_at))
                    final_text = message.result or "".join(assistant_text_parts).strip()
                    if final_text and not message.is_error:
                        output = TaskOutput(
                            output_id=f"output_{uuid.uuid4().hex[:16]}",
                            task_id=task_id,
                            output_type=OutputType.TEXT,
                            category="assistant_response",
                            content={
                                "text": final_text,
                                "source": "claude_sdk_result",
                                "sessionId": message.session_id,
                            },
                            confidence=None,
                            importance="medium",
                            actionable=False,
                            requires_review=False,
                            status=OutputStatus.VERIFIED,
                        )
                        await output_repo.create(output)
                        yield await emit(
                            EVT_TASK_OUTPUT_PRODUCED,
                            {"taskId": task_id, "output": output.to_dict()},
                        )

                    if message.is_error:
                        error_msg = BusinessEventAdapter._result_error_message(message)
                        await update_task_status("error", error_msg)
                        yield await emit(
                            EVT_TASK_STATUS_CHANGED,
                            {"taskId": task_id, "status": "failed", "reason": error_msg},
                        )
                        yield await emit(
                            EVT_TASK_COMPLETED,
                            {
                                "taskId": task_id,
                                "summary": {
                                    "outputsProduced": 0,
                                    "duration": message.duration_ms,
                                    "cost": message.total_cost_usd,
                                    "status": "failed",
                                    "error": error_msg,
                                },
                            },
                        )
                    else:
                        await update_task_status("completed")
                        yield await emit(
                            EVT_TASK_STATUS_CHANGED,
                            {"taskId": task_id, "status": "completed"},
                        )
                        yield await emit(
                            EVT_TASK_COMPLETED,
                            {
                                "taskId": task_id,
                                "summary": {
                                    "outputsProduced": 1 if final_text else 0,
                                    "duration": message.duration_ms,
                                    "cost": message.total_cost_usd,
                                    "status": "completed",
                                    "numTurns": message.num_turns,
                                },
                            },
                        )
                    return

            # 正常结束但没收到 ResultMessage
            await update_task_status("completed")
            yield await emit(
                EVT_TASK_STATUS_CHANGED,
                {"taskId": task_id, "status": "completed", "reason": "sdk_stream_ended"},
            )
            yield await emit(
                EVT_TASK_COMPLETED,
                {
                    "taskId": task_id,
                    "summary": {
                        "outputsProduced": 0,
                        "duration": None,
                        "cost": None,
                        "status": "completed",
                    },
                },
            )
        except Exception as exc:
            logger.error("Business event stream error: %s", exc, exc_info=True)
            await update_task_status("error", str(exc))
            yield await emit(
                EVT_TASK_STATUS_CHANGED,
                {"taskId": task_id, "status": "failed", "reason": str(exc)},
            )
            yield await emit(
                EVT_TASK_COMPLETED,
                {
                    "taskId": task_id,
                    "summary": {
                        "outputsProduced": 0,
                        "duration": None,
                        "cost": None,
                        "status": "failed",
                        "error": str(exc),
                    },
                },
            )

    @staticmethod
    def _format_sse(event_type: str, data: dict) -> str:
        """格式化 SSE"""
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

    @staticmethod
    def _infer_progress_phase(message: Any) -> Optional[str]:
        if isinstance(message, SystemMessage) and message.subtype == "init":
            return "初始化"
        if isinstance(message, AssistantMessage):
            if any(isinstance(block, ToolUseBlock) for block in message.content):
                return "工具调用"
            return "生成回复"
        if isinstance(message, UserMessage):
            return "工具结果"
        if isinstance(message, ResultMessage):
            return "完成"
        return None

    @staticmethod
    def _phase_step(phase: str) -> int:
        return {"初始化": 1, "工具调用": 2, "工具结果": 3, "生成回复": 3, "完成": 4}.get(phase, 1)

    @staticmethod
    def _phase_percentage(phase: str) -> int:
        return {"初始化": 10, "工具调用": 50, "工具结果": 75, "生成回复": 80, "完成": 100}.get(phase, 10)

    @staticmethod
    def _extract_stream_text_delta(message: StreamEvent) -> str:
        event = message.event
        if event.get("type") != "content_block_delta":
            return ""
        delta = event.get("delta", {})
        if delta.get("type") != "text_delta":
            return ""
        return delta.get("text", "")

    @staticmethod
    def _iter_tool_results(message: UserMessage) -> list[ToolResultBlock]:
        if not isinstance(message.content, list):
            return []
        return [block for block in message.content if isinstance(block, ToolResultBlock)]

    @staticmethod
    def _result_error_message(message: ResultMessage) -> str:
        if message.errors:
            return "; ".join(str(error) for error in message.errors)
        return message.result or message.subtype or "unknown_error"

    @staticmethod
    def _extract_result_telemetry(
        message: ResultMessage,
        streamed_chars: int,
        started_at: float,
    ) -> dict[str, Any]:
        usage = message.usage or {}
        input_tokens = usage.get("input_tokens") or usage.get("inputTokens")
        output_tokens = usage.get("output_tokens") or usage.get("outputTokens")
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens

        duration_ms = message.duration_ms
        elapsed = max(time.monotonic() - started_at, 0.001)
        return {
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "totalTokens": total_tokens,
            "charPerSecond": round(streamed_chars / elapsed, 2) if streamed_chars else None,
            "durationMs": duration_ms,
            "costUsd": message.total_cost_usd,
            "usage": usage,
            "numTurns": message.num_turns,
        }

    @staticmethod
    def _serialize_sdk_message(message: Any) -> dict:
        payload = {"messageType": type(message).__name__}
        for attr in (
            "subtype",
            "session_id",
            "message_id",
            "uuid",
            "stop_reason",
            "is_error",
            "num_turns",
            "duration_ms",
            "total_cost_usd",
            "result",
        ):
            if hasattr(message, attr):
                payload[attr] = getattr(message, attr)

        if isinstance(message, StreamEvent):
            payload["event"] = message.event
        elif isinstance(message, SystemMessage):
            payload["data"] = message.data
        elif isinstance(message, (AssistantMessage, UserMessage)):
            payload["content"] = [BusinessEventAdapter._serialize_block(block) for block in message.content]
        elif isinstance(message, ResultMessage):
            payload["usage"] = message.usage
            payload["errors"] = message.errors
        return payload

    @staticmethod
    def _serialize_block(block: Any) -> dict:
        if isinstance(block, TextBlock):
            return {"type": "text", "text": block.text}
        if isinstance(block, ToolUseBlock):
            return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
        if isinstance(block, ToolResultBlock):
            return {
                "type": "tool_result",
                "tool_use_id": block.tool_use_id,
                "content": block.content,
                "is_error": block.is_error,
            }
        return {"type": type(block).__name__, "repr": repr(block)}
