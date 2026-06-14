"""
AG-UI Event Adapter

将 ANIFORCE AgentRuntime 事件流适配为 AG-UI 标准协议。
对接 CopilotKit @ag-ui/client 的 HttpAgent。

文件职责:
  - agui_events.py    AG-UI 标准事件类型定义
  - agui_registry.py  可扩展的工具注册中心
  - agui_adapter.py   本文件：适配器 + SSE generator
  - copilotkit.py     FastAPI 路由端点
"""

import json
import uuid
from typing import Optional, AsyncIterator
from dataclasses import dataclass, field

from loguru import logger

from .agui_events import (
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    StateSnapshotEvent,
    ActivitySnapshotEvent,
)
from .agui_registry import ToolRegistry, ToolPresentation, create_default_tool_registry


# ============================================================
# AG-UI Request Model (HttpAgent 发送的格式)
# ============================================================

@dataclass
class AgUiRequest:
    """HttpAgent POST 请求体"""
    thread_id: str = ""
    run_id: Optional[str] = None
    messages: list = field(default_factory=list)
    state: dict = field(default_factory=dict)
    tools: list = field(default_factory=list)
    context: list = field(default_factory=list)
    forwarded_props: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "AgUiRequest":
        return cls(
            thread_id=str(data.get("threadId", data.get("thread_id", ""))),
            run_id=data.get("runId") or data.get("run_id"),
            messages=data.get("messages", []),
            state=data.get("state", {}),
            tools=data.get("tools", []),
            context=data.get("context", []),
            forwarded_props=data.get("forwardedProps", data.get("forwarded_props", {})),
        )


# ============================================================
# Adapter: ANIFORCE → AG-UI
# ============================================================

class AgUiEventAdapter:
    """
    ANIFORCE AgentTaskEvent → AG-UI 标准事件适配器。

    职责:
      路由事件 (runtime → RunStarted, message → TextMessage, tool_call → Activity + ToolCall)
      通过 ToolRegistry 获取工具展示与结果提取逻辑
      维护 state 快照，工具完成时自动写入 StateSnapshot

    不负责:
      工具展示文案 (由 ToolRegistry 提供)
      业务数据提取规则 (由 ToolRegistry 提供)
      HTTP/SSE 传输 (由 agui_sse_generator 负责)
    """

    def __init__(
        self,
        thread_id: str,
        run_id: str,
        tool_registry: ToolRegistry = None,
    ):
        self.thread_id = thread_id
        self.run_id = run_id
        self.state: dict = {}
        self._current_message_id: Optional[str] = None
        self._pending_tool_calls: dict = {}  # tool_call_id → { name, activity_msg_id }
        self._tool_registry = tool_registry or create_default_tool_registry()

    def adapt(self, event: "AgentTaskEvent") -> list:
        """将一个 ANIFORCE 事件转换为一组 AG-UI 事件"""
        event_type = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
        payload = event.payload if hasattr(event, 'payload') and event.payload else {}

        # === Runtime ===
        if event_type == "runtime.started":
            return [RunStartedEvent(thread_id=self.thread_id, run_id=self.run_id)]

        if event_type == "runtime.completed":
            return [
                StateSnapshotEvent(snapshot={**self.state, "status": "completed"}),
                RunFinishedEvent(thread_id=self.thread_id, run_id=self.run_id),
            ]

        if event_type == "runtime.error":
            return [RunErrorEvent(
                message=str(payload.get("message", "Agent runtime error")),
                code=payload.get("code"),
            )]

        # === Message ===
        if event_type == "message.started":
            self._current_message_id = payload.get("id") or f"msg_{uuid.uuid4().hex[:12]}"
            return [TextMessageStartEvent(message_id=self._current_message_id)]

        if event_type == "message.updated":
            delta = payload.get("delta", "")
            if not delta:
                return []
            mid = self._current_message_id or f"msg_{uuid.uuid4().hex[:12]}"
            return [TextMessageContentEvent(message_id=mid, delta=delta)]

        if event_type == "message.completed":
            mid = self._current_message_id or f"msg_{uuid.uuid4().hex[:12]}"
            self._current_message_id = None
            return [TextMessageEndEvent(message_id=mid)]

        # === Tool Call Started ===
        if event_type == "tool_call.started":
            return self._on_tool_started(payload)

        # === Tool Call Completed ===
        if event_type in ("tool_call.completed", "tool_call.error"):
            return self._on_tool_completed(payload, is_error=(event_type == "tool_call.error"))

        # === CUSTOM (Plan) ===
        if event_type == "CUSTOM":
            return self._on_custom_event(payload)

        return []

    # --------------------------------------------------------
    # Internal handlers
    # --------------------------------------------------------

    def _on_tool_started(self, payload: dict) -> list:
        tool_call_id = payload.get("tool_call_id") or f"tc_{uuid.uuid4().hex[:8]}"
        tool_name = str(payload.get("tool_name", "unknown"))
        args = payload.get("arguments", {})

        presentation = self._tool_registry.get(tool_name)
        title = presentation.title("running") if presentation else f"{tool_name} (running)"
        activity_msg_id = f"activity_{tool_call_id}"

        self._pending_tool_calls[tool_call_id] = {
            "name": tool_name,
            "activity_msg_id": activity_msg_id,
        }

        return [
            ToolCallStartEvent(
                tool_call_id=tool_call_id,
                tool_call_name=tool_name,
                parent_message_id=self._current_message_id,
            ),
            ActivitySnapshotEvent(
                message_id=activity_msg_id,
                activity_type="TOOL_CALL",
                content={
                    "toolName": tool_name,
                    "status": "running",
                    "title": title,
                    "arguments": args,
                },
            ),
        ]

    def _on_tool_completed(self, payload: dict, is_error: bool) -> list:
        tool_call_id = payload.get("tool_call_id") or self._find_pending_tool_id()
        tool_name = str(payload.get("tool_name", "unknown"))
        result = payload.get("result")

        if not tool_call_id:
            return []

        pending = self._pending_tool_calls.pop(tool_call_id, {})
        activity_msg_id = pending.get("activity_msg_id", f"activity_{tool_call_id}")

        presentation = self._tool_registry.get(tool_name)
        status = "error" if is_error else "completed"
        title = presentation.title(status) if presentation else f"{tool_name} ({status})"

        events = []

        # ToolCallEnd + Result
        events.append(ToolCallEndEvent(tool_call_id=tool_call_id))
        if result is not None:
            result_str = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
            events.append(ToolCallResultEvent(
                message_id=f"tool_result_{tool_call_id}",
                tool_call_id=tool_call_id,
                content=result_str,
            ))

        # Activity: 更新为完成状态
        activity_content = {"toolName": tool_name, "status": status, "title": title}
        if result and isinstance(result, str):
            activity_content["resultSummary"] = result[:200]
        events.append(ActivitySnapshotEvent(
            message_id=activity_msg_id,
            activity_type="TOOL_CALL",
            content=activity_content,
        ))

        # StateSnapshot: 如果注册了 extract_result，自动提取业务数据
        if not is_error and presentation and presentation.extract_result:
            extracted = presentation.extract_result(result)
            if extracted is not None:
                self.state.update(extracted)
                self.state["lastAction"] = tool_name
                events.append(StateSnapshotEvent(snapshot=dict(self.state)))

        return events

    def _on_custom_event(self, payload: dict) -> list:
        subtype = payload.get("subtype", "")
        if subtype == "plan.created":
            todos = payload.get("todos", [])
            return [
                ActivitySnapshotEvent(
                    message_id=f"plan_{uuid.uuid4().hex[:8]}",
                    activity_type="PLAN",
                    content={"todos": todos, "status": "created"},
                ),
                StateSnapshotEvent(snapshot={**self.state, "plan": {"todos": todos}}),
            ]
        return []

    def _find_pending_tool_id(self) -> Optional[str]:
        if self._pending_tool_calls:
            return list(self._pending_tool_calls.keys())[-1]
        return None


# ============================================================
# SSE Generator
# ============================================================

async def agui_sse_generator(
    aniforce_events: AsyncIterator,
    thread_id: str,
    run_id: Optional[str] = None,
    tool_registry: ToolRegistry = None,
) -> AsyncIterator[str]:
    """
    消费 ANIFORCE 事件流，产出 AG-UI 标准 SSE 流。

    Args:
        aniforce_events: ANIFORCE AgentRuntime 事件流
        thread_id:       会话 ID
        run_id:          本轮执行 ID（可选，自动生成）
        tool_registry:   工具注册表（可选，默认使用内置注册表）
    """
    run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
    adapter = AgUiEventAdapter(
        thread_id=thread_id,
        run_id=run_id,
        tool_registry=tool_registry or create_default_tool_registry(),
    )

    try:
        async for event in aniforce_events:
            for agui_event in adapter.adapt(event):
                yield agui_event.to_sse() + "\n"
        # 事件流结束后，发送最终 state
        if adapter.state:
            yield StateSnapshotEvent(snapshot=adapter.state).to_sse() + "\n"
    except Exception as e:
        logger.exception(f"AG-UI adapter error: {e}")
        yield RunErrorEvent(message=str(e)).to_sse() + "\n"
