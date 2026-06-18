from __future__ import annotations

import argparse
import json
import os
from typing import Any

import anyio
from loguru import logger
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from sdk_learning_common import (
    LEARNING_DIR,
    OUT_DIR,
    LogState,
    count_message_classes,
    log_message,
    load_profile_env,
    setup_logger,
    summarize_message,
    write_record,
)

# 第 6 章主题：Streaming 流式输出。
# 验证目标：
# 1. AssistantMessage 是增量更新（delta）还是完整替换（snapshot）？
# 2. TextBlock / ThinkingBlock 的流式行为是什么？
# 3. 一个完整 response 会产生多少条 AssistantMessage？
# 4. 为 ANIFORCE 的 SSE event 映射积累证据。
#
# 策略：
# - 用一个会产生较长输出的 prompt（让模型写一段代码或解释复杂概念）
# - 开启 thinking（观察 ThinkingBlock 流式）
# - 详细记录每条 AssistantMessage 的完整内容（不只摘要）
# - 对比相邻两条 AssistantMessage，判断是否增量

CLAUDE_CONFIG_SANDBOX = LEARNING_DIR / "examples" / "06_claude_config_sandbox"


def build_options(profile: str) -> ClaudeAgentOptions:
    load_profile_env(profile)
    env = {k: v for k, v in os.environ.items() if k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_")}
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-sdk-learning/0.6-streaming-probe"
    env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_SANDBOX)
    model = os.getenv("CLAUDE_AGENT_MODEL", "claude-opus-4-6")
    return ClaudeAgentOptions(
        model=model,
        max_turns=3,
        tools=[],
        system_prompt="You are a helpful coding assistant.",
        env=env,
        thinking={"type": "adaptive"},  # 自适应 thinking，观察流式行为
        effort="medium",
    )


async def main_async(args: argparse.Namespace) -> None:
    setup_logger("06_streaming_probe")
    logger.info("开始第 6 章 Streaming 流式输出验证: profile={}", args.profile)
    options = build_options(args.profile)

    output_path = OUT_DIR / "06_streaming_probe.jsonl"
    output_path.unlink(missing_ok=True)
    records: list = []
    log_state = LogState()

    # 用一个会产生较长输出的 prompt
    prompt = (
        "Write a Python function that implements binary search on a sorted list. "
        "Include detailed comments explaining each step, handle edge cases, "
        "and provide a usage example with test cases."
    )

    async with ClaudeSDKClient(options=options) as client:
        logger.info("发出 query: {}", prompt)
        await client.query(prompt)

        assistant_messages = []
        async for message in client.receive_response():
            record = summarize_message(len(records), message)
            records.append(record)
            log_message(record, log_state)
            write_record(output_path, record)

            # 保留所有 AssistantMessage 的完整内容用于后续分析
            if record.class_name == "AssistantMessage":
                assistant_messages.append({
                    "index": record.index,
                    "content_blocks": record.summary.get("content", []),
                })

    # 分析流式行为
    text_block_updates = []
    thinking_block_updates = []

    for i, msg in enumerate(assistant_messages):
        for block in msg["content_blocks"]:
            if block["type"] == "text":
                text_block_updates.append({
                    "message_index": msg["index"],
                    "text_length": len(block.get("text", "")),
                    "text_preview": block.get("text", "")[:100],
                })
            elif block["type"] == "thinking":
                thinking_block_updates.append({
                    "message_index": msg["index"],
                    "thinking_length": len(block.get("thinking", "")),
                    "thinking_preview": block.get("thinking", "")[:100],
                })

    # 判断是否增量：如果相邻两条消息的 text 长度递增，说明是增量；如果跳变或相等，说明是快照
    is_incremental_text = False
    if len(text_block_updates) > 1:
        lengths = [u["text_length"] for u in text_block_updates]
        is_incremental_text = all(lengths[i] <= lengths[i+1] for i in range(len(lengths)-1))

    summary = {
        "profile": args.profile,
        "prompt": prompt,
        "total_messages": len(records),
        "assistant_message_count": len(assistant_messages),
        "text_block_updates": text_block_updates,
        "thinking_block_updates": thinking_block_updates,
        "is_incremental_text": is_incremental_text,
        "message_class_counts": count_message_classes(records),
    }

    summary_path = OUT_DIR / "06_streaming_probe_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    logger.info("总消息数: {}", len(records))
    logger.info("AssistantMessage 数量: {}", len(assistant_messages))
    logger.info("TextBlock 更新次数: {}", len(text_block_updates))
    logger.info("ThinkingBlock 更新次数: {}", len(thinking_block_updates))
    logger.info("TextBlock 是否增量更新: {}", is_incremental_text)
    logger.info("第 6 章摘要已写出: {}", summary_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 6: Streaming behavior probe.")
    parser.add_argument("--profile", default="codefoxai_sonnet")
    return parser.parse_args()


def main() -> None:
    anyio.run(main_async, parse_args())


if __name__ == "__main__":
    main()
