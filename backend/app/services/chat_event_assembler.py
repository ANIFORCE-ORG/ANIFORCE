"""Assemble visible Agent messages from runtime SSE events."""

from __future__ import annotations

from typing import Any


class ChatEventAssembler:
    """Convert runtime events into frontend-facing content_json blocks."""

    def __init__(self, save_full_thinking: bool = True) -> None:
        self.save_full_thinking = save_full_thinking

    def user_message(self, text: str) -> dict:
        return {
            "blocks": [{"type": "text", "content": text, "text": text}],
            "usage": None,
        }

    def error_message(self, code: str, message: str) -> dict:
        return {
            "blocks": [{"type": "error", "code": code, "message": message}],
            "usage": None,
        }

    def assemble_assistant_message(self, events: list[tuple[str, dict[str, Any]]]) -> dict:
        text_parts: list[str] = []
        thinking_parts: list[str] = []
        tool_blocks: list[dict] = []
        usage = None
        tool_by_id: dict[str, dict] = {}

        for event_name, data in events:
            if event_name == "message.updated":
                delta = str(data.get("delta") or data.get("content") or "")
                if delta:
                    text_parts.append(delta)
            elif event_name == "thinking.updated":
                delta = str(data.get("delta") or data.get("content") or "")
                if delta:
                    thinking_parts.append(delta)
            elif event_name == "tool_call.started":
                call_id = str(data.get("tool_call_id") or data.get("id") or f"tool_{len(tool_blocks) + 1}")
                block = {
                    "type": "tool_call",
                    "toolCallId": call_id,
                    "tool": data.get("tool_name") or data.get("tool") or data.get("name"),
                    "args": data.get("arguments") or data.get("args") or {},
                    "status": "running",
                }
                tool_by_id[call_id] = block
                tool_blocks.append(block)
            elif event_name in {"tool_call.completed", "tool_call.error"}:
                call_id = str(data.get("tool_call_id") or data.get("id") or "")
                block = tool_by_id.get(call_id)
                if not block:
                    block = {
                        "type": "tool_call",
                        "toolCallId": call_id or f"tool_{len(tool_blocks) + 1}",
                        "tool": data.get("tool_name") or data.get("tool") or data.get("name"),
                        "args": data.get("arguments") or data.get("args") or {},
                    }
                    tool_blocks.append(block)
                block["status"] = "error" if event_name.endswith(".error") else "completed"
                block["result"] = data.get("result") or data.get("error")
            elif event_name in {"runtime.completed", "message.completed"}:
                usage = data.get("usage") or usage

        blocks: list[dict] = []
        thinking = "".join(thinking_parts).strip()
        if thinking:
            block = {"type": "thinking", "summary": self._summarize(thinking), "collapsed": True}
            if self.save_full_thinking:
                block["content"] = thinking
                block["thinking"] = thinking
            blocks.append(block)
        blocks.extend(tool_blocks)
        text = "".join(text_parts)
        if text:
            blocks.append({"type": "text", "content": text, "text": text})

        return {"blocks": blocks, "usage": usage}

    def _summarize(self, content: str) -> str:
        cleaned = " ".join(content.split())
        return cleaned[:120] + ("..." if len(cleaned) > 120 else "")
