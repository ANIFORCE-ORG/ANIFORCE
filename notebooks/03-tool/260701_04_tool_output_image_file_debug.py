#!/usr/bin/env python3
# %%
"""调试工具返回图像或文件：ANIFORCE 场景。

场景：
  - 返回素材缩略图（图像）
  - 返回投放报告文件
  - 自定义 FunctionTool

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/03-runtime/260701_04_tool_output_image_file_debug.py
"""

import asyncio
import base64
from typing import Annotated

from openai import AsyncOpenAI
from agents import Agent, ModelSettings, Runner, RunContextWrapper, FunctionTool, function_tool
from agents.models.openai_responses import OpenAIResponsesModel
from agents.tool import ToolOutputImage, ToolOutputFileContent
from pydantic import BaseModel

MODEL = "gpt-5.3-codex"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"


# === 方式 1：@function_tool 返回图像 ===

@function_tool                                                                                                                          
def get_material_thumbnail(                                                                                                             
    material_id: Annotated[str, "素材 ID"],                                                                                             
) -> ToolOutputImage:                                                                                                                   
    """获取素材缩略图。"""                                                                                                              
    red_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="                 
    return ToolOutputImage(
        image_url=f"data:image/png;base64,{red_png_base64}",
        detail="low",
    )                                                                                                                                   
                                                                                                                                        
                                                                                                                                        
@function_tool                                                                                                                          
def download_campaign_report(                                                                                                           
    project_id: Annotated[str, "项目 ID"],                                                                                              
) -> ToolOutputFileContent:                                                                                                             
    """下载投放报告文件。"""                                                                                                            
    report_content = f"# {project_id} 投放报告\n\n- CTR: 2.5%\n- ROI: 3.2\n"                                                            
    report_base64 = base64.b64encode(report_content.encode("utf-8")).decode("utf-8")
    return ToolOutputFileContent(
        filename=f"{project_id}_report.md",
        # Responses API 需要 data URL 格式，不是裸 base64。
        file_data=f"data:text/plain;base64,{report_base64}",
    )                                  


# === 方式 3：自定义 FunctionTool ===

class AnalyzeArgs(BaseModel):
    project_id: str
    date_range: str


async def run_custom_analyze(ctx: RunContextWrapper, args: str) -> str:
    parsed = AnalyzeArgs.model_validate_json(args)
    return f"[custom_analyze] 项目 {parsed.project_id} 在 {parsed.date_range} 的分析完成"


custom_tool = FunctionTool(
    name="custom_analyze",
    description="自定义分析工具：深度分析项目数据",
    params_json_schema=AnalyzeArgs.model_json_schema(),
    on_invoke_tool=run_custom_analyze,
)


# === 调试主逻辑 ===

async def main():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    model = OpenAIResponsesModel(model=MODEL, openai_client=client)

    agent = Agent(
        name="ANIFORCE Material Assistant",
        instructions="你是 ANIFORCE 助手，可以获取素材缩略图、下载报告、执行分析。",
        model=model,
        tools=[
            get_material_thumbnail,
            download_campaign_report,
            custom_tool,
        ],
        model_settings=ModelSettings(
            parallel_tool_calls=False,
            truncation="auto",
            store=False,
        ),
    )

    prompt = "帮我获取素材 M001 的缩略图，然后下载项目 P001 的报告"

    result = await Runner.run(agent, prompt, max_turns=5)

    print("\n" + "=" * 80)
    print("调试输出：result.new_items")
    print("=" * 80 + "\n")

    for item in result.new_items:
        print(f"type: {item.type}")
        if hasattr(item, "output"):
            print(f"output: {item.output[:200] if isinstance(item.output, str) else item.output}")
        print("\n" + "-" * 80 + "\n")

    print("\n" + "=" * 80)
    print("最终回答：")
    print("=" * 80 + "\n")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
