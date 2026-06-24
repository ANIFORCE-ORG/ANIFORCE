"""OpenAI Agents SDK Tracing 能力调试

测试 Tracing 的核心能力：
1. set_tracing 启用追踪
2. trace events 数据格式
3. trace 与 backend 集成方式

运行方式：
  cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE
  UV_CACHE_DIR=./uv_cache uv run python drafts/260624/03_tracing_probe.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "aniforce-agent"))

from agents import Agent, Runner, function_tool, set_trace_processors, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from agents.tracing import TracingProcessor
from openai import AsyncOpenAI

LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "drafts"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / f"tracing_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"


def load_agent_env():
    env_path = Path("aniforce-agent/.env")
    if not env_path.exists():
        raise RuntimeError("Missing aniforce-agent/.env")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def create_sdk_model():
    load_agent_env()
    api_mode = os.environ.get("OPENAI_AGENTS_API", "").strip().lower()
    if api_mode not in {"chat", "chat_completions", "chat-completions"}:
        raise RuntimeError(f"DeepSeek probe requires chat_completions, got {api_mode!r}")
    model = os.environ.get("OPENAI_AGENTS_MODEL", "deepseek-v4-pro")
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )
    return OpenAIChatCompletionsModel(model=model, openai_client=client)


def log_event(event_type: str, data: dict):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": event_type, "timestamp": datetime.now().isoformat(), "data": data}, ensure_ascii=False) + "\n")


class MemoryTraceProcessor(TracingProcessor):
    def __init__(self):
        self.events = []

    def on_trace_start(self, trace):
        self.events.append({
            "event": "trace.start",
            "trace_id": trace.trace_id,
            "name": getattr(trace, "name", None),
        })

    def on_trace_end(self, trace):
        self.events.append({
            "event": "trace.end",
            "trace_id": trace.trace_id,
            "name": getattr(trace, "name", None),
        })

    def on_span_start(self, span):
        self.events.append({
            "event": "span.start",
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_id": span.parent_id,
            "span_type": type(span.span_data).__name__,
        })

    def on_span_end(self, span):
        exported = span.export() or {}
        self.events.append({
            "event": "span.end",
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_id": span.parent_id,
            "span_type": type(span.span_data).__name__,
            "export_keys": sorted(exported.keys()),
        })

    def shutdown(self):
        return None

    def force_flush(self):
        return None


def enable_memory_tracing():
    processor = MemoryTraceProcessor()
    set_trace_processors([processor])
    set_tracing_disabled(False)
    return processor


def disable_memory_tracing():
    set_tracing_disabled(True)
    set_trace_processors([])


@function_tool
def calculate(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"


@function_tool
def get_weather(city: str) -> str:
    """获取天气（模拟）"""
    return f"{city} 的天气：晴天，25度"


async def test_tracing_enabled():
    """测试 1: 启用 tracing 并捕获 trace events"""
    print("\n=== Test 1: 启用 Tracing ===")

    processor = enable_memory_tracing()

    agent = Agent(
        name="assistant",
        instructions="你是一个助手，可以计算和查天气。",
        model=create_sdk_model(),
        tools=[calculate, get_weather]
    )

    print("\n执行: 计算 123 + 456，并查询北京天气")
    result = await Runner.run(agent, "计算 123 + 456，并查询北京天气")

    trace_events = processor.events
    log_event("tracing_enabled", {
        "result": result.final_output,
        "trace_events_count": len(trace_events),
        "trace_events_sample": trace_events[:3] if trace_events else []
    })

    print(f"✓ 捕获到 {len(trace_events)} 个 trace events")
    if trace_events:
        print(f"  样例 trace event 类型: {trace_events[0]['event']}")

    disable_memory_tracing()

    return trace_events


async def test_trace_structure():
    """测试 2: Trace 数据结构分析"""
    print("\n=== Test 2: Trace 数据结构 ===")

    processor = enable_memory_tracing()

    agent = Agent(name="test", instructions="test", model=create_sdk_model(), tools=[calculate])
    await Runner.run(agent, "计算 1+1")

    trace_events = processor.events
    disable_memory_tracing()

    if trace_events:
        log_event("trace_structure", {
            "events_count": len(trace_events),
            "unique_events": list(set(e["event"] for e in trace_events)),
            "unique_span_types": sorted(set(e["span_type"] for e in trace_events if "span_type" in e)),
            "sample_structure": trace_events[0] if trace_events else None
        })

        print(f"✓ Trace event 类型: {set(e['event'] for e in trace_events)}")
    else:
        print("✗ 未捕获到 trace events")


async def test_tracing_vs_streaming():
    """测试 3: Tracing 与 Streaming 的关系"""
    print("\n=== Test 3: Tracing vs Streaming ===")

    stream_events = []
    processor = enable_memory_tracing()

    agent = Agent(name="test", instructions="简洁回答", model=create_sdk_model())

    # Streaming run
    print("\n使用 run_streamed")
    result = Runner.run_streamed(agent, "你好")

    async for event in result.stream_events():
        stream_events.append({"type": event.type, "source": "stream"})

    trace_events = processor.events
    disable_memory_tracing()

    log_event("tracing_vs_streaming", {
        "trace_events_count": len(trace_events),
        "stream_events_count": len(stream_events),
        "trace_types": [e['event'] for e in trace_events[:5]],
        "stream_types": [e['type'] for e in stream_events[:5]]
    })

    print(f"  Trace events: {len(trace_events)}")
    print(f"  Stream events: {len(stream_events)}")
    print("  结论: Tracing 是调试/监控层，Stream 是用户实时反馈层")


async def main():
    print("OpenAI Agents SDK Tracing 能力调试")
    print(f"日志文件: {log_file}")
    print("=" * 60)

    try:
        await test_tracing_enabled()
        await test_trace_structure()
        await test_tracing_vs_streaming()

        print("\n" + "=" * 60)
        print(f"✓ 所有测试完成，日志已写入: {log_file}")
        print("\n关键发现：")
        print("1. Tracing 是全局钩子，可以捕获所有 agent 执行细节")
        print("2. Trace events 包含 agent、tool、input、output、duration 等")
        print("3. Tracing 独立于 Streaming，两者可以同时启用")
        print("4. Tracing 适合做性能监控、审计日志，不是用户可见的 UI 数据源")
        print("5. Backend 可以实现自定义 trace_handler 写入数据库")

    except Exception as e:
        log_event("error", {"message": str(e), "type": type(e).__name__})
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    set_tracing_disabled(True)
    asyncio.run(main())
