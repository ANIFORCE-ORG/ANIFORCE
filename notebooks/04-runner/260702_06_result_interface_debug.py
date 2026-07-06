#!/usr/bin/env python3
# %%
"""系统调试 Runner 结果接口：RunResult 和 RunResultStreaming。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260702_06_result_interface_debug.py

验证点：
1. to_input_list() 的两种模式（preserve_all vs normalized）
2. new_items 的完整结构（各种 Item 类型）
3. 流式生命周期（final_output、is_complete 的变化时机）
4. last_agent vs current_agent（任务转移时的区别）
5. raw_responses 和用量统计
6. input vs to_input_list() 的区别
"""

import asyncio
import json
from typing import Annotated

from openai import AsyncOpenAI
from agents import (
    Agent,
    ModelSettings,
    Runner,
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
def get_material_metrics(material_id: Annotated[str, "素材 ID"]) -> str:
    """查询素材投放指标。"""
    return f"素材 {material_id}：CTR=2.8%，CVR=8.1%，ROI=3.4。"


@function_tool
def analyze_creative(material_id: Annotated[str, "素材 ID"]) -> str:
    """分析素材创意。"""
    return f"素材 {material_id}：核心卖点是限定角色，视觉风格为高饱和战斗场景。"


def print_section(title: str) -> None:
    """打印章节标题。"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


async def test_to_input_list_modes() -> None:
    """场景1：to_input_list() 的两种模式。"""
    print_section("场景1：to_input_list() 的两种模式")

    agent = Agent(
        name="Material Agent",
        instructions="你是素材分析助手，调用工具获取数据。",
        model=make_model(),
        tools=[get_material_metrics, analyze_creative],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '查询素材 M001 的指标'\n")

    result = await Runner.run(agent, "查询素材 M001 的指标")

    print("【模式1：preserve_all（默认）】\n")
    input_list_default = result.to_input_list()
    print(f"条目数量: {len(input_list_default)}")
    for i, item in enumerate(input_list_default, 1):
        item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", type(item).__name__)
        role = item.get("role") if isinstance(item, dict) else getattr(item, "role", None)
        print(f"  {i}. type={item_type}, role={role}")

    print("\n【模式2：normalized】\n")
    input_list_normalized = result.to_input_list(mode="normalized")
    print(f"条目数量: {len(input_list_normalized)}")
    for i, item in enumerate(input_list_normalized, 1):
        item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", type(item).__name__)
        role = item.get("role") if isinstance(item, dict) else getattr(item, "role", None)
        print(f"  {i}. type={item_type}, role={role}")

    print(f"\n两种模式是否相同: {input_list_default == input_list_normalized}")


async def test_new_items_structure() -> None:
    """场景2：new_items 的完整结构。"""
    print_section("场景2：new_items 的完整结构")

    agent = Agent(
        name="Material Agent",
        instructions="你是素材分析助手，调用工具获取数据。",
        model=make_model(),
        tools=[get_material_metrics],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '查询素材 M001 的指标'\n")

    result = await Runner.run(agent, "查询素材 M001 的指标")

    print(f"new_items 数量: {len(result.new_items)}\n")

    for i, item in enumerate(result.new_items, 1):
        print(f"【Item {i}】")
        print(f"  type: {item.type}")
        
        if item.type == "message_output_item":
            print(f"  role: {item.raw_item.role}")
            content = item.raw_item.content or []
            text = "".join(getattr(part, "text", "") for part in content)
            print(f"  text: {text[:80]}...")
        
        elif item.type == "reasoning_item":
            content = item.raw_item.content or []
            text = "".join(getattr(part, "text", "") for part in content)
            print(f"  reasoning: {text[:80]}...")
        
        elif item.type == "tool_call_item":
            print(f"  tool_name: {item.raw_item.name}")
            print(f"  arguments: {item.raw_item.arguments}")
            print(f"  call_id: {item.raw_item.call_id}")
        
        elif item.type == "tool_call_output_item":
            print(f"  output: {item.output[:80]}...")
        
        print()


async def test_streaming_lifecycle() -> None:
    """场景3：流式生命周期（final_output、is_complete 的变化时机）。"""
    print_section("场景3：流式生命周期")

    agent = Agent(
        name="Simple Agent",
        instructions="你是助手，回答简洁。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '你好'\n")

    result = Runner.run_streamed(agent, "你好", max_turns=1)

    print("【流开始前】")
    print(f"  final_output: {result.final_output}")
    print(f"  is_complete: {result.is_complete}")
    print(f"  new_items: {len(result.new_items) if hasattr(result, 'new_items') else 'N/A'}")

    print("\n开始消费流式事件...\n")

    event_count = 0
    async for event in result.stream_events():
        event_count += 1
        if event_count <= 3:
            print(f"  事件 {event_count}: {event.type}")

    print(f"\n流式事件总数: {event_count}\n")

    print("【流结束后】")
    print(f"  final_output: {result.final_output[:50] if result.final_output else None}...")
    print(f"  is_complete: {result.is_complete}")
    print(f"  new_items: {len(result.new_items)}")


async def test_last_agent_vs_current_agent() -> None:
    """场景4：last_agent vs current_agent（流式运行中的区别）。"""
    print_section("场景4：last_agent vs current_agent")

    agent = Agent(
        name="Material Agent",
        instructions="你是素材分析助手。",
        model=make_model(),
        tools=[get_material_metrics],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '查询素材 M001 的指标'\n")

    # 非流式运行
    print("【非流式运行】")
    result = await Runner.run(agent, "查询素材 M001 的指标")
    print(f"  last_agent: {result.last_agent.name}")
    print(f"  有 current_agent 属性: {hasattr(result, 'current_agent')}")

    # 流式运行
    print("\n【流式运行】")
    result = Runner.run_streamed(agent, "查询素材 M001 的指标")
    
    print(f"  流开始前 current_agent: {result.current_agent.name}")
    
    async for event in result.stream_events():
        if event.type == "agent_updated_stream_event":
            print(f"  检测到 agent_updated: new_agent={event.new_agent.name}")
            print(f"  此时 current_agent: {result.current_agent.name}")

    print(f"  流结束后 last_agent: {result.last_agent.name}")
    print(f"  流结束后 current_agent: {result.current_agent.name}")


async def test_raw_responses_and_usage() -> None:
    """场景5：raw_responses 和用量统计。"""
    print_section("场景5：raw_responses 和用量统计")

    agent = Agent(
        name="Material Agent",
        instructions="你是素材分析助手，调用工具获取数据。",
        model=make_model(),
        tools=[get_material_metrics],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '查询素材 M001 的指标'\n")

    result = await Runner.run(agent, "查询素材 M001 的指标")

    print(f"【raw_responses】")
    print(f"  模型调用次数: {len(result.raw_responses)}\n")
    
    for i, resp in enumerate(result.raw_responses, 1):
        print(f"  调用 {i}:")
        print(f"    response_id: {resp.response_id}")
        print(f"    request_id: {resp.request_id}")
        if resp.usage:
            print(f"    usage: input={resp.usage.input_tokens}, output={resp.usage.output_tokens}")
        print()

    print(f"【总用量】")
    if hasattr(result, 'context_wrapper') and result.context_wrapper:
        usage = result.context_wrapper.usage
        print(f"  input_tokens: {usage.input_tokens if usage else 'N/A'}")
        print(f"  output_tokens: {usage.output_tokens if usage else 'N/A'}")
        print(f"  total_tokens: {usage.total_tokens if usage else 'N/A'}")
    else:
        print("  context_wrapper 不可用")


async def test_input_vs_to_input_list() -> None:
    """场景6：input vs to_input_list() 的区别。"""
    print_section("场景6：input vs to_input_list() 的区别")

    agent = Agent(
        name="Material Agent",
        instructions="你是素材分析助手。",
        model=make_model(),
        tools=[get_material_metrics],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("用户输入: '查询素材 M001 的指标'\n")

    result = await Runner.run(agent, "查询素材 M001 的指标")

    print("【result.input】")
    if isinstance(result.input, str):
        print(f"  类型: str")
        print(f"  内容: {result.input}")
    elif isinstance(result.input, list):
        print(f"  类型: list")
        print(f"  长度: {len(result.input)}")
        for i, item in enumerate(result.input[:3], 1):
            item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", "unknown")
            print(f"    {i}. type={item_type}")
    else:
        print(f"  类型: {type(result.input)}")

    print("\n【result.to_input_list()】")
    input_list = result.to_input_list()
    print(f"  类型: list")
    print(f"  长度: {len(input_list)}")
    for i, item in enumerate(input_list[:3], 1):
        item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", "unknown")
        print(f"    {i}. type={item_type}")

    print(f"\n【区别】")
    print(f"  input 是本次运行的基础输入（可能被过滤器重写）")
    print(f"  to_input_list() 是下一轮输入（包含本次运行的完整历史）")


async def main() -> None:
    await test_to_input_list_modes()
    await test_new_items_structure()
    await test_streaming_lifecycle()
    await test_last_agent_vs_current_agent()
    await test_raw_responses_and_usage()
    await test_input_vs_to_input_list()

    print("\n" + "=" * 80)
    print("所有场景调试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
