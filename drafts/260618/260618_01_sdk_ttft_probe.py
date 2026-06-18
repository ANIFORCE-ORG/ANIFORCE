"""SDK 首字延迟探针 —— deepseek vs claude 对比"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import anyio
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    StreamEvent,
)

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = ROOT / "drafts" / "260618" / "ttft_sandbox"
CONFIG_SANDBOX = ROOT / "drafts" / "260618" / "ttft_config_sandbox"

BASE_URL = "https://copilot.huya.info/api/anthropic"
TOKEN = "sk-hvtAUe3lPjYQtwiZqLMfYg"


def build_env() -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items()
        if k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_")
    }
    env["ANTHROPIC_AUTH_TOKEN"] = TOKEN
    env["ANTHROPIC_BASE_URL"] = BASE_URL
    env["CLAUDE_CONFIG_DIR"] = str(CONFIG_SANDBOX)
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "ttft-probe/1.0"
    return env


async def run_case(name: str, model: str, env_override: dict | None = None) -> None:
    SANDBOX.mkdir(parents=True, exist_ok=True)
    CONFIG_SANDBOX.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  CASE [{name}]  model={model}")
    print(f"{'='*60}")

    env = build_env()
    if env_override:
        env.update(env_override)

    options = ClaudeAgentOptions(
        cwd=str(SANDBOX),
        model=model,
        max_turns=1,
        env=env,
        thinking={"type": "disabled"},
        effort="low",
        include_partial_messages=True,
        setting_sources=[],
        skills=[],
    )

    t0 = time.monotonic()
    def stamp(label: str):
        print(f"  T+{(time.monotonic()-t0)*1000:7.0f}ms  {label}")

    stamp("START")
    client = ClaudeSDKClient(options)
    await client.connect()
    stamp("connect done")
    await client.query("hi")
    stamp("query sent")

    first_msg = True
    first_delta = True
    async for msg in client.receive_response():
        if first_msg:
            stamp(f"first msg: {type(msg).__name__}")
            first_msg = False
        if first_delta and isinstance(msg, StreamEvent):
            event = msg.event if hasattr(msg, "event") else {}
            if event.get("type") == "content_block_delta":
                d = event.get("delta", {})
                if d.get("type") == "text_delta" and d.get("text"):
                    stamp(f"first delta: {d['text']!r}")
                    first_delta = False
        if isinstance(msg, ResultMessage):
            stamp(f"ResultMessage (subtype={msg.subtype})")
            break

    await client.disconnect()
    stamp("disconnect done")


async def main():
    # A: claude-sonnet-4-6
    await run_case("A: copilot + claude-sonnet-4-6", "claude-sonnet-4-6")

    # B: deepseek-v4-pro
    await run_case("B: copilot + deepseek-v4-pro", "deepseek/deepseek-v4-pro")

    # C: 直连 anthropic
    await run_case("C: direct api.anthropic.com", "claude-sonnet-4-6", {
        "ANTHROPIC_BASE_URL": "",  # 删掉让 CLI 走默认
    })


if __name__ == "__main__":
    anyio.run(main)
