from app.api.runtime_sessions import _items_to_messages


def test_history_parser_pairs_tool_calls_and_outputs() -> None:
    messages = _items_to_messages([
        {"role": "user", "content": "list projects"},
        {
            "type": "function_call",
            "call_id": "call_1",
            "name": "list_projects",
            "arguments": '{"limit": 5}',
        },
        {"type": "function_call_output", "call_id": "call_1", "output": '{"projects": []}'},
        {"role": "assistant", "content": [{"type": "output_text", "text": "No projects."}]},
    ])

    assert messages[0]["role"] == "user"
    assistant = messages[1]
    tool, text = assistant["content_json"]["blocks"]
    assert tool == {
        "type": "tool_call",
        "toolCallId": "call_1",
        "tool": "list_projects",
        "args": {"limit": 5},
        "status": "completed",
        "result": '{"projects": []}',
    }
    assert text["content"] == "No projects."


def test_history_parser_merges_reasoning_before_text() -> None:
    messages = _items_to_messages([
        {"type": "reasoning", "summary": [{"text": "first"}, {"text": "second"}]},
        {"role": "assistant", "content": [{"type": "output_text", "text": "answer"}]},
    ])

    blocks = messages[0]["content_json"]["blocks"]
    assert [block["type"] for block in blocks] == ["thinking", "text"]
    assert blocks[0]["content"] == "first\n\nsecond"
