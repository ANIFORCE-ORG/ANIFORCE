"""用 strace 抓 SDK 的网络系统调用，定位 8 秒去了哪。

跑一次 SDK query("hi")，同时 strace 抓 connect/sendto/recvfrom，
最后分析每个 socket 的生命周期。
"""

from __future__ import annotations

import asyncio
import os
import subprocess
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
SANDBOX = ROOT / "drafts" / "260618" / "ttft_sandbox_strace"
CONFIG_SANDBOX = ROOT / "drafts" / "260618" / "ttft_config_sandbox_strace"
STRACE_LOG = ROOT / "drafts" / "260618" / "strace.log"


# ---- 配置 ----
BASE_URL = "https://copilot.huya.info/api/anthropic"
TOKEN = "sk-hvtAUe3lPjYQtwiZqLMfYg"
MODEL = "claude-sonnet-4-6"


def build_env() -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items()
        if k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_")
    }
    env["ANTHROPIC_AUTH_TOKEN"] = TOKEN
    env["ANTHROPIC_BASE_URL"] = BASE_URL
    env["CLAUDE_CONFIG_DIR"] = str(CONFIG_SANDBOX)
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "ttft-strace/1.0"
    return env


async def run_with_strace():
    SANDBOX.mkdir(parents=True, exist_ok=True)
    CONFIG_SANDBOX.mkdir(parents=True, exist_ok=True)
    if STRACE_LOG.exists():
        STRACE_LOG.unlink()

    print(f"[INFO] PID={os.getpid()}")

    # 启动 strace 跟踪当前进程及子进程的网络 syscall
    strace_proc = subprocess.Popen(
        [
            "strace",
            "-f",  # 跟踪 fork 的子进程
            "-tt",  # 时间戳到微秒
            "-T",   # 每条 syscall 的耗时
            "-y",   # 显示 fd 关联的目标
            "-e", "trace=network",
            "-p", str(os.getpid()),
            "-o", str(STRACE_LOG),
        ],
        stderr=subprocess.PIPE,
    )

    # 等 strace attach
    await anyio.sleep(0.5)

    options = ClaudeAgentOptions(
        cwd=str(SANDBOX),
        model=MODEL,
        max_turns=1,
        env=build_env(),
        thinking={"type": "disabled"},
        effort="low",
        include_partial_messages=True,
        setting_sources=[],
        skills=[],
    )

    t0 = time.monotonic()
    def stamp(label):
        print(f"  T+{(time.monotonic()-t0)*1000:7.0f}ms  {label}")

    stamp("START")
    client = ClaudeSDKClient(options)
    await client.connect()
    stamp("client.connect() done")
    await client.query("hi")
    stamp("client.query() returned")

    first_msg = True
    first_delta = True
    async for msg in client.receive_response():
        if first_msg:
            stamp(f"first message: {type(msg).__name__}")
            first_msg = False
        if first_delta and isinstance(msg, StreamEvent):
            event = msg.event if hasattr(msg, "event") else {}
            if event.get("type") == "content_block_delta":
                d = event.get("delta", {})
                if d.get("type") == "text_delta" and d.get("text"):
                    stamp(f"first text delta: {d['text']!r}")
                    first_delta = False
        if isinstance(msg, ResultMessage):
            stamp(f"ResultMessage")
            break

    await client.disconnect()
    stamp("client.disconnect() done")

    # 停止 strace
    strace_proc.terminate()
    try:
        strace_proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        strace_proc.kill()

    print(f"\n[INFO] strace log: {STRACE_LOG}")
    print(f"[INFO] log size: {STRACE_LOG.stat().st_size} bytes")


if __name__ == "__main__":
    anyio.run(run_with_strace)
