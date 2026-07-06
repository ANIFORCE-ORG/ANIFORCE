#!/usr/bin/env python3
# %%
"""系统调试人在回路（HITL）审批流程。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260702_08_hitl_approval_debug.py

验证点：
1. 基础审批流程（needs_approval=True）
2. 条件审批（动态判断是否需要审批）
3. interruptions 的结构
4. 批准后恢复运行，验证工具是否真正执行
5. 拒绝后模型收到的错误消息
6. 自定义拒绝消息
7. always_approve/always_reject 的持久性
8. 状态持久化（to_json/from_json）
9. 流式 + 审批
"""

import asyncio
import json
from pathlib import Path
from typing import Annotated

from openai import AsyncOpenAI
from agents import (
    Agent,
    ModelSettings,
    Runner,
    RunState,
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


@function_tool(needs_approval=True)
def delete_campaign(campaign_id: Annotated[str, "活动 ID"]) -> str:
    """删除投放活动（需要审批）。"""
    return f"活动 {campaign_id} 已删除。"


async def needs_approval_if_high_budget(_ctx, params, _call_id) -> bool:
    """预算超过 10000 才需要审批。"""
    budget = params.get("budget", 0)
    return budget > 10000


@function_tool(needs_approval=needs_approval_if_high_budget)
def update_campaign_budget(
    campaign_id: Annotated[str, "活动 ID"],
    budget: Annotated[int, "新预算"]
) -> str:
    """更新活动预算。"""
    return f"活动 {campaign_id} 预算已更新为 {budget} 元。"


@function_tool
def get_campaign_info(campaign_id: Annotated[str, "活动 ID"]) -> str:
    """查询活动信息（不需要审批）。"""
    return f"活动 {campaign_id}：状态=运行中，预算=5000 元。"


def print_section(title: str) -> None:
    """打印章节标题。"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


async def test_basic_approval() -> None:
    """场景1：基础审批流程。"""
    print_section("场景1：基础审批流程（needs_approval=True）")

    agent = Agent(
        name="Campaign Manager",
        instructions="你是活动管理助手。用户要求删除活动时调用工具。",
        model=make_model(),
        tools=[delete_campaign],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '删除活动 C001'\n")

    # 第一次运行：触发审批
    result = await Runner.run(agent, "删除活动 C001", max_turns=5)

    print("【第一次运行结果】")
    print(f"  final_output: {result.final_output}")
    print(f"  interruptions: {len(result.interruptions)} 个\n")

    if result.interruptions:
        print("【待审批项详情】")
        for i, item in enumerate(result.interruptions, 1):
            print(f"  {i}. type: {item.type}")
            print(f"     tool_name: {item.tool_name}")
            print(f"     arguments: {item.arguments}")
            print(f"     call_id: {item.call_id}")
            print()

        # 批准并恢复
        print("【批准并恢复运行】\n")
        state = result.to_state()
        for item in result.interruptions:
            print(f"  批准: {item.tool_name}({item.arguments})")
            state.approve(item)

        result = await Runner.run(agent, state)

        print(f"\n[恢复后结果]")
        print(f"  final_output: {result.final_output}")
        print(f"  interruptions: {len(result.interruptions)} 个")


async def test_conditional_approval() -> None:
    """场景2：条件审批。"""
    print_section("场景2：条件审批（动态判断）")

    agent = Agent(
        name="Budget Manager",
        instructions="你是预算管理助手。用户要求修改预算时调用工具。",
        model=make_model(),
        tools=[update_campaign_budget],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    # 测试1：低预算（不需要审批）
    print("【测试1：更新预算到 5000（不需要审批）】\n")
    result = await Runner.run(agent, "把活动 C001 的预算改成 5000", max_turns=5)
    print(f"  interruptions: {len(result.interruptions)} 个")
    print(f"  final_output: {result.final_output}\n")

    # 测试2：高预算（需要审批）
    print("【测试2：更新预算到 50000（需要审批）】\n")
    result = await Runner.run(agent, "把活动 C001 的预算改成 50000", max_turns=5)
    print(f"  interruptions: {len(result.interruptions)} 个")

    if result.interruptions:
        print(f"  触发审批: {result.interruptions[0].tool_name}")
        print(f"  参数: {result.interruptions[0].arguments}")


async def test_rejection() -> None:
    """场景3：拒绝审批。"""
    print_section("场景3：拒绝审批")

    agent = Agent(
        name="Campaign Manager",
        instructions="你是活动管理助手。",
        model=make_model(),
        tools=[delete_campaign],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '删除活动 C001'\n")

    result = await Runner.run(agent, "删除活动 C001", max_turns=5)

    if result.interruptions:
        print("【拒绝审批】\n")
        state = result.to_state()
        for item in result.interruptions:
            print(f"  拒绝: {item.tool_name}({item.arguments})")
            state.reject(item)

        result = await Runner.run(agent, state)

        print(f"\n【拒绝后结果】")
        print(f"  final_output: {result.final_output}")


async def test_custom_rejection_message() -> None:
    """场景4：自定义拒绝消息。"""
    print_section("场景4：自定义拒绝消息")

    agent = Agent(
        name="Campaign Manager",
        instructions="你是活动管理助手。",
        model=make_model(),
        tools=[delete_campaign],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '删除活动 C001'\n")

    result = await Runner.run(agent, "删除活动 C001", max_turns=5)

    if result.interruptions:
        print("【拒绝并提供自定义消息】\n")
        state = result.to_state()
        for item in result.interruptions:
            custom_message = "操作被管理员拒绝：该活动正在投放中，不能删除。"
            print(f"  拒绝: {item.tool_name}")
            print(f"  自定义消息: {custom_message}\n")
            state.reject(item, rejection_message=custom_message)

        result = await Runner.run(agent, state)

        print(f"【拒绝后结果】")
        print(f"  final_output: {result.final_output}")


async def test_state_serialization() -> None:
    """场景5：状态持久化。"""
    print_section("场景5：状态持久化（to_json/from_json）")

    agent = Agent(
        name="Campaign Manager",
        instructions="你是活动管理助手。",
        model=make_model(),
        tools=[delete_campaign],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '删除活动 C001'\n")

    result = await Runner.run(agent, "删除活动 C001", max_turns=5)

    if result.interruptions:
        # 保存状态
        state = result.to_state()
        state_json = state.to_json()
        
        state_path = Path("drafts/260702/pending_approval.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state_json, ensure_ascii=False, indent=2))

        print(f"【状态已保存】")
        print(f"  路径: {state_path}")
        print(f"  大小: {len(json.dumps(state_json))} 字节\n")

        # 加载状态
        print("【加载状态并批准】\n")
        stored = json.loads(state_path.read_text())
        loaded_state = await RunState.from_json(agent, stored)

        for item in result.interruptions:
            print(f"  批准: {item.tool_name}")
            loaded_state.approve(item)

        result = await Runner.run(agent, loaded_state)

        print(f"\n【恢复后结果】")
        print(f"  final_output: {result.final_output}")


async def test_always_approve() -> None:
    """场景6：always_approve 持久性。"""
    print_section("场景6：always_approve 持久性")

    agent = Agent(
        name="Campaign Manager",
        instructions="你是活动管理助手。",
        model=make_model(),
        tools=[delete_campaign, get_campaign_info],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '删除活动 C001，然后删除活动 C002'\n")

    # 第一次运行
    result = await Runner.run(agent, "删除活动 C001，然后删除活动 C002", max_turns=10)

    print(f"【第一次暂停】")
    print(f"  interruptions: {len(result.interruptions)} 个")

    if result.interruptions:
        state = result.to_state()
        for item in result.interruptions:
            print(f"  批准（always_approve=True）: {item.tool_name}")
            state.approve(item, always_approve=True)

        # 恢复运行
        result = await Runner.run(agent, state)

        print(f"\n【恢复后】")
        print(f"  interruptions: {len(result.interruptions)} 个")
        print(f"  说明: 第二次调用同一工具自动批准，无需再次暂停")
        print(f"  final_output: {result.final_output[:100]}...")


async def test_streaming_with_approval() -> None:
    """场景7：流式 + 审批。"""
    print_section("场景7：流式传输 + 审批")

    agent = Agent(
        name="Campaign Manager",
        instructions="你是活动管理助手。",
        model=make_model(),
        tools=[delete_campaign],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '删除活动 C001'\n")

    # 流式运行
    result = Runner.run_streamed(agent, "删除活动 C001", max_turns=5)

    print("【消费流式事件】\n")
    event_count = 0
    async for event in result.stream_events():
        event_count += 1
        if event.type == "run_item_stream_event":
            print(f"  事件: {event.name}")

    print(f"\n流式事件总数: {event_count}")
    print(f"interruptions: {len(result.interruptions)} 个\n")

    if result.interruptions:
        print("【批准并恢复流式运行】\n")
        state = result.to_state()
        for item in result.interruptions:
            state.approve(item)

        result = Runner.run_streamed(agent, state)

        event_count = 0
        async for event in result.stream_events():
            event_count += 1

        print(f"恢复后流式事件总数: {event_count}")
        print(f"final_output: {result.final_output}")


async def main() -> None:
    await test_basic_approval()
    await test_conditional_approval()
    await test_rejection()
    await test_custom_rejection_message()
    await test_state_serialization()
    await test_always_approve()
    await test_streaming_with_approval()

    print("\n" + "=" * 80)
    print("所有场景调试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
