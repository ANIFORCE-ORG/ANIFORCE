#!/usr/bin/env python3
# %%
"""调试函数工具超时：ANIFORCE 场景。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/03-runtime/260701_05_function_tool_timeout_debug.py
"""

import asyncio

from openai import AsyncOpenAI
from agents import Agent, ModelSettings, Runner, ToolTimeoutError, function_tool, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel

MODEL = "gpt-5.3-codex"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"

set_tracing_disabled(True)


@function_tool(timeout=1.0, timeout_behavior="error_as_result")
async def slow_material_metrics(material_id: str) -> str:
    """查询素材指标。超时后把错误作为工具结果返回给模型。"""
    await asyncio.sleep(3)
    return f"素材 {material_id}: CTR=2.3%, ROI=3.5"


@function_tool(timeout=1.0, timeout_behavior="raise_exception")
async def slow_publish_campaign(campaign_id: str) -> str:
    """发布广告计划。超时后直接让本次 run 失败。"""
    await asyncio.sleep(3)
    return f"广告计划 {campaign_id} 已发布"


async def main():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    model = OpenAIResponsesModel(model=MODEL, openai_client=client)

    # 1) error_as_result：工具超时会变成模型可见的工具输出，run 不崩
    recover_agent = Agent(
        name="ANIFORCE Timeout Recover Agent",
        instructions="你是 ANIFORCE 助手。工具超时时，明确告诉用户超时，并给出下一步建议。",
        model=model,
        tools=[slow_material_metrics],
        model_settings=ModelSettings(parallel_tool_calls=False, truncation="auto", store=False),
    )

    result = await Runner.run(recover_agent, "查询素材 M001 的投放指标", max_turns=3)
    print("\n=== error_as_result: result.new_items ===\n")
    for item in result.new_items:
        print(item)
        print("\n" + "-" * 80 + "\n")
    print("最终回答：", result.final_output)

    # 2) raise_exception：工具超时会抛 ToolTimeoutError，run 失败，由业务层处理
    hard_fail_agent = Agent(
        name="ANIFORCE Timeout Hard Fail Agent",
        instructions="你是 ANIFORCE 助手。发布广告计划必须调用工具。",
        model=model,
        tools=[slow_publish_campaign],
        model_settings=ModelSettings(parallel_tool_calls=False, truncation="auto", store=False),
    )

    print("\n=== raise_exception ===\n")
    try:
        await Runner.run(hard_fail_agent, "发布广告计划 C001", max_turns=3)
    except ToolTimeoutError as e:
        print(f"捕获 ToolTimeoutError: tool={e.tool_name}, timeout={e.timeout_seconds}s")


if __name__ == "__main__":
    asyncio.run(main())
