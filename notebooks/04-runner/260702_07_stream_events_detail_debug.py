#!/usr/bin/env python3
# %%
"""详细调试流式事件的数据结构和内容。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260702_07_stream_events_detail_debug.py

验证点：
1. agent_updated_stream_event 的数据结构
2. raw_response_event 的各种类型（response.created, delta, completed 等）
3. run_item_stream_event 的各种 name（tool_called, tool_output, message_output_created 等）
4. 每种事件的完整字段和内容
"""

import asyncio
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


def print_dict_structure(obj, indent=0, max_depth=3):
    """递归打印对象结构，限制深度避免过长。"""
    prefix = "  " * indent
    
    if indent > max_depth:
        print(f"{prefix}...")
        return
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)) and value:
                print(f"{prefix}{key}:")
                print_dict_structure(value, indent + 1, max_depth)
            else:
                value_str = str(value)[:60]
                print(f"{prefix}{key}: {value_str}")
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:3]):  # 只显示前3个
            print(f"{prefix}[{i}]:")
            print_dict_structure(item, indent + 1, max_depth)
        if len(obj) > 3:
            print(f"{prefix}... (共 {len(obj)} 项)")
    
    else:
        # 对象属性
        attrs = {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        if attrs:
            print_dict_structure(attrs, indent, max_depth)
        else:
            print(f"{prefix}{str(obj)[:60]}")


async def test_stream_events_detail() -> None:
    """详细展示每种流式事件的数据结构。"""
    
    agent = Agent(
        name="Material Agent",
        instructions="你是素材分析助手，调用工具获取数据。",
        model=make_model(),
        tools=[get_material_metrics],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    print("\n" + "=" * 80)
    print("流式事件详细结构")
    print("=" * 80 + "\n")
    
    print("用户输入: '查询素材 M001 的指标'\n")

    result = Runner.run_streamed(agent, "查询素材 M001 的指标", max_turns=3)

    # 统计各类事件
    event_stats = {}
    
    # 收集样例
    samples = {
        "agent_updated_stream_event": None,
        "raw_response_event": {
            "response.created": None,
            "response.output_item.added": None,
            "response.reasoning_text.delta": None,
            "response.output_text.delta": None,
            "response.content_part.added": None,
            "response.completed": None,
        },
        "run_item_stream_event": {
            "reasoning_item_created": None,
            "tool_called": None,
            "tool_output": None,
            "message_output_created": None,
        }
    }

    async for event in result.stream_events():
        event_type = event.type
        event_stats[event_type] = event_stats.get(event_type, 0) + 1
        
        # 收集样例
        if event_type == "agent_updated_stream_event":
            if samples["agent_updated_stream_event"] is None:
                samples["agent_updated_stream_event"] = event
        
        elif event_type == "raw_response_event":
            raw_type = getattr(event.data, "type", None)
            if raw_type and raw_type in samples["raw_response_event"]:
                if samples["raw_response_event"][raw_type] is None:
                    samples["raw_response_event"][raw_type] = event
        
        elif event_type == "run_item_stream_event":
            event_name = event.name
            if event_name in samples["run_item_stream_event"]:
                if samples["run_item_stream_event"][event_name] is None:
                    samples["run_item_stream_event"][event_name] = event

    # 打印统计
    print("\n【事件统计】\n")
    for event_type, count in sorted(event_stats.items()):
        print(f"  {event_type}: {count} 次")

    # 打印详细样例
    print("\n\n" + "=" * 80)
    print("各类事件的详细数据结构")
    print("=" * 80 + "\n")

    # 1. agent_updated_stream_event
    if samples["agent_updated_stream_event"]:
        print("\n【1. agent_updated_stream_event】\n")
        event = samples["agent_updated_stream_event"]
        print(f"事件类型: {event.type}")
        print(f"新 Agent 名称: {event.new_agent.name}")
        print(f"新 Agent 指令（前80字符）: {event.new_agent.instructions[:80]}...")
        print(f"新 Agent 工具数量: {len(event.new_agent.tools)}")
        print(f"\n完整属性:")
        print_dict_structure(event, indent=1, max_depth=2)

    # 2. raw_response_event
    print("\n\n【2. raw_response_event（各种子类型）】\n")
    
    for raw_type, event in samples["raw_response_event"].items():
        if event is None:
            continue
        
        print(f"\n  ▶ {raw_type}\n")
        print(f"    event.type: {event.type}")
        print(f"    event.data.type: {event.data.type}")
        
        if hasattr(event.data, 'delta'):
            delta = getattr(event.data, 'delta', None)
            print(f"    event.data.delta: {delta!r}")
        
        if hasattr(event.data, 'item'):
            item = event.data.item
            print(f"    event.data.item.type: {getattr(item, 'type', None)}")
        
        if hasattr(event.data, 'response'):
            resp = event.data.response
            print(f"    event.data.response.id: {getattr(resp, 'id', None)}")
        
        print(f"\n    完整 event.data 属性:")
        print_dict_structure(event.data, indent=2, max_depth=2)

    # 3. run_item_stream_event
    print("\n\n【3. run_item_stream_event（各种 name）】\n")
    
    for event_name, event in samples["run_item_stream_event"].items():
        if event is None:
            continue
        
        print(f"\n  ▶ {event_name}\n")
        print(f"    event.type: {event.type}")
        print(f"    event.name: {event.name}")
        print(f"    event.item.type: {event.item.type}")
        
        if event_name == "tool_called":
            print(f"    tool_name: {event.item.raw_item.name}")
            print(f"    arguments: {event.item.raw_item.arguments}")
            print(f"    call_id: {event.item.raw_item.call_id}")
        
        elif event_name == "tool_output":
            print(f"    output: {event.item.output[:80]}...")
        
        elif event_name == "message_output_created":
            content = event.item.raw_item.content or []
            text = "".join(getattr(part, "text", "") for part in content)
            print(f"    message text（前80字符）: {text[:80]}...")
        
        elif event_name == "reasoning_item_created":
            content = event.item.raw_item.content or []
            text = "".join(getattr(part, "text", "") for part in content)
            print(f"    reasoning text（前80字符）: {text[:80]}...")
        
        print(f"\n    完整 event.item 属性:")
        print_dict_structure(event.item, indent=2, max_depth=2)


async def main() -> None:
    await test_stream_events_detail()
    
    print("\n\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
