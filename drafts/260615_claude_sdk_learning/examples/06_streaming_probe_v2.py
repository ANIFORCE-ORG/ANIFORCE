from __future__ import annotations

import argparse
import json
import os

import anyio
from loguru import logger
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, AssistantMessage, TextBlock, ResultMessage, StreamEvent

from sdk_learning_common import (
    LEARNING_DIR,
    OUT_DIR,
    load_profile_env,
    setup_logger,
)

# 第 6 章 v2：正确观察流式行为。
# 关键修正：直接打印原始 TextBlock.text，不要用 summarize_message 压缩。

CLAUDE_CONFIG_SANDBOX = LEARNING_DIR / "examples" / "06_claude_config_sandbox_v2"


def build_options(profile: str) -> ClaudeAgentOptions:
    load_profile_env(profile)
    env = {k: v for k, v in os.environ.items() if k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_")}
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-sdk-learning/0.6-streaming-probe-v2"
    env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_SANDBOX)
    model = os.getenv("CLAUDE_AGENT_MODEL", "claude-opus-4-6")
    return ClaudeAgentOptions(
        model=model,
        max_turns=3,
        tools=[],
        system_prompt="You are a helpful coding assistant.",
        env=env,
        thinking={"type": "disabled"},  # 先关闭 thinking，只观察 text 流式
        effort="low",
        include_partial_messages=True,  # 🔑 关键：启用增量流式消息！
    )


async def main_async(args: argparse.Namespace) -> None:
    setup_logger("06_streaming_probe_v2")
    logger.info("开始第 6 章 v2 流式输出验证（原始 text 观察）: profile={}", args.profile)
    options = build_options(args.profile)

    output_path = OUT_DIR / "06_streaming_probe_v2.jsonl"
    output_path.unlink(missing_ok=True)

    prompt = (
        "Write a detailed tutorial on Python decorators. Include: "
        "1) Basic decorator syntax, 2) Decorators with arguments, "
        "3) Class decorators, 4) Built-in decorators, 5) Practical examples. "
        "Make it comprehensive with code examples for each section."
    )

    text_snapshots = []  # 记录每次 TextBlock 的完整文本
    stream_events = []  # 记录 StreamEvent
    assistant_message_count = 0

    async with ClaudeSDKClient(options=options) as client:
        logger.info("发出 query: {}", prompt)
        await client.query(prompt)

        async for message in client.receive_messages():
            if isinstance(message, StreamEvent):
                stream_events.append({
                    "event_type": message.event.get("type"),
                    "event": message.event,
                })
                logger.info("StreamEvent | type={} | event={}",
                           message.event.get("type"),
                           str(message.event)[:200])
            elif isinstance(message, AssistantMessage):
                assistant_message_count += 1
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text = block.text
                        text_snapshots.append({
                            "message_index": assistant_message_count,
                            "text_length": len(text),
                            "text_preview": text[:200] if len(text) > 200 else text,
                        })
                        # 实时打印，观察是否增量
                        logger.info("AssistantMessage #{} | TextBlock length={} | preview: {}...",
                                    assistant_message_count, len(text), text[:100])
            elif isinstance(message, ResultMessage):
                logger.info("收到 ResultMessage，结束循环")
                break

    # 判断是否增量：如果相邻快照的 text_length 递增，说明是增量流式
    is_incremental = False
    if len(text_snapshots) > 1:
        lengths = [s["text_length"] for s in text_snapshots]
        # 所有相邻长度都递增 -> 增量流式
        is_incremental = all(lengths[i] < lengths[i+1] for i in range(len(lengths)-1))

    summary = {
        "profile": args.profile,
        "prompt": prompt,
        "assistant_message_count": assistant_message_count,
        "stream_event_count": len(stream_events),
        "text_snapshot_count": len(text_snapshots),
        "text_snapshots": text_snapshots,
        "stream_event_types": [e["event_type"] for e in stream_events],
        "is_incremental_streaming": is_incremental,
        "verdict": "incremental_streaming" if is_incremental else "full_block_push",
    }

    summary_path = OUT_DIR / "06_streaming_probe_v2_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    logger.info("AssistantMessage 总数: {}", assistant_message_count)
    logger.info("StreamEvent 总数: {}", len(stream_events))
    logger.info("TextBlock 快照数: {}", len(text_snapshots))
    logger.info("是否增量流式: {}", is_incremental)
    logger.info("结论: {}", summary["verdict"])
    logger.info("第 6 章 v2 摘要已写出: {}", summary_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 6 v2: Streaming behavior probe (raw text observation).")
    parser.add_argument("--profile", default="codefoxai_sonnet")
    return parser.parse_args()


def main() -> None:
    anyio.run(main_async, parse_args())


if __name__ == "__main__":
    main()
