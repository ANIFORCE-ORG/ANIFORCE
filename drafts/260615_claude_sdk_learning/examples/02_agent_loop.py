from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import anyio
from loguru import logger
from claude_agent_sdk import ClaudeAgentOptions, query

from sdk_learning_common import (
    LEARNING_DIR,
    OUT_DIR,
    LogState,
    count_message_classes,
    count_system_subtypes,
    count_tool_usage,
    load_profile_env,
    log_message,
    prepare_clean_dir,
    setup_logger,
    summarize_message,
    write_record,
)


SANDBOX_DIR = LEARNING_DIR / "examples" / "02_agent_loop_sandbox"
CLAUDE_CONFIG_SANDBOX = LEARNING_DIR / "examples" / "02_claude_config_sandbox"


def reset_sandbox() -> None:
    logger.info("重置第 2 章 sandbox: {}", SANDBOX_DIR)
    prepare_clean_dir(SANDBOX_DIR)
    prepare_clean_dir(CLAUDE_CONFIG_SANDBOX / "projects")
    (SANDBOX_DIR / "utils.py").write_text(
        """def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)


def get_user_name(user):
    return user[\"name\"].upper()
""",
        encoding="utf-8",
    )


def build_options(profile: str, max_turns: int) -> ClaudeAgentOptions:
    load_profile_env(profile)
    env = {key: value for key, value in os.environ.items() if key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_")}
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-sdk-learning/0.2-agent-loop"
    env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_SANDBOX)
    model = os.getenv("CLAUDE_AGENT_MODEL", "claude-opus-4-6")
    logger.info("构造 options: model={}, cwd={}, max_turns={}, thinking=disabled, effort=low", model, SANDBOX_DIR, max_turns)
    return ClaudeAgentOptions(
        cwd=SANDBOX_DIR,
        model=model,
        max_turns=max_turns,
        allowed_tools=["Read", "Glob", "Grep"],
        disallowed_tools=["Write", "Edit", "Bash"],
        permission_mode="dontAsk",
        system_prompt="You are an agent loop lifecycle probe. Do not modify files.",
        env=env,
        thinking={"type": "disabled"},
        effort="low",
    )


async def run_case(case: str, profile: str, max_turns: int) -> dict[str, Any]:
    log_path = setup_logger(f"02_agent_loop_{case}")
    logger.info("开始第 2 章 Agent Loop 验证: case={}, profile={}, max_turns={}", case, profile, max_turns)
    reset_sandbox()

    prompt = (
        "Use the Read tool on the relative path utils.py in the current working directory. "
        "Review it for bugs that would cause crashes. Do not edit files. "
        "Explain the bugs and crash scenarios only."
    )
    output_path = OUT_DIR / f"02_agent_loop_{case}.jsonl"
    summary_path = OUT_DIR / f"02_agent_loop_{case}_summary.json"
    output_path.unlink(missing_ok=True)
    records = []
    log_state = LogState()
    started_at = anyio.current_time()
    before = (SANDBOX_DIR / "utils.py").read_text(encoding="utf-8")

    try:
        async for message in query(prompt=prompt, options=build_options(profile, max_turns)):
            record = summarize_message(len(records), message)
            records.append(record)
            log_message(record, log_state)
            write_record(output_path, record)
    except Exception as exc:
        record = type(records[0])(
            index=len(records),
            class_name="ProbeException",
            summary={"error_type": exc.__class__.__name__, "message": str(exc)},
        ) if records else None
        if record:
            records.append(record)
            log_message(record, log_state)
            write_record(output_path, record)

    after = (SANDBOX_DIR / "utils.py").read_text(encoding="utf-8")
    result_records = [record for record in records if record.class_name == "ResultMessage"]
    final_result = result_records[-1].summary if result_records else {}
    summary = {
        "case": case,
        "profile": profile,
        "max_turns": max_turns,
        "elapsed_ms": round((anyio.current_time() - started_at) * 1000, 2),
        "message_count": len(records),
        "message_class_counts": count_message_classes(records),
        "system_subtype_counts": count_system_subtypes(records),
        "tool_use_counts": count_tool_usage(records),
        "result_subtype": final_result.get("subtype"),
        "result_is_error": final_result.get("is_error"),
        "result_num_turns": final_result.get("num_turns"),
        "result_session_id": final_result.get("session_id"),
        "utils_changed": before != after,
        "log_path": str(log_path),
        "output_path": str(output_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("第 2 章 case 结束: {}", json.dumps(summary, ensure_ascii=False))
    return summary


async def main_async(args: argparse.Namespace) -> None:
    if args.case == "both":
        success = await run_case("success", args.profile, 8)
        max_turns = await run_case("max_turns", args.profile, 1)
        compare_path = OUT_DIR / "02_agent_loop_compare_summary.json"
        compare_path.write_text(json.dumps({"success": success, "max_turns": max_turns}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        logger.info("第 2 章对比摘要: {}", compare_path)
        return
    max_turns = 8 if args.case == "success" else 1
    await run_case(args.case, args.profile, max_turns)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 2: agent loop lifecycle probe.")
    parser.add_argument("--case", choices=["success", "max_turns", "both"], default="both")
    parser.add_argument("--profile", default="codefoxai_sonnet")
    return parser.parse_args()


def main() -> None:
    anyio.run(main_async, parse_args())


if __name__ == "__main__":
    main()
