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

# 第 5 章主题：ClaudeSDKClient。
# 接第 4 章悬念：同一个 client 实例内多次 query() 是否共享上下文（有状态）。
# 直接对照第 4 章：同样的“失忆实验”，这次应当“记得”。
# 基线：thinking=disabled + effort=low，无工具。

CLAUDE_CONFIG_SANDBOX = LEARNING_DIR / "examples" / "05_claude_config_sandbox"

def build_options(profile: str) -> ClaudeAgentOptions:
    load_profile_env(profile)
    env = {k: v for k, v in os.environ.items() if k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_")}
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-sdk-learning/0.5-client-stateful"
    env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_SANDBOX)
    model = os.getenv("CLAUDE_AGENT_MODEL", "claude-opus-4-6")
    return ClaudeAgentOptions(
        model=model,
        max_turns=2,
        tools=[],
        system_prompt="You are a concise assistant. Answer in one short sentence.",
        env=env,
        thinking={"type": "disabled"},
        effort="low",
    )


async def run_turn(
    client: ClaudeSDKClient,
    label: str,
    prompt: str,
    output_path: Any,
    log_state: LogState,
    records: list,
) -> dict[str, Any]:
    """在同一个 client 上发一轮 query 并收完一个 response。"""
    logger.info("[{}] 发出 query: {}", label, prompt)
    await client.query(prompt)
    turn_start = len(records)
    final_text = ""
    session_id = None
    async for message in client.receive_response():
        record = summarize_message(len(records), message)
        records.append(record)
        log_message(record, log_state)
        write_record(output_path, record)
        if record.class_name == "ResultMessage":
            session_id = record.summary.get("session_id")
            if record.summary.get("result"):
                final_text = record.summary["result"]
    return {
        "label": label,
        "prompt": prompt,
        "session_id": session_id,
        "final_text": final_text,
        "turn_message_count": len(records) - turn_start,
    }


async def main_async(args: argparse.Namespace) -> None:
    setup_logger("05_client_stateful")
    logger.info("开始第 5 章 ClaudeSDKClient 有状态验证: profile={}", args.profile)
    options = build_options(args.profile)

    output_path = OUT_DIR / "05_client_stateful.jsonl"
    output_path.unlink(missing_ok=True)
    records: list = []
    log_state = LogState()

    # 同一个 client 实例内跑两轮 —— 与第 4 章两次独立 query 形成对照。
    async with ClaudeSDKClient(options=options) as client:
        first = await run_turn(
            client,
            "first",
            "The capital of France is Paris. Remember this fact.",
            output_path,
            log_state,
            records,
        )
        second = await run_turn(
            client,
            "second",
            "What city did I mention in my previous message? If you have no previous message, say you don't know.",
            output_path,
            log_state,
            records,
        )

    same_session = bool(first["session_id"]) and first["session_id"] == second["session_id"]
    remembered = "paris" in second["final_text"].lower()

    summary = {
        "profile": args.profile,
        "first": first,
        "second": second,
        "same_session_id": same_session,
        "second_remembered_context": remembered,
        "message_class_counts": count_message_classes(records),
        "verdict": "stateful_confirmed" if remembered else "stateless_unexpected",
    }
    summary_path = OUT_DIR / "05_client_stateful_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    logger.info("第 1 轮 session_id: {}", first["session_id"])
    logger.info("第 2 轮 session_id: {}", second["session_id"])
    logger.info("两轮 session_id 相同? {}", same_session)
    logger.info("第 2 轮是否记得上文(出现 Paris)? {}", remembered)
    logger.info("结论: {}", summary["verdict"])
    logger.info("第 5 章摘要已写出: {}", summary_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 5: ClaudeSDKClient stateful probe.")
    parser.add_argument("--profile", default="codefoxai_sonnet")
    return parser.parse_args()


def main() -> None:
    anyio.run(main_async, parse_args())


if __name__ == "__main__":
    main()

