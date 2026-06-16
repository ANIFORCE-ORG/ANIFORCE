from __future__ import annotations

import argparse
import json
import os
import shutil
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import anyio
from loguru import logger
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)


ROOT = Path(__file__).resolve().parents[3]
LEARNING_DIR = ROOT / "drafts" / "260615_claude_sdk_learning"
OUT_DIR = LEARNING_DIR / "outputs"
SANDBOX_DIR = LEARNING_DIR / "examples" / "01_query_quickstart_sandbox"
CLAUDE_CONFIG_SANDBOX = LEARNING_DIR / "examples" / "01_claude_config_sandbox"
PROFILE_FILE = LEARNING_DIR / "configs" / "claude_sdk_profiles.yaml"


def setup_logger(mode: str, config_mode: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUT_DIR / f"01_query_quickstart_{mode}_{config_mode}.log"
    logger.remove()
    logger.add(
        lambda message: print(message, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | {message}",
        level="INFO",
        colorize=True,
    )
    logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | {message}",
        level="INFO",
        encoding="utf-8",
        mode="w",
    )
    return log_path


@dataclass
class MessageRecord:
    index: int
    class_name: str
    summary: dict[str, Any]


@dataclass
class LogState:
    thinking_token_events: int = 0
    thinking_token_latest: int | None = None
    thinking_token_delta_total: int = 0

    def record_thinking_tokens(self, data: dict[str, Any]) -> None:
        self.thinking_token_events += 1
        latest = data.get("estimated_tokens")
        if isinstance(latest, int):
            self.thinking_token_latest = latest
        delta = data.get("estimated_tokens_delta")
        if isinstance(delta, int):
            self.thinking_token_delta_total += delta

    def flush_thinking_tokens(self, reason: str) -> None:
        if self.thinking_token_events == 0:
            return
        logger.info(
            "[thinking_progress] {} events, latest_estimated_tokens={}, delta_total={} ({})",
            self.thinking_token_events,
            self.thinking_token_latest,
            self.thinking_token_delta_total,
            reason,
        )
        self.thinking_token_events = 0
        self.thinking_token_latest = None
        self.thinking_token_delta_total = 0


def reset_sandbox(config_mode: str) -> None:
    logger.info("重置 sandbox 目录: {}", SANDBOX_DIR)
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    if config_mode == "isolated":
        logger.info("重置 Claude 配置隔离目录: {}", CLAUDE_CONFIG_SANDBOX)
        if CLAUDE_CONFIG_SANDBOX.exists():
            shutil.rmtree(CLAUDE_CONFIG_SANDBOX)
        (CLAUDE_CONFIG_SANDBOX / "projects").mkdir(parents=True, exist_ok=True)
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
    logger.info("写入带 bug 的演示文件: {}", SANDBOX_DIR / "utils.py")


def load_profile_env(profile_name: str) -> dict[str, str]:
    profiles = load_profiles()
    if profile_name not in profiles:
        raise ValueError(f"Unknown profile: {profile_name}")
    loaded = profiles[profile_name]
    for key, value in loaded.items():
        os.environ[key] = value
    logger.info("从 YAML profile 加载 Claude 相关配置: {}", profile_name)
    logger.info("当前 token 指纹: {}", mask_secret(loaded.get("ANTHROPIC_AUTH_TOKEN", "")))
    logger.info("当前 base_url: {}", loaded.get("ANTHROPIC_BASE_URL"))
    logger.info("当前 model: {}", loaded.get("CLAUDE_AGENT_MODEL"))
    return loaded


def load_profiles() -> dict[str, dict[str, str]]:
    if not PROFILE_FILE.exists():
        raise FileNotFoundError(f"Profile file not found: {PROFILE_FILE}")
    profiles: dict[str, dict[str, str]] = {}
    current_profile: str | None = None
    current_section: str | None = None
    for raw_line in PROFILE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0 and stripped.endswith(":"):
            key = stripped[:-1]
            if key != "profiles":
                raise ValueError(f"Unexpected top-level key in profile file: {key}")
            current_section = key
            continue
        if current_section != "profiles":
            continue
        if indent == 2 and stripped.endswith(":"):
            current_profile = stripped[:-1]
            profiles[current_profile] = {}
            continue
        if indent == 4 and ":" in stripped and current_profile:
            key, value = stripped.split(":", 1)
            profiles[current_profile][key.strip()] = unquote_yaml_scalar(value.strip())
    return profiles


def unquote_yaml_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def mask_secret(value: str) -> str:
    if len(value) <= 12:
        return "<short-secret>"
    return f"{value[:8]}...{value[-4:]}"


def log_current_env_fingerprint() -> None:
    token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    model = os.getenv("CLAUDE_AGENT_MODEL")
    if token:
        logger.info("当前 token 指纹: {}", mask_secret(token))
    else:
        logger.warning("当前进程未设置 ANTHROPIC_AUTH_TOKEN")
    logger.info("当前 base_url: {}", base_url)
    logger.info("当前 model: {}", model)


def summarize_block(block: Any) -> dict[str, Any]:
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    if block.__class__.__name__ == "ThinkingBlock":
        thinking = getattr(block, "thinking", "")
        return {
            "type": "thinking",
            "chars": len(thinking),
            "preview": short_text(thinking, 180),
        }
    if isinstance(block, ToolUseBlock):
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    if isinstance(block, ToolResultBlock):
        return {
            "type": "tool_result",
            "tool_use_id": block.tool_use_id,
            "content": block.content,
            "is_error": block.is_error,
        }
    return {"type": block.__class__.__name__, "repr": repr(block)}


def count_message_classes(records: list["MessageRecord"]) -> dict[str, int]:
    return dict(Counter(record.class_name for record in records))


def count_system_subtypes(records: list["MessageRecord"]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        if record.class_name == "SystemMessage":
            subtype = str(record.summary.get("subtype") or "unknown")
            counter[subtype] += 1
    return dict(counter)


def count_tool_usage(records: list["MessageRecord"]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        if record.class_name != "AssistantMessage":
            continue
        for block in record.summary.get("content") or []:
            if block.get("type") == "tool_use":
                name = str(block.get("name") or "unknown")
                counter[name] += 1
    return dict(counter)


def summarize_message(index: int, message: Any) -> MessageRecord:
    if isinstance(message, AssistantMessage):
        return MessageRecord(
            index=index,
            class_name="AssistantMessage",
            summary={
                "model": message.model,
                "message_id": message.message_id,
                "session_id": message.session_id,
                "stop_reason": message.stop_reason,
                "usage": message.usage,
                "content": [summarize_block(block) for block in message.content],
            },
        )
    if isinstance(message, UserMessage):
        content = message.content
        return MessageRecord(index=index, class_name="UserMessage", summary={"content": str(content)[:500]})
    if isinstance(message, ResultMessage):
        return MessageRecord(
            index=index,
            class_name="ResultMessage",
            summary={
                "subtype": message.subtype,
                "is_error": message.is_error,
                "duration_ms": message.duration_ms,
                "duration_api_ms": message.duration_api_ms,
                "num_turns": message.num_turns,
                "session_id": message.session_id,
                "stop_reason": message.stop_reason,
                "total_cost_usd": message.total_cost_usd,
                "usage": message.usage,
                "result": message.result,
                "errors": message.errors,
                "api_error_status": message.api_error_status,
            },
        )
    if isinstance(message, SystemMessage):
        return MessageRecord(index=index, class_name="SystemMessage", summary={"subtype": message.subtype, "data": message.data})
    return MessageRecord(index=index, class_name=message.__class__.__name__, summary={"repr": repr(message)})


def build_options(
    mode: str,
    config_mode: str,
    profile: str,
    thinking_mode: str,
    effort: str | None,
    max_turns: int,
) -> ClaudeAgentOptions:
    load_profile_env(profile)
    env = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_")
    }
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-sdk-learning/0.1"
    if config_mode == "isolated":
        env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_SANDBOX)
        logger.info("启用 Claude 配置隔离: CLAUDE_CONFIG_DIR={}", CLAUDE_CONFIG_SANDBOX)
    else:
        logger.warning("使用继承的 Claude 配置环境，可能加载本机 hooks/plugins/skills")
    model = os.getenv("CLAUDE_AGENT_MODEL", "claude-opus-4-6")
    logger.info("构造 ClaudeAgentOptions: mode={}, config_mode={}, model={}, cwd={}, max_turns={}", mode, config_mode, model, SANDBOX_DIR, max_turns)
    thinking_config: dict[str, Any] | None
    if thinking_mode == "disabled":
        thinking_config = {"type": "disabled"}
    elif thinking_mode == "adaptive":
        thinking_config = {"type": "adaptive"}
    else:
        thinking_config = None
    if effort:
        logger.info("effort 设置: {}", effort)

    if mode == "readonly":
        logger.info("权限策略: 允许 Read/Glob/Grep，禁止 Write/Edit/Bash，permission_mode=dontAsk")
        return ClaudeAgentOptions(
            cwd=SANDBOX_DIR,
            model=model,
            max_turns=max_turns,
            allowed_tools=["Read", "Glob", "Grep"],
            disallowed_tools=["Write", "Edit", "Bash"],
            permission_mode="dontAsk",
            system_prompt="You are a careful SDK learning probe. Do not modify files.",
            env=env,
            thinking=thinking_config,
            effort=effort,
        )

    logger.info("权限策略: 允许 Read/Edit/Glob，禁止 Bash/Write，permission_mode=acceptEdits")
    return ClaudeAgentOptions(
        cwd=SANDBOX_DIR,
        model=model,
        max_turns=max_turns,
        allowed_tools=["Read", "Edit", "Glob"],
        disallowed_tools=["Bash", "Write"],
        permission_mode="acceptEdits",
        system_prompt=(
            "You are a careful SDK learning probe. Only edit files inside the current working directory. "
            "Do not run shell commands."
        ),
        env=env,
        thinking=thinking_config,
        effort=effort,
    )


async def run_probe(
    mode: str,
    config_mode: str,
    profile: str,
    thinking_mode: str,
    effort: str | None,
    max_turns: int,
) -> dict[str, Any]:
    log_path = setup_logger(mode, config_mode)
    logger.info(
        "开始第 1 章演示: query() quickstart, mode={}, config_mode={}, profile={}, thinking_mode={}, effort={}, max_turns={}",
        mode,
        config_mode,
        profile,
        thinking_mode,
        effort,
        max_turns,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    loaded_env = load_profile_env(profile)
    reset_sandbox(config_mode)
    before = (SANDBOX_DIR / "utils.py").read_text(encoding="utf-8")

    if mode == "readonly":
        prompt = (
            "Use the Read tool on the relative path utils.py in the current working directory. "
            "Review it for bugs that would cause crashes. Do not edit files. "
            "Explain the bugs and crash scenarios only."
        )
    else:
        prompt = (
            "Use the Read tool on the relative path utils.py in the current working directory, "
            "then fix the bugs directly by editing utils.py. "
            "Do not only explain. Keep the fix minimal and stay within the current working directory."
        )
    output_path = OUT_DIR / f"01_query_quickstart_{mode}_{config_mode}.jsonl"
    if output_path.exists():
        output_path.unlink()
    records: list[MessageRecord] = []
    log_state = LogState()
    logger.info("原始消息 JSONL 输出: {}", output_path)
    logger.info("人类可读日志输出: {}", log_path)
    logger.info("向 SDK 发送 prompt: {}", prompt)

    started_at = anyio.current_time()
    try:
        async for message in query(prompt=prompt, options=build_options(mode, config_mode, profile, thinking_mode, effort, max_turns)):
            record = summarize_message(len(records), message)
            records.append(record)
            log_message(record, log_state)
            with output_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    except Exception as exc:
        error_record = MessageRecord(
            index=len(records),
            class_name="ProbeException",
            summary={"error_type": exc.__class__.__name__, "message": str(exc)},
        )
        records.append(error_record)
        log_state.flush_thinking_tokens("before exception")
        logger.error("SDK 演示执行异常: {}: {}", exc.__class__.__name__, exc)
        with output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(error_record), ensure_ascii=False) + "\n")

    after = (SANDBOX_DIR / "utils.py").read_text(encoding="utf-8")
    elapsed_ms = round((anyio.current_time() - started_at) * 1000, 2)
    summary = {
        "mode": mode,
        "config_mode": config_mode,
        "thinking_mode": thinking_mode,
        "effort": effort,
        "elapsed_ms": elapsed_ms,
        "max_turns": max_turns,
        "sandbox_dir": str(SANDBOX_DIR),
        "output_path": str(output_path),
        "message_count": len(records),
        "message_class_counts": count_message_classes(records),
        "system_subtype_counts": count_system_subtypes(records),
        "tool_use_counts": count_tool_usage(records),
        "utils_changed": before != after,
        "utils_before": before,
        "utils_after": after,
        "auth_env_present": {
            "ANTHROPIC_AUTH_TOKEN": bool(os.getenv("ANTHROPIC_AUTH_TOKEN")),
            "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
            "ANTHROPIC_BASE_URL": bool(os.getenv("ANTHROPIC_BASE_URL")),
            "CLAUDE_AGENT_MODEL": bool(os.getenv("CLAUDE_AGENT_MODEL")),
        },
        "loaded_backend_env_keys": sorted(loaded_env.keys()),
        "profile": profile,
        "claude_config_dir": str(CLAUDE_CONFIG_SANDBOX) if config_mode == "isolated" else os.getenv("CLAUDE_CONFIG_DIR"),
    }
    log_state.flush_thinking_tokens("before finish")
    summary_path = OUT_DIR / f"01_query_quickstart_{mode}_{config_mode}_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("演示结束: message_count={}, utils_changed={}", len(records), before != after)
    logger.info("摘要输出: {}", summary_path)
    print(
        json.dumps(
            {
                k: summary[k]
                for k in ["mode", "thinking_mode", "effort", "elapsed_ms", "max_turns", "message_count", "message_class_counts", "utils_changed", "output_path"]
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return summary


def short_text(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def log_message(record: MessageRecord, state: LogState) -> None:
    summary = record.summary
    prefix = f"#{record.index:03d} {record.class_name}"
    if record.class_name == "SystemMessage":
        subtype = summary.get("subtype")
        data = summary.get("data") or {}
        if subtype == "thinking_tokens":
            state.record_thinking_tokens(data)
            logger.debug("{} | system subtype=thinking_tokens data={}", prefix, data)
            return
        state.flush_thinking_tokens(f"before {subtype}")
        if subtype in {"init", "api_retry", "hook_started", "hook_response", "thinking_tokens"}:
            logger.info("{} | system subtype={}", prefix, subtype)
        else:
            logger.debug("{} | system subtype={} data={}", prefix, subtype, data)
        if subtype == "init":
            logger.info(
                "    init: cwd={}, model={}, permissionMode={}, tools_count={}, plugins_count={}",
                data.get("cwd"),
                data.get("model"),
                data.get("permissionMode"),
                len(data.get("tools") or []),
                len(data.get("plugins") or []),
            )
        if subtype == "api_retry":
            logger.warning(
                "    api_retry: attempt={}/{} status={} delay_ms={}",
                data.get("attempt"),
                data.get("max_retries"),
                data.get("error_status"),
                data.get("retry_delay_ms"),
            )
        return

    if record.class_name == "AssistantMessage":
        state.flush_thinking_tokens("before AssistantMessage")
        for block in summary.get("content") or []:
            block_type = block.get("type")
            if block_type == "text":
                logger.info("{} | assistant text: {}", prefix, short_text(block.get("text", "")))
            elif block_type == "tool_use":
                logger.info("{} | tool_use: {} input={}", prefix, block.get("name"), block.get("input"))
            elif block_type == "thinking":
                logger.info(
                    "{} | assistant thinking captured: chars={}, preview={}",
                    prefix,
                    block.get("chars"),
                    block.get("preview"),
                )
            else:
                logger.debug("{} | assistant block: {}", prefix, block)
        return

    if record.class_name == "UserMessage":
        state.flush_thinking_tokens("before UserMessage")
        logger.info("{} | tool/user result: {}", prefix, short_text(summary.get("content", "")))
        return

    if record.class_name == "ResultMessage":
        state.flush_thinking_tokens("before ResultMessage")
        logger.info(
            "{} | result: subtype={}, is_error={}, turns={}, cost={}, stop_reason={}",
            prefix,
            summary.get("subtype"),
            summary.get("is_error"),
            summary.get("num_turns"),
            summary.get("total_cost_usd"),
            summary.get("stop_reason"),
        )
        if summary.get("result"):
            logger.info("    final result: {}", short_text(summary["result"], 500))
        return

    if record.class_name == "ProbeException":
        state.flush_thinking_tokens("before ProbeException")
        logger.error("{} | exception: {} {}", prefix, summary.get("error_type"), summary.get("message"))
        return

    logger.debug("{} | summary={}", prefix, summary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Claude Agent SDK chapter 1 query quickstart probe.")
    parser.add_argument("--mode", choices=["readonly", "edit"], default="readonly")
    parser.add_argument("--config-mode", choices=["inherited", "isolated"], default="inherited")
    parser.add_argument("--profile", default="codefoxai_sonnet")
    parser.add_argument("--thinking-mode", choices=["adaptive", "disabled"], default="disabled")
    parser.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default="low")
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--compare-thinking", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.compare_thinking:
        async def compare() -> None:
            base = await run_probe(args.mode, args.config_mode, args.profile, "adaptive", args.effort, args.max_turns)
            disabled = await run_probe(args.mode, args.config_mode, args.profile, "disabled", args.effort, args.max_turns)
            compare_path = OUT_DIR / f"01_query_quickstart_{args.mode}_{args.config_mode}_thinking_compare.json"
            compare_payload = {"adaptive": base, "disabled": disabled}
            compare_path.write_text(json.dumps(compare_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            logger.info("thinking 对比输出: {}", compare_path)

        anyio.run(compare)
    else:
        anyio.run(run_probe, args.mode, args.config_mode, args.profile, args.thinking_mode, args.effort, args.max_turns)


if __name__ == "__main__":
    main()
