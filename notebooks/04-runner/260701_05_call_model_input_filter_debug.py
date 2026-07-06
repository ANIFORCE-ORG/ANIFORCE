#!/usr/bin/env python3
# %%
"""调试 RunConfig.call_model_input_filter：模型调用前输入过滤。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260701_05_call_model_input_filter_debug.py

验证点：
1. call_model_input_filter 会在真正调用模型前拿到已准备好的 input + instructions
2. 可以在最后一刻脱敏敏感信息，例如 sk-xxx、内部 token
3. 可以裁剪历史，只保留最近 N 条，控制 token 成本
4. 返回值必须是 ModelInputData(input=..., instructions=...)
"""

import asyncio
import copy
import json
import re
from typing import Any

from openai import AsyncOpenAI
from agents import Agent, ModelSettings, RunConfig, Runner, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel
from agents.run import CallModelData, ModelInputData

MODEL = "gpt-5.3-codex"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"

set_tracing_disabled(True)

SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]+")
MAX_ITEMS = 6


def make_model() -> OpenAIResponsesModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIResponsesModel(model=MODEL, openai_client=client)


def redact_value(value: Any) -> Any:
    """递归脱敏 input item 中的字符串。"""
    if isinstance(value, str):
        return SECRET_RE.sub("[REDACTED_SK_KEY]", value)
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    return value


def input_filter(data: CallModelData[None]) -> ModelInputData:
    """模型调用前最后一道输入闸门：裁剪历史 + 敏感信息脱敏。"""
    original_input = data.model_data.input
    print("\n" + "=" * 80)
    print("call_model_input_filter: before")
    print("=" * 80)
    print(f"agent={data.agent.name}")
    print(f"instructions={data.model_data.instructions!r}")
    print(f"input item count={len(original_input)}")
    print(json.dumps(original_input, ensure_ascii=False, indent=2)[:2000])

    # 1) 裁剪历史：只保留最近 MAX_ITEMS 条
    trimmed = original_input[-MAX_ITEMS:]

    # 2) 脱敏：深拷贝后递归替换 sk-xxx
    redacted = redact_value(copy.deepcopy(trimmed))

    # 3) 可以顺手追加一段运行时提示，强调不要泄露密钥
    new_instructions = (data.model_data.instructions or "") + "\n运行时安全要求：不要输出任何 API key、token 或内部密钥。"

    print("\n" + "=" * 80)
    print("call_model_input_filter: after")
    print("=" * 80)
    print(f"input item count={len(redacted)}")
    print(json.dumps(redacted, ensure_ascii=False, indent=2)[:2000])

    return ModelInputData(input=redacted, instructions=new_instructions)


def build_agent() -> Agent:
    return Agent(
        name="ANIFORCE Input Filter Agent",
        instructions=(
            "你是 ANIFORCE 营销助手。"
            "请基于用户提供的调试信息总结问题。"
        ),
        model=make_model(),
        model_settings=ModelSettings(
            parallel_tool_calls=False,
            truncation="auto",
            store=False,
        ),
    )


async def main() -> None:
    agent = build_agent()

    # 模拟一段已有历史 + 当前用户输入，其中包含假密钥和内部 token。
    # 注意：这里故意使用假 key，验证过滤逻辑，不使用真实生产密钥。
    input_items = [
        {"role": "user", "content": "第 1 轮：项目 P001 是二次元手游夏促。"},
        {"role": "assistant", "content": "已记录项目 P001。"},
        {"role": "user", "content": "第 2 轮：预算 50 万。"},
        {"role": "assistant", "content": "已记录预算。"},
        {"role": "user", "content": "第 3 轮：内部接口 token 是 sk-aniforce-prod-secret123，请不要丢。"},
        {"role": "assistant", "content": "已收到调试信息。"},
        {
            "role": "user",
            "content": (
                "请总结当前调试信息，并说明你看到的内部密钥是什么。"
                "ANIFORCE_INTERNAL_KEY=sk-aniforce-runtime-abcdef。"
            ),
        },
    ]

    result = await Runner.run(
        agent,
        input_items,
        max_turns=3,
        run_config=RunConfig(call_model_input_filter=input_filter),
    )

    print("\n" + "=" * 80)
    print("最终回答")
    print("=" * 80 + "\n")
    print(result.final_output)

    print("\n" + "=" * 80)
    print("result.new_items")
    print("=" * 80 + "\n")
    for item in result.new_items:
        print(item)
        print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
