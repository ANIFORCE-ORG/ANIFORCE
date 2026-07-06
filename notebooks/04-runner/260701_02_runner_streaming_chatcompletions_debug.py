#!/usr/bin/env python3
# %%
"""调试 Runner.run_streamed 流式输出：使用 OpenAIChatCompletionsModel + claude-sonnet-5。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260701_02_runner_streaming_chatcompletions_debug.py

验证点：
1. OpenAIChatCompletionsModel 可以使用 /v1/chat/completions 兼容接口
2. 使用 claude-sonnet-5 模型
3. Runner.run_streamed(): 返回 RunResultStreaming
4. stream_events(): 实时收到 raw_response_event / run_item_stream_event
5. 有工具调用时，流里能看到 tool_called / tool_output / message_output_created
6. 流结束后，仍然可以读取 result.final_output 和 result.new_items
"""

import asyncio
import time
from typing import Annotated

from openai import AsyncOpenAI
from agents import Agent, ModelSettings, Runner, function_tool, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel

MODEL = "gpt-5.4"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"

set_tracing_disabled(True)


def make_model() -> OpenAIResponsesModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIResponsesModel(model=MODEL, openai_client=client)


@function_tool
def get_material_metrics(material_id: Annotated[str, "素材 ID，例如 M001"]) -> str:
    """查询素材投放指标，包括 CTR、CVR、ROI 和消耗。"""
    data = {
        "M001": "素材 M001：CTR=2.8%，CVR=8.1%，ROI=3.4，消耗=12000 元。",
        "M002": "素材 M002：CTR=1.9%，CVR=5.6%，ROI=2.2，消耗=9000 元。",
    }
    return data.get(material_id, f"未找到素材 {material_id} 的投放指标")


@function_tool
def get_material_creative_brief(material_id: Annotated[str, "素材 ID，例如 M001"]) -> str:
    """查询素材创意简介，包括卖点、视觉风格和目标人群。"""
    data = {
        "M001": "素材 M001：核心卖点是限定角色，视觉风格为高饱和二次元战斗场景，目标人群是 18-28 岁手游用户。",
        "M002": "素材 M002：核心卖点是开服福利，视觉风格为礼包展示，目标人群是泛二次元用户。",
    }
    return data.get(material_id, f"未找到素材 {material_id} 的创意简介")


def build_agent() -> Agent:
    return Agent(
        name="ANIFORCE ChatCompletions Streaming Agent",
        instructions=(
            "你是 ANIFORCE 营销助手。"
            "涉及素材指标或创意简介时必须调用工具。"
            "回答要简洁，最后给出一个优化建议。"
        ),
        model=make_model(),
        tools=[get_material_metrics, get_material_creative_brief],
        model_settings=ModelSettings(
            parallel_tool_calls=False,
            store=False,
        ),
    )


def summarize_run_item(item) -> str:
    """压缩展示 run_item_stream_event，避免输出过长。"""
    item_type = getattr(item, "type", type(item).__name__)
    raw_item = getattr(item, "raw_item", None)
    output = getattr(item, "output", None)

    if item_type == "tool_call_item" and raw_item is not None:
        return f"{item_type}: tool={getattr(raw_item, 'name', None)}, args={getattr(raw_item, 'arguments', None)}"
    if item_type == "tool_call_output_item":
        return f"{item_type}: output={output}"
    if item_type == "message_output_item" and raw_item is not None:
        content = getattr(raw_item, "content", []) or []
        text = "".join(getattr(part, "text", "") for part in content)
        return f"{item_type}: text={text[:120]!r}..."
    return repr(item)


async def run_streamed_demo() -> None:
    agent = build_agent()
    result = Runner.run_streamed(
        agent,
        "分析素材 M001 的投放表现和创意特点，并给一个优化建议。",
        max_turns=5,
    )

    print("\n" + "=" * 80)
    print(f"流式事件：result.stream_events() [model={MODEL}]")
    print("=" * 80 + "\n")

    in_text_stream = False
    start_time = time.time()

    async for event in result.stream_events():
        elapsed = time.time() - start_time
        
        if event.type == "raw_response_event":
            raw_type = getattr(event.data, "type", "")

            if raw_type == "response.created":
                print(f"[{elapsed:.3f}s] [raw] response.created")

            elif raw_type == "response.output_text.delta":
                if not in_text_stream:
                    in_text_stream = True
                    print(f"\n[{elapsed:.3f}s] [raw text delta begin]")
                delta_content = getattr(event.data, 'delta', '')
                print(f"[{elapsed:.3f}s] [delta] {delta_content!r}", flush=True)

            elif raw_type == "response.completed":
                if in_text_stream:
                    print(f"\n[{elapsed:.3f}s] [raw text delta end]")
                    in_text_stream = False
                print(f"[{elapsed:.3f}s] [raw] response.completed")

        elif event.type == "run_item_stream_event":
            if in_text_stream:
                print(f"\n[{elapsed:.3f}s] [raw text delta paused]")
                in_text_stream = False
            print(f"\n[{elapsed:.3f}s] [run_item] name={event.name}")
            print(summarize_run_item(event.item))
            print("-" * 80)

        elif event.type == "agent_updated_stream_event":
            print(f"\n[{elapsed:.3f}s] [agent_updated] new_agent={event.new_agent.name}")
            print("-" * 80)

        else:
            print(f"[{elapsed:.3f}s] [unknown_event] {event}")

    print("\n" + "=" * 80)
    print("流结束后的完整结果")
    print("=" * 80 + "\n")
    print("最终回答：", result.final_output)

    print("\n" + "=" * 80)
    print("流结束后的 result.new_items")
    print("=" * 80 + "\n")
    for item in result.new_items:
        print(item)
        print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_streamed_demo())
