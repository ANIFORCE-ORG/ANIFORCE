#!/usr/bin/env python3
# %%
"""调试 Runner 基础运行与智能体循环：ANIFORCE 场景。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260701_01_runner_basic_and_turn_loop_debug.py

验证点：
1. Runner.run(): 异步运行，返回 RunResult
2. Runner.run_sync(): 同步运行，底层包装异步 run
3. 有工具调用时的 loop: LLM -> tool_call -> tool_output -> LLM -> final_output
4. max_turns 太小时触发 MaxTurnsExceeded
"""

import asyncio
from typing import Annotated

from openai import AsyncOpenAI
from agents import Agent, MaxTurnsExceeded, ModelSettings, Runner, function_tool, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel

MODEL = "gpt-5.3-codex"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"

set_tracing_disabled(True)


def make_model() -> OpenAIResponsesModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIResponsesModel(model=MODEL, openai_client=client)


@function_tool
def get_project_summary(project_id: Annotated[str, "项目 ID，例如 P001"]) -> str:
    """查询 ANIFORCE 项目摘要，包括项目目标、预算和投放状态。"""
    data = {
        "P001": "项目 P001：二次元手游夏促，目标提升预约转化，预算 50 万，状态：投放中。",
        "P002": "项目 P002：新游首发预约，目标提升点击率，预算 80 万，状态：素材测试中。",
    }
    return data.get(project_id, f"未找到项目 {project_id}")


@function_tool
def get_project_roi(project_id: Annotated[str, "项目 ID，例如 P001"]) -> str:
    """查询 ANIFORCE 项目的 ROI 数据。"""
    data = {
        "P001": "项目 P001 当前 ROI=3.2，CTR=2.5%，CVR=7.8%。",
        "P002": "项目 P002 当前 ROI=2.1，CTR=3.1%，CVR=5.4%。",
    }
    return data.get(project_id, f"未找到项目 {project_id} 的 ROI 数据")


def build_agent(name: str = "ANIFORCE Runner Basic Agent") -> Agent:
    return Agent(
        name=name,
        instructions=(
            "你是 ANIFORCE 营销助手。"
            "涉及项目摘要或 ROI 数据时必须调用工具，不要凭空编造。"
        ),
        model=make_model(),
        tools=[get_project_summary, get_project_roi],
        model_settings=ModelSettings(
            parallel_tool_calls=False,
            truncation="auto",
            store=False,
        ),
    )


def print_items(title: str, result) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")
    for item in result.new_items:
        print(item)
        print("\n" + "-" * 80 + "\n")
    print("最终回答：", result.final_output)


def run_sync_demo() -> None:
    """同步入口：适合普通脚本或非 async 环境。"""
    agent = build_agent("ANIFORCE Runner Sync Agent")
    result = Runner.run_sync(agent, "用一句话介绍 ANIFORCE 是什么。", max_turns=3)
    print_items("1. Runner.run_sync(): 普通问答，无工具调用", result)



#默认是async
async def run_async_and_tool_loop_demo() -> None:
    """异步入口：验证工具调用后的智能体循环。"""
    agent = build_agent("ANIFORCE Runner Async Agent")
    result = await Runner.run(agent, "查询项目 P001 的摘要和 ROI，并给出一句投放判断。", max_turns=5)
    print_items("2. Runner.run(): 工具调用 loop", result)


async def run_max_turns_demo() -> None:
    """max_turns 太小：模型发出工具调用后没有足够轮次继续生成最终回答。"""
    agent = build_agent("ANIFORCE Max Turns Agent")
    print("\n" + "=" * 80)
    print("3. max_turns: 触发 MaxTurnsExceeded")
    print("=" * 80 + "\n")
    try:
        await Runner.run(agent, "查询项目 P001 的 ROI，然后总结是否值得加预算。", max_turns=1)
        print("未触发 MaxTurnsExceeded：这不符合本调试预期")
    except MaxTurnsExceeded as e:
        print(f"捕获 MaxTurnsExceeded: {e}")


async def main() -> None:
    await run_async_and_tool_loop_demo()
    await run_max_turns_demo()


if __name__ == "__main__":
    # run_sync 不能放在已经运行的 event loop 里，所以先跑同步 demo，再跑异步 demo。
    run_sync_demo()
    asyncio.run(main())
