#!/usr/bin/env python3
# %%
"""系统调试 Session 会话管理。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/05-session/260702_01_session_management_debug.py

验证点：
1. 基础多轮对话（自动保持上下文）
2. SQLiteSession（内存 vs 文件持久化）
3. 多个 session 隔离
4. session 操作（get_items, add_items, pop_item, clear_session）
5. 不同 agent 共享同一 session
6. Session 与手动 to_input_list() 的对比
"""

import asyncio
from pathlib import Path
from typing import Annotated

from openai import AsyncOpenAI
from agents import (
    Agent,
    ModelSettings,
    Runner,
    SQLiteSession,
    function_tool,
    set_tracing_disabled,
)
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

MODEL = "deepseek-v4-pro"
BASE_URL = "https://copilot.huya.info/api/openai/v1"
API_KEY = "sk-hvtAUe3lPjYQtwiZqLMfYg"

set_tracing_disabled(True)


def make_model() -> OpenAIChatCompletionsModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIChatCompletionsModel(model=MODEL, openai_client=client)


@function_tool
def get_campaign_info(campaign_id: Annotated[str, "活动 ID"]) -> str:
    """查询活动信息。"""
    return f"活动 {campaign_id}：预算=5000元，状态=运行中，ROI=3.2。"


def print_section(title: str) -> None:
    """打印章节标题。"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


async def test_basic_multi_turn() -> None:
    """场景1：基础多轮对话（自动保持上下文）。"""
    print_section("场景1：基础多轮对话（Session 自动保持上下文）")

    agent = Agent(
        name="Assistant",
        instructions="你是助手，回答简洁。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    # 使用内存 SQLiteSession
    session = SQLiteSession("conversation_123")

    print("【第1轮】")
    print("用户: 金门大桥在哪个城市？\n")
    result = await Runner.run(agent, "金门大桥在哪个城市？", session=session)
    print(f"助手: {result.final_output}\n")

    print("【第2轮】（agent 自动记住上下文）")
    print("用户: 它在哪个州？\n")
    result = await Runner.run(agent, "它在哪个州？", session=session)
    print(f"助手: {result.final_output}\n")

    print("【第3轮】")
    print("用户: 那个州的人口是多少？\n")
    result = await Runner.run(agent, "那个州的人口是多少？", session=session)
    print(f"助手: {result.final_output}\n")

    print("✅ 注意：每轮都没有手动传递 to_input_list()，Session 自动管理历史")


async def test_memory_vs_file_session() -> None:
    """场景2：内存 Session vs 文件 Session。"""
    print_section("场景2：内存 Session vs 文件 Session")

    agent = Agent(
        name="Assistant",
        instructions="你是助手。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    # 内存 Session（进程结束后丢失）
    print("【内存 Session】")
    session_memory = SQLiteSession("user_001")
    result = await Runner.run(agent, "你好，我叫张三", session=session_memory)
    print(f"助手: {result.final_output}")
    
    result = await Runner.run(agent, "我叫什么名字？", session=session_memory)
    print(f"助手: {result.final_output}")
    print("说明: 内存 Session 在当前进程有效，但重启后丢失\n")

    # 文件 Session（持久化）
    print("【文件 Session】")
    db_path = Path("drafts/260702/conversations.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    session_file = SQLiteSession("user_002", str(db_path))
    result = await Runner.run(agent, "你好，我是李四", session=session_file)
    print(f"助手: {result.final_output}")
    
    result = await Runner.run(agent, "记住，我喜欢篮球", session=session_file)
    print(f"助手: {result.final_output}")
    
    print(f"说明: 文件 Session 保存到 {db_path}，进程重启后仍然可用")


async def test_multiple_sessions() -> None:
    """场景3：多个 Session 隔离。"""
    print_section("场景3：多个 Session 隔离")

    agent = Agent(
        name="Assistant",
        instructions="你是助手。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    db_path = Path("drafts/260702/multi_sessions.db")
    
    # 两个不同的用户 session
    session_user1 = SQLiteSession("user_alice", str(db_path))
    session_user2 = SQLiteSession("user_bob", str(db_path))

    print("【用户 Alice 的对话】")
    result = await Runner.run(agent, "你好，我喜欢足球", session=session_user1)
    print(f"助手: {result.final_output}\n")

    print("【用户 Bob 的对话】")
    result = await Runner.run(agent, "你好，我喜欢游泳", session=session_user2)
    print(f"助手: {result.final_output}\n")

    print("【Alice 继续对话】")
    result = await Runner.run(agent, "我刚才说我喜欢什么？", session=session_user1)
    print(f"助手: {result.final_output}\n")

    print("【Bob 继续对话】")
    result = await Runner.run(agent, "我刚才说我喜欢什么？", session=session_user2)
    print(f"助手: {result.final_output}\n")

    print("✅ 两个 Session 完全隔离，互不干扰")


async def test_session_operations() -> None:
    """场景4：Session 操作（get_items, add_items, pop_item, clear_session）。"""
    print_section("场景4：Session 操作")

    agent = Agent(
        name="Assistant",
        instructions="你是助手。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    session = SQLiteSession("operations_test")

    # 初始对话
    print("【初始对话】")
    await Runner.run(agent, "你好", session=session)
    await Runner.run(agent, "今天天气不错", session=session)

    # get_items
    print("\n【get_items】")
    items = await session.get_items()
    print(f"Session 中有 {len(items)} 条记录")
    for i, item in enumerate(items[:3], 1):
        role = item.get("role") if isinstance(item, dict) else getattr(item, "role", "unknown")
        print(f"  {i}. role={role}")

    # add_items
    print("\n【add_items】")
    new_items = [
        {"role": "user", "content": "手动添加的消息"},
    ]
    await session.add_items(new_items)
    items = await session.get_items()
    print(f"添加后有 {len(items)} 条记录")

    # pop_item
    print("\n【pop_item】")
    last_item = await session.pop_item()
    role = last_item.get("role") if isinstance(last_item, dict) else getattr(last_item, "role", "unknown")
    print(f"弹出最后一条: role={role}")
    items = await session.get_items()
    print(f"弹出后有 {len(items)} 条记录")

    # clear_session
    print("\n【clear_session】")
    await session.clear_session()
    items = await session.get_items()
    print(f"清空后有 {len(items)} 条记录")


async def test_shared_session() -> None:
    """场景5：不同 Agent 共享同一 Session。"""
    print_section("场景5：不同 Agent 共享同一 Session")

    support_agent = Agent(
        name="Support Agent",
        instructions="你是客服，帮助用户解决问题。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    billing_agent = Agent(
        name="Billing Agent",
        instructions="你是财务，处理账单问题。",
        model=make_model(),
        tools=[get_campaign_info],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    # 共享 session
    session = SQLiteSession("shared_conversation")

    print("【客服 Agent】")
    print("用户: 我的活动 C001 怎么样了？\n")
    result = await Runner.run(support_agent, "我的活动 C001 怎么样了？", session=session)
    print(f"Support Agent: {result.final_output}\n")

    print("【财务 Agent（看到之前的对话）】")
    print("用户: 它的预算是多少？\n")
    result = await Runner.run(billing_agent, "它的预算是多少？", session=session)
    print(f"Billing Agent: {result.final_output}\n")

    print("✅ 两个不同的 Agent 共享同一个 Session，都能看到完整历史")


async def test_session_vs_manual() -> None:
    """场景6：Session vs 手动 to_input_list() 对比。"""
    print_section("场景6：Session vs 手动 to_input_list() 对比")

    agent = Agent(
        name="Assistant",
        instructions="你是助手。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("【方式1：手动管理历史】")
    print("第1轮:")
    result1 = await Runner.run(agent, "你好，我叫王五")
    print(f"助手: {result1.final_output}")

    print("\n第2轮（手动传递历史）:")
    history = result1.to_input_list()
    result2 = await Runner.run(agent, history + [{"role": "user", "content": "我叫什么名字？"}])
    print(f"助手: {result2.final_output}")
    print("需要手动调用 to_input_list() 并拼接输入\n")

    print("【方式2：Session 自动管理】")
    session = SQLiteSession("auto_managed")
    
    print("第1轮:")
    result1 = await Runner.run(agent, "你好，我叫赵六", session=session)
    print(f"助手: {result1.final_output}")

    print("\n第2轮（Session 自动处理历史）:")
    result2 = await Runner.run(agent, "我叫什么名字？", session=session)
    print(f"助手: {result2.final_output}")
    print("不需要手动管理，Session 自动保存和加载历史")


async def test_pop_item_correction() -> None:
    """场景7：使用 pop_item 进行更正。"""
    print_section("场景7：使用 pop_item 进行更正")

    agent = Agent(
        name="Assistant",
        instructions="你是助手。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    session = SQLiteSession("correction_example")

    print("【初始对话】")
    print("用户: 2 + 2 等于多少？")
    result = await Runner.run(agent, "2 + 2 等于多少？", session=session)
    print(f"助手: {result.final_output}\n")

    print("【用户想更正问题】")
    print("撤销助手回答和用户问题...")
    await session.pop_item()  # 移除助手回答
    await session.pop_item()  # 移除用户问题

    print("\n用户: 2 + 3 等于多少？（更正后的问题）")
    result = await Runner.run(agent, "2 + 3 等于多少？", session=session)
    print(f"助手: {result.final_output}\n")

    print("✅ 使用 pop_item 可以撤销和更正对话")


async def main() -> None:
    await test_basic_multi_turn()
    await test_memory_vs_file_session()
    await test_multiple_sessions()
    await test_session_operations()
    await test_shared_session()
    await test_session_vs_manual()
    await test_pop_item_correction()

    print("\n" + "=" * 80)
    print("所有场景调试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
