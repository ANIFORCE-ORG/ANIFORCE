#!/usr/bin/env python3
# %%
"""完整展示流式输出：reasoning + output_text，带详细时间戳。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260702_04_full_streaming_with_reasoning_debug.py
"""

import asyncio
import time
from typing import Annotated

from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent, ResponseReasoningTextDeltaEvent
from agents import Agent, ModelSettings, Runner, function_tool, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

MODEL = "deepseek-v4-pro"
BASE_URL = "https://copilot.huya.info/api/openai/v1"
API_KEY = "sk-hvtAUe3lPjYQtwiZqLMfYg"

set_tracing_disabled(True)


def make_model() -> OpenAIChatCompletionsModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIChatCompletionsModel(model=MODEL, openai_client=client)


@function_tool
def get_material_metrics(material_id: Annotated[str, "素材 ID"]) -> str:
    """查询素材投放指标。"""
    return f"素材 {material_id}：CTR=2.8%，CVR=8.1%，ROI=3.4。"


def build_agent() -> Agent:
    return Agent(
        name="Agent",
        instructions="你是营销助手。涉及素材指标时调用工具。",
        model=make_model(),
        tools=[get_material_metrics],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )


async def main() -> None:
    agent = build_agent()
    result = Runner.run_streamed(agent, "查询素材 M001 并给优化建议", max_turns=3)

    print("\n" + "=" * 80)
    print("完整流式输出：Reasoning + Output Text")
    print("=" * 80 + "\n")

    start_time = time.time()
    last_event_time = start_time
    reasoning_started = False
    output_started = False

    async for event in result.stream_events():
        current_time = time.time()
        elapsed = current_time - start_time
        delta_time = current_time - last_event_time
        last_event_time = current_time

        # Reasoning 文本 delta
        if event.type == "raw_response_event" and isinstance(event.data, ResponseReasoningTextDeltaEvent):
            if event.data.delta:
                if not reasoning_started:
                    print(f"\n[{elapsed:.3f}s] 🧠 Reasoning 开始：\n")
                    reasoning_started = True
                print(f"[{elapsed:.3f}s] (+{delta_time*1000:.1f}ms) {event.data.delta}", end="", flush=True)

        # 最终输出文本 delta
        elif event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            if event.data.delta:
                if reasoning_started and not output_started:
                    print(f"\n\n[{elapsed:.3f}s] 📝 最终输出开始：\n")
                    output_started = True
                    reasoning_started = False
                print(f"[{elapsed:.3f}s] (+{delta_time*1000:.1f}ms) {event.data.delta}", end="", flush=True)

        # 工具调用进度
        elif event.type == "run_item_stream_event":
            if event.name == "tool_called":
                raw_item = event.item.raw_item
                tool_name = getattr(raw_item, "name", None)
                print(f"\n\n[{elapsed:.3f}s] 🔧 工具调用: {tool_name}")
            elif event.name == "tool_output":
                print(f"[{elapsed:.3f}s] ✅ 工具返回: {event.item.output}")

    print(f"\n\n{'='*80}")
    print("流式传输完成")
    print(f"总耗时: {time.time() - start_time:.2f}s")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
