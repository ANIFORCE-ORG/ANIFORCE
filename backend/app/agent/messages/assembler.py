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

    def assemble_assistant_message(
        self,
        events: list[tuple[str, dict[str, Any]]],
        tool_facts_by_id: dict[str, dict[str, Any]] | None = None,
    ) -> dict:
        blocks: list[dict[str, Any]] = []
        usage = None
        tool_by_id: dict[str, dict[str, Any]] = {}

        def append_delta(block_type: str, field: str, delta: str) -> None:
            if blocks and blocks[-1].get("type") == block_type:
                block = blocks[-1]
            else:
                block = {"type": block_type, field: ""}
                blocks.append(block)
            block[field] = str(block.get(field) or "") + delta

        def next_tool_id() -> str:
            count = sum(1 for block in blocks if block.get("type") == "tool_call")
            return f"tool_{count + 1}"

        for event_name, data in events:
            if event_name in {"raw_response_event", "run_item_stream_event", "agent_updated_stream_event"}:
                sdk_type = str(data.get("type") or "")
                sdk_data = self._as_dict(data.get("data"))
                sdk_item = self._as_dict(data.get("item"))

                if sdk_type == "raw_response_event":
                    data_type = str(sdk_data.get("type") or "")
                    delta = str(sdk_data.get("delta") or "")
                    if data_type == "response.output_text.delta" and delta:
                        append_delta("text", "text", delta)
                    elif data_type in {"response.reasoning_text.delta", "response.reasoning_summary_text.delta"} and delta:
                        append_delta("thinking", "thinking", delta)

                elif sdk_type == "run_item_stream_event":
                    name = str(data.get("name") or "")
                    if name == "tool_called":
                        call_id, tool_name, args = self._tool_call_info(sdk_item)
                        call_id = call_id or next_tool_id()
                        block = {
                            "type": "tool_call",
                            "toolCallId": call_id,
                            "tool": tool_name,
                            "args": args,
                            "status": "running",
                        }
                        tool_by_id[call_id] = block
                        blocks.append(block)
                    elif name == "tool_output":
                        call_id, result = self._tool_output_info(sdk_item)
                        block = tool_by_id.get(call_id or "")
                        if not block:
                            fact = (tool_facts_by_id or {}).get(call_id or "", {})
                            block = {
                                "type": "tool_call",
                                "toolCallId": call_id or next_tool_id(),
                                "tool": str(fact.get("tool_name") or "unknown"),
                                "args": fact.get("arguments") if isinstance(fact.get("arguments"), dict) else {},
                            }
                            blocks.append(block)
                        fact = (tool_facts_by_id or {}).get(call_id or "", {})
                        block["status"] = str(fact.get("status") or "completed")
                        block["result"] = fact.get("result") if fact.get("result") is not None else result
                    elif name == "reasoning_item_created":
                        # Reasoning text is already accumulated from raw deltas.
                        pass
            elif event_name == "runtime.completed":
                usage = data.get("usage") or usage

        normalized_blocks: list[dict[str, Any]] = []
        for block in blocks:
            if block.get("type") == "thinking":
                thinking = str(block.get("thinking") or "").strip()
                if not thinking:
                    continue
                normalized = {
                    "type": "thinking",
                    "summary": self._summarize(thinking),
                    "collapsed": True,
                }
                if self.save_full_thinking:
                    normalized["content"] = thinking
                    normalized["thinking"] = thinking
                normalized_blocks.append(normalized)
                continue
            if block.get("type") == "text":
                text = str(block.get("text") or "")
                if text:
                    normalized_blocks.append({"type": "text", "content": text, "text": text})
                continue
            normalized_blocks.append(block)

        return {"blocks": normalized_blocks, "usage": usage}

    def _summarize(self, content: str) -> str:
        cleaned = " ".join(content.split())
        return cleaned[:120] + ("..." if len(cleaned) > 120 else "")

    def _as_dict(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _tool_call_info(self, item: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        raw = self._as_dict(item.get("raw_item"))
        call_id = str(item.get("call_id") or raw.get("call_id") or raw.get("id") or "")
        tool_name = str(item.get("tool_name") or raw.get("name") or item.get("name") or "tool")
        args = raw.get("arguments") or item.get("arguments") or {}
        if isinstance(args, str):
            import json
            try:
                args = json.loads(args) if args.strip() else {}
            except Exception:
                args = {"raw": args}
        if not isinstance(args, dict):
            args = {}
        return call_id, tool_name, args

    def _tool_output_info(self, item: dict[str, Any]) -> tuple[str, Any]:
        raw = self._as_dict(item.get("raw_item"))
        call_id = str(item.get("call_id") or raw.get("call_id") or raw.get("id") or "")
        result = item.get("output")
        if result is None:
            result = raw.get("output") if "output" in raw else raw.get("content")
        return call_id, result

