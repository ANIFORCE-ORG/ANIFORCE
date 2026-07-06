#!/usr/bin/env python3
# %%
"""查看 SDK 原始流式事件输出。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260702_02_raw_stream_events_debug.py
"""

import asyncio
import time
from typing import Annotated

from openai import AsyncOpenAI
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
        name="Simple Agent",
        instructions="你是助手，涉及素材指标时调用工具。",
        model=make_model(),
        tools=[get_material_metrics],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )


async def main() -> None:
    agent = build_agent()
    result = Runner.run_streamed(agent, "查询素材 M001 的指标", max_turns=3)

    start_time = time.time()
    event_count = 0

    async for event in result.stream_events():
        elapsed = time.time() - start_time
        event_count += 1
        
        # 打印所有事件的完整信息
        print(f"\n[{elapsed:.3f}s] Event #{event_count}")
        print(f"Type: {event.type}")
        
        if event.type == "raw_response_event":
            data = event.data
            print(f"  raw_type: {getattr(data, 'type', None)}")
            print(f"  delta: {getattr(data, 'delta', None)!r}")
            print(f"  full data: {data}")
        else:
            print(f"  data: {event}")

    print(f"\n\n总事件数: {event_count}")
    print(f"最终回答: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
