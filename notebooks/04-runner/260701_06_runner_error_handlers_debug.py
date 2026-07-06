#!/usr/bin/env python3
# %%
"""调试 Runner 级错误兜底：error_handlers。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260701_06_runner_error_handlers_debug.py

验证点：
1. 不配置 error_handlers 时，max_turns 超限会抛 MaxTurnsExceeded
2. 配置 error_handlers={"max_turns": ...} 后，Runner.run 不抛异常，而是返回受控 final_output
3. 这是 Agent Runtime 级别兜底，不是单个工具的 failure_error_function
"""

import asyncio
from typing import Annotated

from openai import AsyncOpenAI
from agents import (
    Agent,
    MaxTurnsExceeded,
    ModelSettings,
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from agents.models.openai_responses import OpenAIResponsesModel

MODEL = "gpt-5.3-codex"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"

set_tracing_disabled(True)


def make_model() -> OpenAIResponsesModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIResponsesModel(model=MODEL, openai_client=client)


@function_tool
def get_project_roi(project_id: Annotated[str, "项目 ID，例如 P001"]) -> str:
    """查询项目 ROI 数据。"""
    return f"项目 {project_id}: ROI=3.2, CTR=2.5%, CVR=7.8%"


def build_agent() -> Agent:
    return Agent(
        name="ANIFORCE Runner Error Handler Agent",
        instructions=(
            "你是 ANIFORCE 营销助手。"
            "用户询问项目 ROI 时必须调用 get_project_roi 工具，然后再总结。"
        ),
        model=make_model(),
        tools=[get_project_roi],
        model_settings=ModelSettings(
            parallel_tool_calls=False,
            truncation="auto",
            store=False,
        ),
    )


def on_max_turns(data: RunErrorHandlerInput[None]) -> RunErrorHandlerResult:
    """把 MaxTurnsExceeded 转成用户可见的受控文本。"""
    print("\n[on_max_turns handler triggered]")
    print(f"error={data.error}")
    print(f"last_agent={data.run_data.last_agent.name}")
    print(f"new_items_count={len(data.run_data.new_items)}")

    return RunErrorHandlerResult(
        final_output=(
            "这次分析没有在限定轮次内完成。"
            "我已经停止继续调用模型/工具，以避免请求长时间挂起。"
            "请缩小问题范围，或稍后重试。"
        ),
        include_in_history=False,
    )


def summarize_result(title: str, result) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")
    print("final_output:", result.final_output)
    print("\nnew_items:")
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


async def without_handler_demo() -> None:
    print("\n" + "#" * 80)
    print("1. 不配置 error_handlers：直接抛 MaxTurnsExceeded")
    print("#" * 80)

    try:
        await Runner.run(
            build_agent(),
            "查询项目 P001 的 ROI，并判断是否值得加预算。",
            max_turns=1,
        )
        print("未触发 MaxTurnsExceeded：这不符合预期")
    except MaxTurnsExceeded as e:
        print(f"捕获 MaxTurnsExceeded: {e}")


async def with_handler_demo() -> None:
    print("\n" + "#" * 80)
    print("2. 配置 error_handlers：返回受控 final_output")
    print("#" * 80)

    result = await Runner.run(
        build_agent(),
        "查询项目 P001 的 ROI，并判断是否值得加预算。",
        max_turns=1,
        error_handlers={"max_turns": on_max_turns},
    )
    summarize_result("max_turns fallback result", result)


async def main() -> None:
    await without_handler_demo()
    await with_handler_demo()


if __name__ == "__main__":
    asyncio.run(main())
