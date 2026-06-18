from __future__ import annotations

import json
import os
import shutil
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from loguru import logger
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)


ROOT = Path(__file__).resolve().parents[3]
LEARNING_DIR = ROOT / "drafts" / "260615_claude_sdk_learning"
OUT_DIR = LEARNING_DIR / "outputs"
PROFILE_FILE = LEARNING_DIR / "configs" / "claude_sdk_profiles.yaml"


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


def setup_logger(log_name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUT_DIR / f"{log_name}.log"
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


def prepare_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


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
            current_section = stripped[:-1]
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


def summarize_block(block: Any) -> dict[str, Any]:
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    if block.__class__.__name__ == "ThinkingBlock":
        thinking = getattr(block, "thinking", "")
        return {"type": "thinking", "chars": len(thinking), "preview": short_text(thinking, 180)}
    if isinstance(block, ToolUseBlock):
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    if isinstance(block, ToolResultBlock):
        return {"type": "tool_result", "tool_use_id": block.tool_use_id, "content": block.content, "is_error": block.is_error}
    return {"type": block.__class__.__name__, "repr": repr(block)}


def summarize_message(index: int, message: Any) -> MessageRecord:
    if isinstance(message, AssistantMessage):
        return MessageRecord(index, "AssistantMessage", {
            "model": message.model,
            "message_id": message.message_id,
            "session_id": message.session_id,
            "stop_reason": message.stop_reason,
            "usage": message.usage,
            "content": [summarize_block(block) for block in message.content],
        })
    if isinstance(message, UserMessage):
        return MessageRecord(index, "UserMessage", {"content": str(message.content)[:500]})
    if isinstance(message, ResultMessage):
        return MessageRecord(index, "ResultMessage", {
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
        })
    if isinstance(message, SystemMessage):
        return MessageRecord(index, "SystemMessage", {"subtype": message.subtype, "data": message.data})
    return MessageRecord(index, message.__class__.__name__, {"repr": repr(message)})


def write_record(path: Path, record: MessageRecord) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def count_message_classes(records: list[MessageRecord]) -> dict[str, int]:
    return dict(Counter(record.class_name for record in records))


def count_system_subtypes(records: list[MessageRecord]) -> dict[str, int]:
    return dict(Counter(str(r.summary.get("subtype") or "unknown") for r in records if r.class_name == "SystemMessage"))


def count_tool_usage(records: list[MessageRecord]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        if record.class_name != "AssistantMessage":
            continue
        for block in record.summary.get("content") or []:
            if block.get("type") == "tool_use":
                counter[str(block.get("name") or "unknown")] += 1
    return dict(counter)


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
            return
        state.flush_thinking_tokens(f"before {subtype}")
        logger.info("{} | system subtype={}", prefix, subtype)
        if subtype == "init":
            logger.info("    init: cwd={}, model={}, permissionMode={}, tools_count={}, plugins_count={}, session_id={}", data.get("cwd"), data.get("model"), data.get("permissionMode"), len(data.get("tools") or []), len(data.get("plugins") or []), data.get("session_id"))
        return
    if record.class_name == "AssistantMessage":
        state.flush_thinking_tokens("before AssistantMessage")
        for block in summary.get("content") or []:
            if block.get("type") == "text":
                logger.info("{} | assistant text: {}", prefix, short_text(block.get("text", "")))
            elif block.get("type") == "tool_use":
                logger.info("{} | tool_use: {} input={}", prefix, block.get("name"), block.get("input"))
            elif block.get("type") == "thinking":
                logger.info("{} | assistant thinking captured: chars={}", prefix, block.get("chars"))
        return
    if record.class_name == "UserMessage":
        state.flush_thinking_tokens("before UserMessage")
        logger.info("{} | tool/user result: {}", prefix, short_text(summary.get("content", "")))
        return
    if record.class_name == "ResultMessage":
        state.flush_thinking_tokens("before ResultMessage")
        logger.info("{} | result: subtype={}, is_error={}, turns={}, cost={}, session_id={}", prefix, summary.get("subtype"), summary.get("is_error"), summary.get("num_turns"), summary.get("total_cost_usd"), summary.get("session_id"))
        if summary.get("result"):
            logger.info("    final result: {}", short_text(summary["result"], 500))
        return
    if record.class_name == "ProbeException":
        state.flush_thinking_tokens("before ProbeException")
        logger.error("{} | exception: {} {}", prefix, summary.get("error_type"), summary.get("message"))
