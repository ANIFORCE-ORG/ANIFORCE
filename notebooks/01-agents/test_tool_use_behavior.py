import asyncio
import os
from typing import Any

from agents import (
    Agent,
    FunctionToolResult,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunConfig,
    RunContextWrapper,
    Runner,
    StopAtTools,
    ToolsToFinalOutputResult,
    function_tool,
)
from openai import AsyncOpenAI


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("Please set DEEPSEEK_API_KEY before running this script.")

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

model = OpenAIChatCompletionsModel(
    model="deepseek-v4-pro",
    openai_client=client,
)


@function_tool
def get_weather(city: str) -> str:
    """Returns weather info for the specified city."""
    return f"The weather in {city} is sunny"


@function_tool
def sum_numbers(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b


def custom_tool_handler(
    context: RunContextWrapper[Any],
    tool_results: list[FunctionToolResult],
) -> ToolsToFinalOutputResult:
    """Stop only when get_weather returns sunny weather."""
    for result in tool_results:
        if result.tool.name == "get_weather" and "sunny" in str(result.output):
            return ToolsToFinalOutputResult(
                is_final_output=True,
                final_output=f"Final weather: {result.output}",
            )

    return ToolsToFinalOutputResult(is_final_output=False, final_output=None)


async def run_case(title: str, agent: Agent, user_input: str) -> None:
    print(f"\n===== {title} =====")

    result = await Runner.run(
        agent,
        user_input,
        run_config=RunConfig(tracing_disabled=True),
    )

    print("final_output:", result.final_output)
    print("model_turns:", len(result.raw_responses))
    print("new_items:")
    for item in result.new_items:
        print(" -", item)


async def main() -> None:
    common_settings = ModelSettings(tool_choice="auto")
    weather_prompt = "今天广州天气如何？请先调用 get_weather 工具，再回答。"

    await run_case(
        "1. run_llm_again: 工具结果会再交给 LLM 生成最终回答",
        Agent(
            name="Weather Agent - run_llm_again",
            model=model,
            instructions="Retrieve weather details. You must use get_weather when asked weather.",
            tools=[get_weather],
            model_settings=common_settings,
            tool_use_behavior="run_llm_again",
        ),
        weather_prompt,
    )

    await run_case(
        "2. stop_on_first_tool: 第一个工具输出直接作为最终回答",
        Agent(
            name="Weather Agent - stop_on_first_tool",
            model=model,
            instructions="Retrieve weather details. You must use get_weather when asked weather.",
            tools=[get_weather],
            model_settings=common_settings,
            tool_use_behavior="stop_on_first_tool",
        ),
        weather_prompt,
    )

    await run_case(
        "3. StopAtTools: 命中 get_weather 时直接停止",
        Agent(
            name="Weather Agent - StopAtTools",
            model=model,
            instructions=(
                "Use get_weather for weather questions and sum_numbers for math questions. "
                "When asked weather, call get_weather first."
            ),
            tools=[get_weather, sum_numbers],
            model_settings=common_settings,
            tool_use_behavior=StopAtTools(stop_at_tool_names=["get_weather"]),
        ),
        weather_prompt,
    )

    await run_case(
        "4. custom_tool_handler: 自定义函数决定是否直接输出",
        Agent(
            name="Weather Agent - custom handler",
            model=model,
            instructions="Retrieve weather details. You must use get_weather when asked weather.",
            tools=[get_weather],
            model_settings=common_settings,
            tool_use_behavior=custom_tool_handler,
        ),
        weather_prompt,
    )


if __name__ == "__main__":
    asyncio.run(main())
