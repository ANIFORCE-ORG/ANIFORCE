#!/usr/bin/env python3
# %%
"""精简调试：OpenAIResponsesModel + ModelSettings。

运行：
  TOKENLAB_API_KEY=你的key UV_CACHE_DIR=./uv_cache uv run python notebooks/03-runtime/260701_01_responses_model_settings_debug.py
"""

import asyncio
import os

from openai import AsyncOpenAI
from agents import Agent, ModelSettings, Runner
from agents.models.openai_responses import OpenAIResponsesModel

MODEL = os.getenv("ANIFORCE_DEBUG_MODEL", "gpt-5.3-codex")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.tokenlab.sh/v1")
API_KEY = os.getenv("TOKENLAB_API_KEY") or os.getenv("OPENAI_API_KEY")


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
        name="Assistant",
        instructions="You are a helpful assistant. Keep answers concise.",
        model=model,
        model_settings=ModelSettings(
            parallel_tool_calls=False,
            truncation="auto",
            store=False,
            context_management=[{"type": "compaction", "compact_threshold": 200000}],
            prompt_cache_retention="24h",
        ),
    )

    result = await Runner.run(agent, "hi，简单说明 store=false 和 truncation=auto 的作用")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
