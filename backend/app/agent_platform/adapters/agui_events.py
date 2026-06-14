"""
AG-UI Protocol Event Model

标准事件类型定义，与 @ag-ui/client 的 HttpAgent 完全对齐。

事件类型:
  Lifecycle:   RunStarted / RunFinished / RunError
  Text:        TextMessageStart / TextMessageContent / TextMessageEnd
  Tool:        ToolCallStart / ToolCallEnd / ToolCallResult
  State:       StateSnapshot / StateDelta
  Activity:    ActivitySnapshot / ActivityDelta
  Messages:    MessagesSnapshot
"""

import json
from typing import Optional


class AgUiEvent:
    """AG-UI 事件基类"""

    def to_sse(self) -> str:
        payload = json.dumps(self.to_dict(), ensure_ascii=False)
        return f"event: {self.event_type()}\ndata: {payload}\n"

    def event_type(self) -> str:
        raise NotImplementedError

    def to_dict(self) -> dict:
        raise NotImplementedError


# ============================================================
# Lifecycle
# ============================================================

class RunStartedEvent(AgUiEvent):
    def __init__(self, thread_id: str, run_id: str, parent_run_id: str = None, input_data: dict = None):
        self.thread_id = thread_id
        self.run_id = run_id
        self.parent_run_id = parent_run_id
        self.input = input_data

    def event_type(self) -> str:
        return "RunStarted"

    def to_dict(self) -> dict:
        result = {"threadId": self.thread_id, "runId": self.run_id}
        if self.parent_run_id:
            result["parentRunId"] = self.parent_run_id
        if self.input:
            result["input"] = self.input
        return result


class RunFinishedEvent(AgUiEvent):
    def __init__(self, thread_id: str, run_id: str, result: dict = None):
        self.thread_id = thread_id
        self.run_id = run_id
        self.result = result

    def event_type(self) -> str:
        return "RunFinished"

    def to_dict(self) -> dict:
        r = {"threadId": self.thread_id, "runId": self.run_id}
        if self.result:
            r["result"] = self.result
        return r


class RunErrorEvent(AgUiEvent):
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code

    def event_type(self) -> str:
        return "RunError"

    def to_dict(self) -> dict:
        r = {"message": self.message}
        if self.code:
            r["code"] = self.code
        return r


# ============================================================
# Text Message
# ============================================================

class TextMessageStartEvent(AgUiEvent):
    def __init__(self, message_id: str, role: str = "assistant"):
        self.message_id = message_id
        self.role = role

    def event_type(self) -> str:
        return "TextMessageStart"

    def to_dict(self) -> dict:
        return {"messageId": self.message_id, "role": self.role}


class TextMessageContentEvent(AgUiEvent):
    def __init__(self, message_id: str, delta: str):
        self.message_id = message_id
        self.delta = delta

    def event_type(self) -> str:
        return "TextMessageContent"

    def to_dict(self) -> dict:
        return {"messageId": self.message_id, "delta": self.delta}


class TextMessageEndEvent(AgUiEvent):
    def __init__(self, message_id: str):
        self.message_id = message_id

    def event_type(self) -> str:
        return "TextMessageEnd"

    def to_dict(self) -> dict:
        return {"messageId": self.message_id}


# ============================================================
# Tool Call
# ============================================================

class ToolCallStartEvent(AgUiEvent):
    def __init__(self, tool_call_id: str, tool_call_name: str, parent_message_id: str = None):
        self.tool_call_id = tool_call_id
        self.tool_call_name = tool_call_name
        self.parent_message_id = parent_message_id

    def event_type(self) -> str:
        return "ToolCallStart"

    def to_dict(self) -> dict:
        r = {"toolCallId": self.tool_call_id, "toolCallName": self.tool_call_name}
        if self.parent_message_id:
            r["parentMessageId"] = self.parent_message_id
        return r


class ToolCallEndEvent(AgUiEvent):
    def __init__(self, tool_call_id: str):
        self.tool_call_id = tool_call_id

    def event_type(self) -> str:
        return "ToolCallEnd"

    def to_dict(self) -> dict:
        return {"toolCallId": self.tool_call_id}


class ToolCallResultEvent(AgUiEvent):
    def __init__(self, message_id: str, tool_call_id: str, content: str):
        self.message_id = message_id
        self.tool_call_id = tool_call_id
        self.content = content

    def event_type(self) -> str:
        return "ToolCallResult"

    def to_dict(self) -> dict:
        return {
            "messageId": self.message_id,
            "toolCallId": self.tool_call_id,
            "content": self.content,
        }


# ============================================================
# State
# ============================================================

class StateSnapshotEvent(AgUiEvent):
    def __init__(self, snapshot: dict):
        self.snapshot = snapshot

    def event_type(self) -> str:
        return "StateSnapshot"

    def to_dict(self) -> dict:
        return {"snapshot": self.snapshot}


class StateDeltaEvent(AgUiEvent):
    def __init__(self, delta: list):
        self.delta = delta

    def event_type(self) -> str:
        return "StateDelta"

    def to_dict(self) -> dict:
        return {"delta": self.delta}


# ============================================================
# Activity
# ============================================================

class ActivitySnapshotEvent(AgUiEvent):
    def __init__(self, message_id: str, activity_type: str, content: dict, replace: bool = True):
        self.message_id = message_id
        self.activity_type = activity_type
        self.content = content
        self.replace = replace

    def event_type(self) -> str:
        return "ActivitySnapshot"

    def to_dict(self) -> dict:
        return {
            "messageId": self.message_id,
            "activityType": self.activity_type,
            "content": self.content,
            "replace": self.replace,
        }


class ActivityDeltaEvent(AgUiEvent):
    def __init__(self, message_id: str, activity_type: str, patch: list):
        self.message_id = message_id
        self.activity_type = activity_type
        self.patch = patch

    def event_type(self) -> str:
        return "ActivityDelta"

    def to_dict(self) -> dict:
        return {
            "messageId": self.message_id,
            "activityType": self.activity_type,
            "patch": self.patch,
        }


# ============================================================
# Messages
# ============================================================

class MessagesSnapshotEvent(AgUiEvent):
    def __init__(self, messages: list):
        self.messages = messages

    def event_type(self) -> str:
        return "MessagesSnapshot"

    def to_dict(self) -> dict:
        return {"messages": self.messages}
