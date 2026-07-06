#!/usr/bin/env python3
# %%
"""调试非流式调用：OpenAIChatCompletionsModel + codefoxai claude-sonnet-5。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260701_02_runner_nonstreaming_chatcompletions_debug.py

验证点：
1. 非流式调用工具是否正常
2. 如果非流式正常，说明问题只在流式处理逻辑
"""

import asyncio
from typing import Annotated

from openai import AsyncOpenAI
from agents import Agent, ModelSettings, Runner, function_tool, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

MODEL = "claude-sonnet-5"
BASE_URL = "https://www.codefoxai.top/v1"
API_KEY = "sk-o0giBF5bZbqYQ5LwLpt4vBm5npG6syLw9mrZKj5yJ6yu0ZnS"

set_tracing_disabled(True)


def make_model() -> OpenAIChatCompletionsModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIChatCompletionsModel(
        model=MODEL,
        openai_client=client,
        buffer_streamed_tool_calls=True,
    )


@function_tool
def get_material_metrics(material_id: Annotated[str, "素材 ID，例如 M001"]) -> str:
    """查询素材投放指标，包括 CTR、CVR、ROI 和消耗。"""
    data = {
        "M001": "素材 M001：CTR=2.8%，CVR=8.1%，ROI=3.4，消耗=12000 元。",
        "M002": "素材 M002：CTR=1.9%，CVR=5.6%，ROI=2.2，消耗=9000 元。",
    }
    return data.get(material_id, f"未找到素材 {material_id} 的投放指标")


def build_agent() -> Agent:
    return Agent(
        name="ANIFORCE Non-Streaming Agent",
        instructions=(
            "你是 ANIFORCE 营销助手。"
            "涉及素材指标时必须调用工具。"
            "回答要简洁，最后给出一个优化建议。"
        ),
        model=make_model(),
        tools=[get_material_metrics],
        model_settings=ModelSettings(
            parallel_tool_calls=False,
            truncation="auto",
            store=False,
        ),
    )


async def run_non_streamed_demo() -> None:
    agent = build_agent()
    
    # 使用 Runner.run 非流式调用
    result = await Runner.run(
        agent,
        "分析素材 M001 的投放表现，并给一个优化建议。",
        max_turns=5,
    )

    print("\n" + "=" * 80)
    print("非流式调用结果")
    print("=" * 80 + "\n")
    print("最终回答：", result.final_output)

    print("\n" + "=" * 80)
    print("result.new_items")
    print("=" * 80 + "\n")
    for item in result.new_items:
        item_type = getattr(item, "type", type(item).__name__)
        raw_item = getattr(item, "raw_item", None)
        output = getattr(item, "output", None)
        if item_type == "tool_call_item":
            print(f"- tool_call: {getattr(raw_item, 'name', None)} args={getattr(raw_item, 'arguments', None)}")
        elif item_type == "tool_call_output_item":
            print(f"- tool_output: {output}")
        elif item_type == "message_output_item":
            print("- message_output")
        else:
            print(f"- {item_type}")


if __name__ == "__main__":
    asyncio.run(run_non_streamed_demo())
