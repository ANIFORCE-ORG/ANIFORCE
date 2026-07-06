#!/usr/bin/env python3
# %%
"""调试流式传输的高级场景：审批、取消、完整状态。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260702_05_streaming_advanced_debug.py

验证点：
1. 流式传输与工具审批（Human-in-the-loop）
2. 流式取消（立即 vs 当前轮次完成后）
3. 流式完成后的状态（result.is_complete）
4. ItemHelpers.text_message_output() 辅助函数
"""

import asyncio
import time
from typing import Annotated

from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent
from agents import (
    Agent,
    ModelSettings,
    Runner,
    function_tool,
    set_tracing_disabled,
    ItemHelpers,
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
def get_material_metrics(material_id: Annotated[str, "素材 ID"]) -> str:
    """查询素材投放指标。"""
    return f"素材 {material_id}：CTR=2.8%，CVR=8.1%，ROI=3.4。"


@function_tool(needs_approval=True)
def delete_campaign(campaign_id: Annotated[str, "活动 ID"]) -> str:
    """删除投放活动（需要审批）。"""
    return f"活动 {campaign_id} 已删除。"


@function_tool(needs_approval=True)
def publish_campaign(campaign_id: Annotated[str, "活动 ID"]) -> str:
    """发布投放活动（需要审批）。"""
    return f"活动 {campaign_id} 已发布。"


async def test_streaming_with_approval() -> None:
    """场景1：流式传输 + 工具审批。"""
    print("\n" + "=" * 80)
    print("场景1：流式传输 + 工具审批（Human-in-the-loop）")
    print("=" * 80 + "\n")

    agent = Agent(
        name="Campaign Manager",
        instructions="你是活动管理助手。如果用户要删除活动，调用 delete_campaign 工具。",
        model=make_model(),
        tools=[delete_campaign],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '删除活动 C001'\n")

    result = Runner.run_streamed(agent, "删除活动 C001", max_turns=5)

    print("【阶段1：流式消费到审批点】\n")
    event_count = 0
    async for event in result.stream_events():
        event_count += 1
        if event.type == "run_item_stream_event":
            if event.name == "tool_called":
                raw_item = event.item.raw_item
                tool_name = getattr(raw_item, "name", None)
                tool_args = getattr(raw_item, "arguments", None)
                print(f"  [{event_count}] 工具调用请求: {tool_name}({tool_args})")

    print(f"\n流式结束，共 {event_count} 个事件\n")
    print(f"result.is_complete: {result.is_complete}")
    print(f"result.interruptions: {result.interruptions}")

    if result.interruptions:
        print(f"\n发现 {len(result.interruptions)} 个待审批项：")
        for i, interruption in enumerate(result.interruptions, 1):
            print(f"  {i}. type={interruption.type}")
            print(f"     tool_name={interruption.tool_name}")
            print(f"     arguments={interruption.arguments}")
            print(f"     call_id={interruption.call_id}")

        print("\n【阶段2：批准审批并恢复运行】\n")
        state = result.to_state()
        for interruption in result.interruptions:
            print(f"  批准工具调用: {interruption.tool_name}")
            state.approve(interruption)

        print("\n恢复流式运行...\n")
        result = Runner.run_streamed(agent, state)

        event_count = 0
        async for event in result.stream_events():
            event_count += 1
            if event.type == "run_item_stream_event":
                if event.name == "tool_output":
                    print(f"  [{event_count}] 工具返回: {event.item.output}")
                elif event.name == "message_output_created":
                    text = ItemHelpers.text_message_output(event.item)
                    print(f"  [{event_count}] 最终消息: {text[:100]}...")

        print(f"\n恢复后流式结束，共 {event_count} 个事件")
        print(f"result.is_complete: {result.is_complete}")
        print(f"result.final_output: {result.final_output[:100]}...")
    else:
        print("未发现待审批项（不符合预期）")


async def test_streaming_cancel_immediate() -> None:
    """场景2：立即取消流式传输。"""
    print("\n\n" + "=" * 80)
    print("场景2：立即取消流式传输")
    print("=" * 80 + "\n")

    agent = Agent(
        name="Simple Agent",
        instructions="你是助手，回答要详细。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '写一篇 1000 字的营销策略文章'\n")

    result = Runner.run_streamed(agent, "写一篇 1000 字的营销策略文章", max_turns=3)

    print("开始消费流式事件，收到 5 个 text delta 后立即取消...\n")

    delta_count = 0
    start_time = time.time()

    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            if event.data.delta:
                delta_count += 1
                print(f"  [delta {delta_count}] {event.data.delta[:30]}...")

                if delta_count >= 5:
                    elapsed = time.time() - start_time
                    print(f"\n收到 {delta_count} 个 delta，调用 result.cancel() 立即取消")
                    result.cancel()
                    print(f"取消请求已发出，耗时 {elapsed:.2f}s\n")
                    break

    print(f"流式循环退出")
    print(f"result.is_complete: {result.is_complete}")
    print(f"result.final_output: {result.final_output if result.final_output else '(无)'}")


async def test_streaming_cancel_after_turn() -> None:
    """场景3：当前轮次完成后取消。"""
    print("\n\n" + "=" * 80)
    print("场景3：当前轮次完成后取消（cancel(mode='after_turn')）")
    print("=" * 80 + "\n")

    agent = Agent(
        name="Multi-turn Agent",
        instructions="你是助手。先调用工具查询素材，然后给出详细分析。",
        model=make_model(),
        tools=[get_material_metrics],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '查询素材 M001 的指标并详细分析'\n")

    result = Runner.run_streamed(agent, "查询素材 M001 的指标并详细分析", max_turns=10)

    print("开始消费流式事件，工具调用后立即取消（但等当前轮次完成）...\n")

    tool_called = False
    event_count = 0

    async for event in result.stream_events():
        event_count += 1

        if event.type == "run_item_stream_event":
            if event.name == "tool_called":
                tool_called = True
                print(f"  [{event_count}] 检测到工具调用")
                print(f"  调用 result.cancel(mode='after_turn')，等当前轮次完成...")
                result.cancel(mode="after_turn")

            elif event.name == "tool_output":
                print(f"  [{event_count}] 工具返回: {event.item.output}")

            elif event.name == "message_output_created":
                text = ItemHelpers.text_message_output(event.item)
                print(f"  [{event_count}] 最终消息: {text[:80]}...")

    print(f"\n流式循环退出，共 {event_count} 个事件")
    print(f"result.is_complete: {result.is_complete}")
    print(f"已执行的 turns: {len(result.new_items) if hasattr(result, 'new_items') else '?'}")


async def test_item_helpers() -> None:
    """场景4：验证 ItemHelpers.text_message_output()。"""
    print("\n\n" + "=" * 80)
    print("场景4：ItemHelpers.text_message_output() 辅助函数")
    print("=" * 80 + "\n")

    agent = Agent(
        name="Simple Agent",
        instructions="你是助手，回答简洁。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '你好'\n")

    result = Runner.run_streamed(agent, "你好", max_turns=1)

    print("使用 ItemHelpers.text_message_output() 提取消息文本：\n")

    async for event in result.stream_events():
        if event.type == "run_item_stream_event" and event.name == "message_output_created":
            # 方式1：用 ItemHelpers
            text = ItemHelpers.text_message_output(event.item)
            print(f"  ItemHelpers.text_message_output(): {text!r}\n")

            # 方式2：手动提取
            raw_item = event.item.raw_item
            content = getattr(raw_item, "content", []) or []
            manual_text = "".join(getattr(part, "text", "") for part in content)
            print(f"  手动提取: {manual_text!r}\n")

            print(f"  两者一致: {text == manual_text}")

    print(f"\nresult.is_complete: {result.is_complete}")


async def main() -> None:
    await test_streaming_with_approval()
    await test_streaming_cancel_immediate()
    await test_streaming_cancel_after_turn()
    await test_item_helpers()

    print("\n\n" + "=" * 80)
    print("所有场景调试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
