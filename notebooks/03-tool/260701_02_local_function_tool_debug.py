#!/usr/bin/env python3
# %%
"""调试本地运行时工具：以 ANIFORCE 营销平台场景为例。

场景：
  - fetch_project_brief: 读取项目简介（模拟从 backend/本地读取）
  - analyze_material_performance: 分析素材表现（模拟本地数据分析）
  - generate_campaign_report: 生成投放报告（模拟本地文件生成）

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/03-runtime/260701_02_local_function_tool_debug.py
"""

import asyncio
import json
import os
from typing import Annotated

from openai import AsyncOpenAI
from agents import Agent, ModelSettings, Runner, function_tool
from agents.models.openai_responses import OpenAIResponsesModel

MODEL = "gpt-5.3-codex"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"


# === 业务场景：本地运行时工具 ===

@function_tool
def fetch_project_brief(
    project_id: Annotated[str, "项目 ID，例如 P001"],
) -> str:
    """从 backend 或本地读取项目简介和营销目标。"""
    # 模拟从 backend API 或本地文件读取
    mock_data = {
        "P001": "游戏：传奇手游；目标：拉新；预算：10万美元/月；地区：北美",
        "P002": "游戏：卡牌 RPG；目标：ROI 优化；预算：5万美元/月；地区：日韩",
    }
    result = mock_data.get(project_id, f"项目 {project_id} 未找到")
    return f"[fetch_project_brief] {result}"


@function_tool
def analyze_material_performance(
    material_id: Annotated[str, "素材 ID，例如 M001"],
) -> str:
    """分析素材投放表现：CTR、转化率、花费等。"""
    # 模拟从本地或 backend metrics 读取
    mock_metrics = {
        "M001": "CTR: 2.3%, CVR: 1.8%, 花费: $1200, ROI: 3.5",
        "M002": "CTR: 1.9%, CVR: 1.2%, 花费: $800, ROI: 2.1",
    }
    result = mock_metrics.get(material_id, f"素材 {material_id} 无数据")
    return f"[analyze_material_performance] {result}"


@function_tool
def generate_campaign_report(
    project_id: Annotated[str, "项目 ID"],
    report_type: Annotated[str, "报告类型：daily/weekly/monthly"],
) -> str:
    """生成投放报告（模拟写入本地文件或返回报告链接）。"""
    # 模拟生成报告文件
    report_path = f"/tmp/aniforce_reports/{project_id}_{report_type}_report.md"
    return f"[generate_campaign_report] 报告已生成: {report_path}"


# === 调试主逻辑 ===

async def main():
    if not API_KEY:
        raise RuntimeError("请先设置 TOKENLAB_API_KEY 或 OPENAI_API_KEY")

    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=90.0,
        max_retries=0,
    )

    model = OpenAIResponsesModel(
        model=MODEL,
        openai_client=client,
    )

    agent = Agent(
        name="ANIFORCE Marketing Assistant",
        instructions=(
            "你是 ANIFORCE 游戏营销平台的助手。"
            "用户会问项目、素材、报告相关问题，你可以调用本地工具查询或生成。"
            "回答简洁、有条理。"
        ),
        model=model,
        tools=[
            fetch_project_brief,
            analyze_material_performance,
            generate_campaign_report,
        ],
        model_settings=ModelSettings(
            parallel_tool_calls=False,
            truncation="auto",
            store=False,
            prompt_cache_retention="24h",
        ),
    )

    prompt = "帮我查一下项目 P001 的简介，然后分析素材 M001 的表现"

    result = await Runner.run(agent, prompt, max_turns=5)

    print("\n" + "=" * 80)
    print("调试输出：result.new_items")
    print("=" * 80 + "\n")

    for item in result.new_items:
        print(item)
        print("\n" + "-" * 80 + "\n")

    print("\n" + "=" * 80)
    print("最终回答：")
    print("=" * 80 + "\n")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
