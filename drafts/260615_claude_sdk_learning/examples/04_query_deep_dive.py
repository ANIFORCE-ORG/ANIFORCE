from __future__ import annotations

import argparse
import json
from typing import Any

import anyio
from loguru import logger
from claude_agent_sdk import ClaudeAgentOptions, query

from sdk_learning_common import (
    LEARNING_DIR,
    OUT_DIR,
    LogState,
    count_message_classes,
    load_profile_env,
    log_message,
    setup_logger,
    summarize_message,
    write_record,
)

# 第 4 章主题：query() 深入。
# 实证 query() 的「无状态」边界：两次独立 query 之间是否记得上文。
# 这是 ANIFORCE 多轮对话能否用 query() 的关键判断点。
# 基线：thinking=disabled + effort=low，省 token、减噪声。

import os

CLAUDE_CONFIG_SANDBOX = LEARNING_DIR / "examples" / "04_claude_config_sandbox"

def build_options(profile: str) -> ClaudeAgentOptions:
    load_profile_env(profile)
    env = {k: v for k, v in os.environ.items() if k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_")}
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-sdk-learning/0.4-query-deep-dive"
    env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_SANDBOX)
    model = os.getenv("CLAUDE_AGENT_MODEL", "claude-opus-4-6")
    # 无工具：本章只验证对话记忆边界，不需要文件/工具能力。
    return ClaudeAgentOptions(
        model=model,
        max_turns=2,
        tools=[],
        system_prompt="You are a concise assistant. Answer in one short sentence.",
        env=env,
        thinking={"type": "disabled"},
        effort="low",
    )


async def run_one_query(label: str, prompt: str, options: ClaudeAgentOptions) -> dict[str, Any]:
    """跑一次独立 query()，记录消息流和 session_id。"""
    logger.info("[{}] 发出 query: {}", label, prompt)
    records = []
    log_state = LogState()
    output_path = OUT_DIR / f"04_query_deep_dive_{label}.jsonl"
    output_path.unlink(missing_ok=True)
    final_text = ""
    session_id = None
    async for message in query(prompt=prompt, options=options):
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
        "message_class_counts": count_message_classes(records),
        "message_count": len(records),
    }


async def main_async(args: argparse.Namespace) -> None:
    setup_logger("04_query_deep_dive")
    logger.info("开始第 4 章 query() 无状态边界验证: profile={}", args.profile)
    options = build_options(args.profile)

    # 第 1 次：给出一个明确事实。
    first = await run_one_query(
        "first",
        "The capital of France is Paris. Remember this fact.",
        options,
    )
    # 第 2 次：独立 query，故意不重复 'France' / 'Paris'，
    # 只问 “我上一条消息提到的那个城市是什么”。
    # 若 query() 无状态，模型应当无法回答（失忆）。
    second = await run_one_query(
        "second",
        "What city did I mention in my previous message? If you have no previous message, say you don't know.",
        options,
    )

    same_session = bool(first["session_id"]) and first["session_id"] == second["session_id"]
    second_lower = second["final_text"].lower()
    remembered = "paris" in second_lower

    summary = {
        "profile": args.profile,
        "first": first,
        "second": second,
        "same_session_id": same_session,
        "second_remembered_context": remembered,
        "verdict": (
            "stateful_unexpected" if remembered
            else "stateless_confirmed"
        ),
    }
    summary_path = OUT_DIR / "04_query_deep_dive_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    logger.info("第 1 次 session_id: {}", first["session_id"])
    logger.info("第 2 次 session_id: {}", second["session_id"])
    logger.info("两次 session_id 相同? {}", same_session)
    logger.info("第 2 次是否记得上文(出现 Paris)? {}", remembered)
    logger.info("结论: {}", summary["verdict"])
    logger.info("第 4 章摘要已写出: {}", summary_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 4: query() statelessness probe.")
    parser.add_argument("--profile", default="codefoxai_sonnet")
    return parser.parse_args()


def main() -> None:
    anyio.run(main_async, parse_args())


if __name__ == "__main__":
    main()

