#!/usr/bin/env python3
# %%
"""调试状态与对话管理：ANIFORCE 场景。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260701_04_conversation_state_debug.py

验证点：
1. 手动状态管理：result.to_input_list() + 新用户消息
2. 自动状态管理：SQLiteSession 自动保存和加载历史
3. 多轮追问中，第二轮用户只说“它”，Agent 仍能从历史里知道指 P001
4. 服务端托管状态 previous_response_id / conversation_id 本脚本先不调，tokenlab 兼容层不一定完整支持
"""

import asyncio
from pathlib import Path
from typing import Annotated

from openai import AsyncOpenAI
from agents import Agent, ModelSettings, Runner, SQLiteSession, function_tool, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel

MODEL = "gpt-5.3-codex"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"

SESSION_DB = Path("notebooks/04-runner/260701_04_conversation_state.sqlite3")

set_tracing_disabled(True)


def make_model() -> OpenAIResponsesModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIResponsesModel(model=MODEL, openai_client=client)


@function_tool
def get_project_summary(project_id: Annotated[str, "项目 ID，例如 P001"]) -> str:
    """查询项目摘要，包括目标、预算和状态。"""
    data = {
        "P001": "项目 P001：二次元手游夏促，目标提升预约转化，预算 50 万，状态：投放中。",
        "P002": "项目 P002：新游首发预约，目标提升点击率，预算 80 万，状态：素材测试中。",
    }
    return data.get(project_id, f"未找到项目 {project_id}")


@function_tool
def get_project_roi(project_id: Annotated[str, "项目 ID，例如 P001"]) -> str:
    """查询项目 ROI、CTR、CVR 数据。"""
    data = {
        "P001": "项目 P001：ROI=3.2，CTR=2.5%，CVR=7.8%，建议继续投放。",
        "P002": "项目 P002：ROI=2.1，CTR=3.1%，CVR=5.4%，建议继续素材测试。",
    }
    return data.get(project_id, f"未找到项目 {project_id} 的 ROI 数据")


def build_agent() -> Agent:
    return Agent(
        name="ANIFORCE Conversation State Agent",
        instructions=(
            "你是 ANIFORCE 营销助手。"
            "涉及项目摘要或 ROI 时必须调用工具。"
            "如果用户用‘它/这个项目/该项目’追问，要根据历史判断项目 ID。"
            "回答简洁，不要编造工具外的数据。"
        ),
        model=make_model(),
        tools=[get_project_summary, get_project_roi],
        model_settings=ModelSettings(
            parallel_tool_calls=False,
            truncation="auto",
            store=False,
        ),
    )


def summarize_items(title: str, result) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")
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
    print("最终回答：", result.final_output)


async def manual_to_input_list_demo() -> None:
    """手动状态管理：应用自己持有历史列表。"""
    agent = build_agent()

    print("\n" + "#" * 80)
    print("1. 手动状态管理：result.to_input_list()")
    print("#" * 80)

    first = await Runner.run(
        agent,
        "查询项目 P001 的摘要。",
        max_turns=5,
    )
    summarize_items("第一轮：查询 P001 摘要", first)

    next_input = first.to_input_list() + [
        {"role": "user", "content": "它的 ROI 怎么样？"}
    ]
    print(f"\n手动传入下一轮 input item 数量: {len(next_input)}")

    second = await Runner.run(
        agent,
        next_input,
        max_turns=5,
    )
    summarize_items("第二轮：只说‘它’，依赖 to_input_list 历史解析为 P001", second)


async def sqlite_session_demo() -> None:
    """自动状态管理：SDK session 自动加载/保存历史。"""
    agent = build_agent()

    print("\n" + "#" * 80)
    print("2. 自动状态管理：SQLiteSession")
    print("#" * 80)

    SESSION_DB.parent.mkdir(parents=True, exist_ok=True)
    if SESSION_DB.exists():
        SESSION_DB.unlink()

    session = SQLiteSession("conversation_state_debug_p001", db_path=SESSION_DB)
    try:
        first = await Runner.run(
            agent,
            "查询项目 P001 的摘要。",
            max_turns=5,
            session=session,
        )
        summarize_items("第一轮：session 保存 P001 摘要上下文", first)

        saved_after_first = await session.get_items()
        print(f"\nsession 第一轮后保存 item 数量: {len(saved_after_first)}")

        second = await Runner.run(
            agent,
            "它的 ROI 怎么样？",
            max_turns=5,
            session=session,
        )
        summarize_items("第二轮：只传新用户消息，session 自动补齐历史", second)

        saved_after_second = await session.get_items()
        print(f"\nsession 第二轮后保存 item 数量: {len(saved_after_second)}")
        print(f"session sqlite 文件: {SESSION_DB}")
    finally:
        session.close()


async def no_state_negative_demo() -> None:
    """负例：不传历史、不传 session 时，‘它’没有明确指代。"""
    agent = build_agent()

    print("\n" + "#" * 80)
    print("3. 负例：不传历史也不传 session")
    print("#" * 80)

    result = await Runner.run(
        agent,
        "它的 ROI 怎么样？",
        max_turns=3,
    )
    summarize_items("无历史追问：模型通常无法可靠知道‘它’是谁", result)


async def main() -> None:
    await manual_to_input_list_demo()
    await sqlite_session_demo()
    await no_state_negative_demo()


if __name__ == "__main__":
    asyncio.run(main())
