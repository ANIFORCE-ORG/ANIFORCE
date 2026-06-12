from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    SQLiteSession,
    function_tool,
    handoff,
    set_tracing_disabled,
    trace,
)
from agents.tracing.processor_interface import TracingProcessor
from agents.tracing import add_trace_processor
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = PROJECT_ROOT / "backend"
OUTPUT_DIR = PROJECT_ROOT / "drafts" / "260611" / "sdk_capability_probes" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(BACKEND_DIR / ".env")

MODEL_NAME = os.getenv("OPENAI_AGENTS_MODEL", "gpt-4.1-mini")
BASE_URL = os.getenv("OPENAI_BASE_URL")


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump())
    if hasattr(value, "__dict__"):
        return {k: jsonable(v) for k, v in vars(value).items() if not k.startswith("_")}
    return repr(value)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in rows), encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, default=str, indent=2), encoding="utf-8")


def build_model() -> str | OpenAIChatCompletionsModel:
    if BASE_URL:
        return OpenAIChatCompletionsModel(
            model=MODEL_NAME,
            openai_client=AsyncOpenAI(base_url=BASE_URL, api_key=os.getenv("OPENAI_API_KEY")),
            strict_feature_validation=False,
        )
    return MODEL_NAME


def summarize_result(result: Any) -> dict[str, Any]:
    usage = {"input": 0, "output": 0, "total": 0}
    for response in getattr(result, "raw_responses", []) or []:
        raw_usage = getattr(response, "usage", None)
        if raw_usage is None:
            continue
        usage["input"] += int(getattr(raw_usage, "input_tokens", 0) or 0)
        usage["output"] += int(getattr(raw_usage, "output_tokens", 0) or 0)
        usage["total"] += int(getattr(raw_usage, "total_tokens", 0) or 0)
    return {
        "final_output": getattr(result, "final_output", None),
        "last_agent": getattr(getattr(result, "last_agent", None), "name", None),
        "new_items": jsonable(getattr(result, "new_items", [])),
        "raw_responses": jsonable(getattr(result, "raw_responses", [])),
        "usage_summary": usage,
        "to_input_list": jsonable(result.to_input_list()) if hasattr(result, "to_input_list") else None,
        "to_state_type": type(result.to_state()).__name__ if hasattr(result, "to_state") else None,
    }


async def collect_stream(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    async for event in result.stream_events():
        data = getattr(event, "data", None)
        item = getattr(event, "item", None)
        rows.append({
            "ts": time.time(),
            "stream_type": getattr(event, "type", type(event).__name__),
            "name": getattr(event, "name", None),
            "data_type": getattr(data, "type", None),
            "delta": getattr(data, "delta", None),
            "item_type": getattr(item, "type", None),
            "item_raw_type": getattr(getattr(item, "raw_item", None), "type", None),
            "event": jsonable(event),
        })
    return rows


class Weather(BaseModel):
    city: str = Field(description="城市")
    temperature_range: str
    conditions: str


@function_tool
async def get_weather(city: str) -> Weather:
    return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind")


@function_tool
async def list_projects() -> list[dict[str, str]]:
    return [
        {"id": "proj_demo_001", "name": "RPG Global Launch"},
        {"id": "proj_demo_002", "name": "SLG Creative Test"},
    ]


class MemoryTraceProcessor(TracingProcessor):
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def on_trace_start(self, trace_obj: Any) -> None:
        self.rows.append({"kind": "trace_start", "trace": jsonable(trace_obj.export())})

    def on_trace_end(self, trace_obj: Any) -> None:
        self.rows.append({"kind": "trace_end", "trace": jsonable(trace_obj.export())})

    def on_span_start(self, span: Any) -> None:
        self.rows.append({"kind": "span_start", "span": jsonable(span.export())})

    def on_span_end(self, span: Any) -> None:
        self.rows.append({"kind": "span_end", "span": jsonable(span.export())})

    def shutdown(self) -> None:
        self.rows.append({"kind": "shutdown"})

    def force_flush(self) -> None:
        self.rows.append({"kind": "force_flush"})


async def probe_tools() -> None:
    agent = Agent(
        name="Tool Probe Agent",
        instructions="必须调用工具回答。回答时说明工具返回了什么。",
        model=build_model(),
        tools=[get_weather, list_projects],
    )
    result = Runner.run_streamed(agent, "东京天气怎样？然后列出当前项目。")
    rows = await collect_stream(result)
    write_jsonl(OUTPUT_DIR / "tools_stream_events.jsonl", rows)
    write_json(OUTPUT_DIR / "tools_result.json", summarize_result(result))


async def probe_handoff() -> None:
    project_agent = Agent(
        name="project_agent",
        handoff_description="回答项目管理和项目列表问题",
        instructions="你只处理项目管理问题。若问项目列表，说明需要调用业务项目 API；当前只返回示例说明。",
        model=build_model(),
        tools=[list_projects],
    )
    chat_agent = Agent(
        name="chat_agent",
        handoff_description="回答普通对话问题",
        instructions="你只处理普通对话。",
        model=build_model(),
    )
    triage = Agent(
        name="triage_agent",
        instructions="根据用户问题选择合适 agent。项目相关交给 project_agent，普通对话交给 chat_agent。",
        model=build_model(),
        handoffs=[handoff(project_agent), handoff(chat_agent)],
    )
    result = Runner.run_streamed(triage, "现在有哪些项目？")
    rows = await collect_stream(result)
    write_jsonl(OUTPUT_DIR / "handoff_stream_events.jsonl", rows)
    write_json(OUTPUT_DIR / "handoff_result.json", summarize_result(result))


async def probe_agent_as_tool() -> None:
    project_agent = Agent(
        name="Project Lookup Agent",
        instructions="用 list_projects 工具回答项目问题。",
        model=build_model(),
        tools=[list_projects],
    )
    nested_rows: list[dict[str, Any]] = []

    def on_stream(event: dict[str, Any]) -> None:
        stream = event["event"]
        nested_rows.append({
            "agent": event["agent"].name,
            "tool_call": jsonable(event.get("tool_call")),
            "stream_type": getattr(stream, "type", None),
            "name": getattr(stream, "name", None),
            "event": jsonable(stream),
        })

    main_agent = Agent(
        name="Main Agent",
        instructions="必须把项目问题交给 project_lookup_agent 工具。",
        model=build_model(),
        tools=[project_agent.as_tool(
            tool_name="project_lookup_agent",
            tool_description="查询和解释项目列表",
            on_stream=on_stream,
        )],
    )
    result = Runner.run_streamed(main_agent, "现在有哪些项目？")
    rows = await collect_stream(result)
    write_jsonl(OUTPUT_DIR / "agent_as_tool_parent_stream_events.jsonl", rows)
    write_jsonl(OUTPUT_DIR / "agent_as_tool_nested_stream_events.jsonl", nested_rows)
    write_json(OUTPUT_DIR / "agent_as_tool_result.json", summarize_result(result))


async def probe_session_state() -> None:
    session_path = OUTPUT_DIR / "probe_sqlite_session.db"
    session = SQLiteSession("probe_session", db_path=str(session_path))
    agent = Agent(
        name="Session Probe Agent",
        instructions="记住用户说的代号，并在下一轮复述。",
        model=build_model(),
    )
    first = await Runner.run(agent, "我的代号是 ANIFORCE-42。", session=session)
    second = await Runner.run(agent, "我的代号是什么？", session=session)
    state = second.to_state()
    write_json(OUTPUT_DIR / "session_state_result.json", {
        "first": summarize_result(first),
        "second": summarize_result(second),
        "state": jsonable(state),
        "state_type": type(state).__name__,
        "session_db": str(session_path),
    })


async def probe_trace() -> None:
    processor = MemoryTraceProcessor()
    add_trace_processor(processor)
    set_tracing_disabled(False)
    agent = Agent(
        name="Trace Probe Agent",
        instructions="调用 list_projects 后简短回答。",
        model=build_model(),
        tools=[list_projects],
    )
    with trace("aniforce-sdk-trace-probe", group_id="drafts-260611"):
        result = await Runner.run(agent, "列出项目。")
    write_jsonl(OUTPUT_DIR / "trace_events.jsonl", processor.rows)
    write_json(OUTPUT_DIR / "trace_result.json", summarize_result(result))
    set_tracing_disabled(True)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("probe", choices=["tools", "handoff", "agent_as_tool", "session", "trace", "all"])
    args = parser.parse_args()
    set_tracing_disabled(True)
    if args.probe in {"tools", "all"}:
      await probe_tools()
    if args.probe in {"handoff", "all"}:
      await probe_handoff()
    if args.probe in {"agent_as_tool", "all"}:
      await probe_agent_as_tool()
    if args.probe in {"session", "all"}:
      await probe_session_state()
    if args.probe in {"trace", "all"}:
      await probe_trace()


if __name__ == "__main__":
    asyncio.run(main())
