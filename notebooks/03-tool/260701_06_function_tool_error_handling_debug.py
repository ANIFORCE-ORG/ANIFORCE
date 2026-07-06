#!/usr/bin/env python3
# %%
"""调试函数工具错误处理：ANIFORCE 场景。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/03-runtime/260701_06_function_tool_error_handling_debug.py
"""

import asyncio
from typing import Any, Annotated

from openai import AsyncOpenAI
from agents import Agent, ModelSettings, Runner, RunContextWrapper, function_tool, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel

MODEL = "gpt-5.3-codex"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"

set_tracing_disabled(True)


# === 1. 默认错误处理：default_tool_error_function ===

@function_tool
def flaky_meta_query(campaign_id: Annotated[str, "广告系列 ID"]) -> str:
    """查询 Meta 广告数据。可能抛异常。"""
    if campaign_id == "C001":
        return "广告系列 C001: 花费 $5000, ROI 2.8"
    raise ValueError(f"Meta API 返回错误: campaign_id={campaign_id} 不存在")


# === 2. 自定义错误函数：记录日志 + 友好提示 ===

def custom_error_handler(context: RunContextWrapper[Any], error: Exception) -> str:
    """自定义错误处理：记录日志，返回用户友好提示。"""
    print(f"[ERROR_LOG] 工具调用失败: {error}")
    return "内部服务暂时不可用，请稍后重试或联系技术支持。"


@function_tool(failure_error_function=custom_error_handler)
def flaky_material_upload(material_id: Annotated[str, "素材 ID"]) -> str:
    """上传素材到 OSS。可能失败。"""
    if material_id == "M001":
        return f"素材 {material_id} 上传成功"
    raise RuntimeError(f"OSS 上传失败: 素材 {material_id} 格式错误")


# === 3. None：错误直接抛出，由业务层处理 ===

@function_tool(failure_error_function=None)
def critical_publish_ad(ad_id: Annotated[str, "广告 ID"]) -> str:
    """发布广告（关键操作）。失败后直接抛异常。"""
    if ad_id == "AD001":
        return f"广告 {ad_id} 发布成功"
    raise PermissionError(f"权限不足：无法发布广告 {ad_id}")


async def main():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    model = OpenAIResponsesModel(model=MODEL, openai_client=client)

    # 1. 默认错误处理：模型看到通用错误信息
    print("=== 1. 默认错误处理 ===\n")
    default_agent = Agent(
        name="ANIFORCE Default Error Agent",
        instructions="你是 ANIFORCE 助手。工具失败时，告诉用户并给建议。",
        model=model,
        tools=[flaky_meta_query],
        model_settings=ModelSettings(parallel_tool_calls=False, truncation="auto", store=False),
    )
    result = await Runner.run(default_agent, "查询广告系列 C999 的数据", max_turns=3)
    print(f"最终回答: {result.final_output}\n")

    # 2. 自定义错误处理：记录日志 + 友好提示
    print("=== 2. 自定义错误处理 ===\n")
    custom_agent = Agent(
        name="ANIFORCE Custom Error Agent",
        instructions="你是 ANIFORCE 助手。工具失败时，告诉用户并给建议。",
        model=model,
        tools=[flaky_material_upload],
        model_settings=ModelSettings(parallel_tool_calls=False, truncation="auto", store=False),
    )
    result = await Runner.run(custom_agent, "上传素材 M999", max_turns=3)
    print(f"最终回答: {result.final_output}\n")

    # 3. None：错误直接抛出
    print("=== 3. 错误直接抛出 ===\n")
    critical_agent = Agent(
        name="ANIFORCE Critical Fail Agent",
        instructions="你是 ANIFORCE 助手。发布广告是关键操作。",
        model=model,
        tools=[critical_publish_ad],
        model_settings=ModelSettings(parallel_tool_calls=False, truncation="auto", store=False),
    )
    try:
        await Runner.run(critical_agent, "发布广告 AD999", max_turns=3)
    except PermissionError as e:
        print(f"捕获 PermissionError: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
