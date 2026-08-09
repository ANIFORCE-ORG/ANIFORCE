"""Parse Agent Runtime SSE data without performing IO or state changes."""

import json


def is_client_stream_event(event_name: str, data: dict) -> bool:
    if event_name == "raw_response_event":
        sdk_data = data.get("data") if isinstance(data, dict) else None
        data_type = sdk_data.get("type") if isinstance(sdk_data, dict) else None
        return data_type in {
            "response.output_text.delta",
            "response.reasoning_text.delta",
            "response.reasoning_summary_text.delta",
        }
    if event_name == "run_item_stream_event":
        return data.get("name") in {"tool_called", "tool_output", "reasoning_item_created"}
    return event_name == "agent_updated_stream_event"


def parse_sse_events(buffer: str) -> tuple[list[tuple[str, dict]], str]:
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
