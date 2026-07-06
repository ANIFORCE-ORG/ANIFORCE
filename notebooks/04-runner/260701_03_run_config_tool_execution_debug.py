#!/usr/bin/env python3
# %%
"""调试 RunConfig.tool_execution：本地函数工具并发控制。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260701_03_run_config_tool_execution_debug.py

验证点：
1. ModelSettings.parallel_tool_calls=True：允许模型同一轮发多个工具调用
2. RunConfig.tool_execution.max_function_tool_concurrency=None：SDK 默认同时执行本轮所有本地函数工具
3. RunConfig.tool_execution.max_function_tool_concurrency=1：SDK 侧强制本地函数工具串行执行
4. parallel_tool_calls 和 max_function_tool_concurrency 是两层控制：
   - parallel_tool_calls 控制模型能不能一次发多个工具调用
   - max_function_tool_concurrency 控制 SDK 拿到多个工具调用后同时跑几个
"""

import asyncio
import time
from typing import Annotated

from openai import AsyncOpenAI
from agents import Agent, ModelSettings, RunConfig, Runner, ToolExecutionConfig, function_tool, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel

MODEL = "gpt-5.3-codex"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"

set_tracing_disabled(True)

RUN_LABEL = ""
RUN_START = 0.0


def now() -> str:
    return f"+{time.perf_counter() - RUN_START:.2f}s"


def make_model() -> OpenAIResponsesModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIResponsesModel(model=MODEL, openai_client=client)


async def fake_api_call(name: str, delay: float = 1.2) -> str:
    print(f"[{RUN_LABEL}] {now()} START {name}", flush=True)
    await asyncio.sleep(delay)
    print(f"[{RUN_LABEL}] {now()} END   {name}", flush=True)
    return "done"


@function_tool
async def fetch_meta_campaign_metrics(project_id: Annotated[str, "项目 ID，例如 P001"]) -> str:
    """查询 Meta 渠道投放指标。"""
    await fake_api_call("fetch_meta_campaign_metrics")
    return f"{project_id} Meta: spend=12000, roi=3.1, ctr=2.6%"


@function_tool
async def fetch_tiktok_campaign_metrics(project_id: Annotated[str, "项目 ID，例如 P001"]) -> str:
    """查询 TikTok 渠道投放指标。"""
    await fake_api_call("fetch_tiktok_campaign_metrics")
    return f"{project_id} TikTok: spend=9000, roi=2.4, ctr=3.0%"


@function_tool
async def fetch_google_campaign_metrics(project_id: Annotated[str, "项目 ID，例如 P001"]) -> str:
    """查询 Google 渠道投放指标。"""
    await fake_api_call("fetch_google_campaign_metrics")
    return f"{project_id} Google: spend=15000, roi=2.8, ctr=2.2%"


def build_agent() -> Agent:
    return Agent(
        name="ANIFORCE Tool Execution Agent",
        instructions=(
            "你是 ANIFORCE 营销助手。"
            "当用户要求跨渠道对比时，必须分别调用 Meta、TikTok、Google 三个渠道工具。"
            "这些查询彼此独立，可以在同一轮发出多个工具调用。"
            "最后用三行以内总结结果。"
        ),
        model=make_model(),
        tools=[
            fetch_meta_campaign_metrics,
            fetch_tiktok_campaign_metrics,
            fetch_google_campaign_metrics,
        ],
        model_settings=ModelSettings(
            parallel_tool_calls=True,
            truncation="auto",
            store=False,
        ),
    )


def summarize_items(result) -> None:
    print("\nresult.new_items 摘要：")
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
    print("最终回答：", result.final_output)


async def run_case(label: str, max_concurrency: int | None) -> None:
    global RUN_LABEL, RUN_START
    RUN_LABEL = label
    RUN_START = time.perf_counter()

    print("\n" + "=" * 80)
    print(f"{label}: max_function_tool_concurrency={max_concurrency}")
    print("=" * 80 + "\n")

    result = await Runner.run(
        build_agent(),
        "对比项目 P001 在 Meta、TikTok、Google 三个渠道的投放表现。",
        max_turns=5,
        run_config=RunConfig(
            tool_execution=ToolExecutionConfig(
                max_function_tool_concurrency=max_concurrency,
            )
        ),
    )

    elapsed = time.perf_counter() - RUN_START
    print(f"\n[{label}] 总耗时: {elapsed:.2f}s")
    summarize_items(result)


async def main() -> None:
    await run_case("默认并发", None)
    await run_case("限制串行", 1)


if __name__ == "__main__":
    asyncio.run(main())
