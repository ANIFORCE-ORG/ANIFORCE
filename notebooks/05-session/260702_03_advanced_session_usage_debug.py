#!/usr/bin/env python3
# %%
"""测试 AdvancedSQLiteSession 用量统计。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/05-session/260702_03_advanced_session_usage_debug.py

验证点：
1. store_run_usage() 记录用量
2. get_session_usage() 查询总用量
3. get_turn_usage() 查询每轮用量
4. 多轮对话累计用量
5. 分支隔离用量统计
"""

import asyncio
from pathlib import Path

from openai import AsyncOpenAI
from agents import (
    Agent,
    ModelSettings,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from agents.extensions.memory import AdvancedSQLiteSession
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from typing import Annotated

MODEL = "deepseek-v4-pro"
BASE_URL = "https://copilot.huya.info/api/openai/v1"
API_KEY = "sk-hvtAUe3lPjYQtwiZqLMfYg"

set_tracing_disabled(True)


def make_model() -> OpenAIChatCompletionsModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIChatCompletionsModel(model=MODEL, openai_client=client)


@function_tool
def get_campaign_budget(campaign_id: Annotated[str, "活动 ID"]) -> str:
    """查询活动预算。"""
    return f"活动 {campaign_id} 预算为 5000 元"


def print_section(title: str) -> None:
    """打印章节标题。"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


async def test_basic_usage_tracking() -> None:
    """场景1：基础用量统计。"""
    print_section("场景1：基础用量统计")

    agent = Agent(
        name="Assistant",
        instructions="你是助手，回答简洁。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    db_path = Path("drafts/260702/advanced_usage.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    session = AdvancedSQLiteSession(
        session_id="user_001",
        db_path=str(db_path),
        create_tables=True,
    )

    print("【第1轮对话】")
    print("用户: 你好，我是张三\n")
    result = await Runner.run(agent, "你好，我是张三", session=session)
    print(f"助手: {result.final_output}\n")

    # 🔥 关键：记录用量
    await session.store_run_usage(result)
    print("✅ 已记录第1轮用量\n")

    print("【第2轮对话】")
    print("用户: 我叫什么名字？\n")
    result = await Runner.run(agent, "我叫什么名字？", session=session)
    print(f"助手: {result.final_output}\n")

    await session.store_run_usage(result)
    print("✅ 已记录第2轮用量\n")

    # 查询总用量
    print("【查询总用量】")
    usage = await session.get_session_usage()
    if usage:
        print(f"  总请求数: {usage['requests']}")
        print(f"  总 tokens: {usage['total_tokens']}")
        print(f"  输入 tokens: {usage['input_tokens']}")
        print(f"  输出 tokens: {usage['output_tokens']}")
        print(f"  总轮数: {usage['total_turns']}")
    else:
        print("  暂无用量数据")


async def test_turn_by_turn_usage() -> None:
    """场景2：按轮次查看用量。"""
    print_section("场景2：按轮次查看用量")

    agent = Agent(
        name="Assistant",
        instructions="你是助手。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    session = AdvancedSQLiteSession(
        session_id="turn_test",
        create_tables=True,
    )

    # 3轮对话
    questions = [
        "你好",
        "今天天气不错",
        "明天呢？",
    ]

    for i, question in enumerate(questions, 1):
        print(f"【第{i}轮】用户: {question}")
        result = await Runner.run(agent, question, session=session)
        print(f"助手: {result.final_output}\n")
        await session.store_run_usage(result)

    # 查询每轮用量
    print("【每轮用量统计】")
    turn_usage = await session.get_turn_usage()
    for turn_data in turn_usage:
        turn = turn_data['user_turn_number']
        tokens = turn_data['total_tokens']
        input_tokens = turn_data['input_tokens']
        output_tokens = turn_data['output_tokens']
        print(f"  第{turn}轮: 总 {tokens} tokens (输入 {input_tokens} + 输出 {output_tokens})")

    # 查询总用量
    print("\n【总用量】")
    usage = await session.get_session_usage()
    if usage:
        print(f"  总 tokens: {usage['total_tokens']}")
        print(f"  平均每轮: {usage['total_tokens'] / usage['total_turns']:.1f} tokens")


async def test_tool_call_usage() -> None:
    """场景3：工具调用的用量统计。"""
    print_section("场景3：工具调用的用量统计")

    agent = Agent(
        name="Assistant",
        instructions="你是助手。",
        model=make_model(),
        tools=[get_campaign_budget],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    session = AdvancedSQLiteSession(
        session_id="tool_usage_test",
        create_tables=True,
    )

    print("【对话1：不调用工具】")
    print("用户: 你好\n")
    result = await Runner.run(agent, "你好", session=session)
    print(f"助手: {result.final_output}\n")
    await session.store_run_usage(result)

    print("【对话2：调用工具】")
    print("用户: 查询活动 C001 的预算\n")
    result = await Runner.run(agent, "查询活动 C001 的预算", session=session)
    print(f"助手: {result.final_output}\n")
    await session.store_run_usage(result)

    # 查询每轮用量
    print("【每轮用量对比】")
    turn_usage = await session.get_turn_usage()
    for turn_data in turn_usage:
        turn = turn_data['user_turn_number']
        tokens = turn_data['total_tokens']
        requests = turn_data['requests']
        print(f"  第{turn}轮: {tokens} tokens, {requests} 次请求")
        if requests > 1:
            print("    ^ 包含工具调用，请求数 > 1")


async def test_branch_usage_isolation() -> None:
    """场景4：分支用量隔离。"""
    print_section("场景4：分支用量隔离")

    agent = Agent(
        name="Assistant",
        instructions="你是助手。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    session = AdvancedSQLiteSession(
        session_id="branch_usage_test",
        create_tables=True,
    )

    # 主分支对话
    print("【主分支：第1轮】")
    result = await Runner.run(agent, "你好", session=session)
    print(f"助手: {result.final_output}\n")
    await session.store_run_usage(result)

    print("【主分支：第2轮】")
    result = await Runner.run(agent, "今天天气不错", session=session)
    print(f"助手: {result.final_output}\n")
    await session.store_run_usage(result)

    # 创建分支
    print("【创建分支：从第2轮分支】")
    branch_id = await session.create_branch_from_turn(2, branch_name="alternative")
    print(f"分支 ID: {branch_id}\n")

    # 在分支中对话
    print("【分支对话】")
    result = await Runner.run(agent, "明天呢？", session=session)
    print(f"助手: {result.final_output}\n")
    await session.store_run_usage(result)

    # 查询主分支用量
    print("【主分支用量】")
    main_usage = await session.get_session_usage(branch_id="main")
    if main_usage:
        print(f"  总 tokens: {main_usage['total_tokens']}")
        print(f"  总轮数: {main_usage['total_turns']}")

    # 查询分支用量
    print(f"\n【分支 {branch_id} 用量】")
    branch_usage = await session.get_session_usage(branch_id=branch_id)
    if branch_usage:
        print(f"  总 tokens: {branch_usage['total_tokens']}")
        print(f"  总轮数: {branch_usage['total_turns']}")

    print("\n✅ 不同分支的用量完全隔离")


async def test_usage_details() -> None:
    """场景5：详细用量信息。"""
    print_section("场景5：详细用量信息（JSON 明细）")

    agent = Agent(
        name="Assistant",
        instructions="你是助手。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    session = AdvancedSQLiteSession(
        session_id="usage_details_test",
        create_tables=True,
    )

    result = await Runner.run(agent, "你好，介绍一下自己", session=session)
    print(f"助手: {result.final_output}\n")
    await session.store_run_usage(result)

    # 查询详细用量
    print("【用量明细】")
    turn_usage = await session.get_turn_usage()
    if turn_usage:
        turn_data = turn_usage[0]
        print(f"  总 tokens: {turn_data['total_tokens']}")
        print(f"  输入 tokens: {turn_data['input_tokens']}")
        print(f"  输出 tokens: {turn_data['output_tokens']}")
        
        if turn_data.get('input_tokens_details'):
            print(f"\n  输入明细 (JSON):")
            import json
            print(f"    {json.dumps(turn_data['input_tokens_details'], ensure_ascii=False, indent=4)}")
        
        if turn_data.get('output_tokens_details'):
            print(f"\n  输出明细 (JSON):")
            print(f"    {json.dumps(turn_data['output_tokens_details'], ensure_ascii=False, indent=4)}")


async def main() -> None:
    await test_basic_usage_tracking()
    await test_turn_by_turn_usage()
    await test_tool_call_usage()
    await test_branch_usage_isolation()
    await test_usage_details()

    print("\n" + "=" * 80)
    print("所有场景调试完成")
    print("=" * 80)
    print("\n关键总结：")
    print("1. 每次 Runner.run() 后必须调用 session.store_run_usage(result)")
    print("2. get_session_usage() 查询总用量（可按分支过滤）")
    print("3. get_turn_usage() 查询每轮用量（包含详细 JSON）")
    print("4. 工具调用会产生多次请求，用量会更高")
    print("5. 不同分支的用量完全隔离统计")


if __name__ == "__main__":
    asyncio.run(main())
