#!/usr/bin/env python3
# %%
"""调试 ShellTool 本地执行：ANIFORCE 场景。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/03-runtime/260701_03_shelltool_local_debug.py
"""

import asyncio

from openai import AsyncOpenAI
from agents import ModelSettings, Runner, SandboxAgent
from agents.models.openai_responses import OpenAIResponsesModel
from agents.run import RunConfig
from agents.sandbox import SandboxRunConfig
from agents.sandbox.capabilities import Shell
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient

MODEL = "gpt-5.3-codex"
BASE_URL = "https://api.tokenlab.sh/v1"
API_KEY = "sk-aeRemEo2sD0YgQWEFGjipWrzTp4LVFUVzHD8bD5fx5PoLMGF"


async def main():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    model = OpenAIResponsesModel(model=MODEL, openai_client=client)

    agent = SandboxAgent(
        name="ANIFORCE Shell Assistant",
        instructions="你是 ANIFORCE 助手，可以执行本地 shell 命令。回答简洁。",
        model=model,
        capabilities=[Shell()],
        model_settings=ModelSettings(
            parallel_tool_calls=False,
            truncation="auto",
            store=False,
        ),
    )

    prompt = "列出当前目录，然后统计有多少个 .py 文件"

    result = await Runner.run(
        agent,
        prompt,
        run_config=RunConfig(sandbox=SandboxRunConfig(client=UnixLocalSandboxClient())),
        max_turns=5,
    )

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
