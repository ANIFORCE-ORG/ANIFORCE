#!/usr/bin/env python3
# %%
"""按官方教程调试流式输出：只打印最终 output_text delta。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260702_03_official_streaming_debug.py

验证点：
1. 按官方推荐方式处理流式事件
2. 只打印最终输出文本，忽略 reasoning
3. 验证真正的流式粒度
"""

import asyncio
import time
from typing import Annotated

from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent
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
def get_material_metrics(material_id: Annotated[str, "素材 ID，例如 M001"]) -> str:
    """查询素材投放指标。"""
    data = {
        "M001": "素材 M001：CTR=2.8%，CVR=8.1%，ROI=3.4，消耗=12000 元。",
    }
    return data.get(material_id, f"未找到素材 {material_id}")


def build_agent() -> Agent:
    return Agent(
        name="ANIFORCE Streaming Agent",
        instructions="你是 ANIFORCE 营销助手。涉及素材指标时调用工具。回答简洁。",
        model=make_model(),
        tools=[get_material_metrics],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )


async def stream_output_text_only() -> None:
    """方式1：按官方教程，逐 token 打印输出文本（忽略 reasoning）。"""
    agent = build_agent()
    result = Runner.run_streamed(agent, "查询素材 M001 的投放表现并给优化建议", max_turns=5)

    print("\n" + "=" * 80)
    print("方式1：逐 token 打印输出文本（忽略 reasoning）")
    print("=" * 80 + "\n")

    start_time = time.time()
    
    async for event in result.stream_events():
        elapsed = time.time() - start_time
        
        # 只处理最终输出文本的 delta
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            if event.data.delta:  # 只打印非空 delta
                print(f"[{elapsed:.3f}s] {event.data.delta}", end="", flush=True)

    print("\n\n最终回答：", result.final_output)


async def stream_with_progress_updates() -> None:
    """方式2：按官方教程，打印高层级事件（tool_called, message_output）。"""
    agent = build_agent()
    result = Runner.run_streamed(agent, "查询素材 M001 的投放表现并给优化建议", max_turns=5)

    print("\n" + "=" * 80)
    print("方式2：高层级进度更新（忽略原始 delta）")
    print("=" * 80 + "\n")

    start_time = time.time()

    async for event in result.stream_events():
        elapsed = time.time() - start_time
        
        # 忽略原始 delta 事件
        if event.type == "raw_response_event":
            continue
        
        # Agent 更新
        elif event.type == "agent_updated_stream_event":
            print(f"[{elapsed:.3f}s] Agent 更新: {event.new_agent.name}")
        
        # 运行项事件
        elif event.type == "run_item_stream_event":
            if event.name == "tool_called":
                raw_item = event.item.raw_item
                tool_name = getattr(raw_item, "name", None)
                tool_args = getattr(raw_item, "arguments", None)
                print(f"[{elapsed:.3f}s] 工具调用: {tool_name}({tool_args})")
            
            elif event.name == "tool_output":
                print(f"[{elapsed:.3f}s] 工具返回: {event.item.output}")
            
            elif event.name == "message_output_created":
                print(f"[{elapsed:.3f}s] 消息生成完成")
            
            elif event.name == "reasoning_item_created":
                print(f"[{elapsed:.3f}s] Reasoning 完成（deepseek 特性）")

    print(f"\n最终回答：{result.final_output}")


async def main() -> None:
    await stream_output_text_only()
    print("\n\n" + "#" * 80 + "\n\n")
    await stream_with_progress_updates()


if __name__ == "__main__":
    asyncio.run(main())
