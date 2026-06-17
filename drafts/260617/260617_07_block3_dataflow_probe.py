"""
Block 3 数据流动探针

目的：把 Claude SDK 消息流 → AG-UI 适配层 → SSE 输出的完整数据流可视化。
每条 SDK 消息进来打详细 log，适配层输出的每个 AG-UI 事件也打 log，
让"消息怎么被翻译"一目了然。

用法：
  .venv/bin/python drafts/260617/260617_07_block3_dataflow_probe.py --scenario text
  .venv/bin/python drafts/260617/260617_07_block3_dataflow_probe.py --scenario tool

日志输出：
  - 控制台（彩色）
  - drafts/260615_claude_sdk_learning/outputs/260617_07_block3_dataflow_{scenario}.log
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from loguru import logger

# 路径
LEARNING_DIR = Path(__file__).resolve().parents[1] / "260615_claude_sdk_learning"
ANIFORCE_AGENT = LEARNING_DIR.parent.parent / "aniforce-agent"
sys.path.insert(0, str(LEARNING_DIR / "examples"))
sys.path.insert(0, str(ANIFORCE_AGENT))

from sdk_learning_common import load_profile_env, prepare_clean_dir, OUT_DIR  # noqa: E402
from claude_agent_sdk import (  # noqa: E402
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
)
from app.services.copilotkit_adapter import CopilotKitAdapter  # noqa: E402

# 统计计数器
STATS = {
    "sdk_messages": 0,
    "sdk_by_type": {},
    "agui_events": 0,
    "agui_by_type": {},
    "text_chars": 0,
    "tool_calls": 0,
}


def setup_logger(scenario: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUT_DIR / f"260617_07_block3_dataflow_{scenario}.log"
    logger.remove()
    # 控制台：彩色精简
    logger.add(
        lambda m: print(m, end=""),
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <7}</level> | {message}",
        level="INFO",
        colorize=True,
    )
    # 文件：完整
    logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | {message}",
        level="DEBUG",
        encoding="utf-8",
        mode="w",
    )
    return log_path


def short(s: str, limit: int = 80) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def log_sdk_message(idx: int, msg: Any) -> None:
    """详细打印每条 SDK 消息"""
    STATS["sdk_messages"] = idx
    tname = type(msg).__name__
    STATS["sdk_by_type"][tname] = STATS["sdk_by_type"].get(tname, 0) + 1

    logger.info("━━━ SDK 消息 #{} ━━━ {}", idx, tname)

    if isinstance(msg, SystemMessage):
        subtype = msg.subtype
        # thinking_tokens 太多，只计数不详细打
        if subtype == "thinking_tokens":
            tokens = msg.data.get("estimated_tokens")
            logger.debug("    SystemMessage(thinking_tokens) estimated_tokens={}", tokens)
            return
        logger.debug("    subtype={}", subtype)
        if subtype == "init":
            d = msg.data
            logger.debug("    init: model={} apiKeySource={} tools_count={} session_id={}",
                         d.get("model"), d.get("apiKeySource"),
                         len(d.get("tools") or []), d.get("session_id"))
        elif subtype == "api_retry":
            d = msg.data
            logger.warning("    api_retry: status={} attempt={}/{} error={}",
                          d.get("error_status"), d.get("attempt"),
                          d.get("max_retries"), short(d.get("error", ""), 120))
        else:
            logger.debug("    data keys={}", list(msg.data.keys()))
        return

    if isinstance(msg, StreamEvent):
        event = msg.event
        etype = event.get("type")
        index = event.get("index")
        if etype == "content_block_start":
            block = event.get("content_block", {})
            logger.debug("    StreamEvent(content_block_start) index={} block_type={}",
                         index, block.get("type"))
        elif etype == "content_block_delta":
            delta = event.get("delta", {})
            dtype = delta.get("type")
            if dtype == "text_delta":
                text = delta.get("text", "")
                logger.debug("    StreamEvent(text_delta) index={} text={!r}", index, short(text, 40))
            else:
                logger.debug("    StreamEvent(delta) index={} delta_type={}", index, dtype)
        elif etype == "content_block_stop":
            logger.debug("    StreamEvent(content_block_stop) index={}", index)
        elif etype == "message_start":
            m = event.get("message", {})
            logger.debug("    StreamEvent(message_start) model={}", m.get("model"))
        elif etype in ("message_delta", "message_stop"):
            logger.debug("    StreamEvent({}) {}", etype, short(json.dumps(event.get("delta", {})), 60))
        else:
            logger.debug("    StreamEvent({})", etype)
        return

    if isinstance(msg, AssistantMessage):
        blocks = msg.content
        block_types = [type(b).__name__ for b in blocks]
        logger.debug("    AssistantMessage blocks={} message_id={}", block_types, msg.message_id)
        for i, b in enumerate(blocks):
            if isinstance(b, TextBlock):
                logger.debug("      [{}] TextBlock text={!r}", i, short(b.text, 60))
            elif isinstance(b, ThinkingBlock):
                logger.debug("      [{}] ThinkingBlock chars={}", i, len(b.thinking))
            elif isinstance(b, ToolUseBlock):
                logger.debug("      [{}] ToolUseBlock id={} name={} input={}",
                             i, b.id, b.name, short(json.dumps(b.input, ensure_ascii=False), 60))
        return

    if isinstance(msg, UserMessage):
        content = msg.content
        if isinstance(content, list):
            for i, b in enumerate(content):
                if isinstance(b, ToolResultBlock):
                    logger.debug("    UserMessage[{}] ToolResultBlock tool_use_id={} is_error={} content={!r}",
                                 i, b.tool_use_id, b.is_error, short(str(b.content), 60))
                else:
                    logger.debug("    UserMessage[{}] {}", i, type(b).__name__)
        else:
            logger.debug("    UserMessage content={!r}", short(str(content), 60))
        return

    if isinstance(msg, ResultMessage):
        logger.debug("    ResultMessage subtype={} is_error={} turns={} cost={} duration_ms={} stop_reason={}",
                     msg.subtype, msg.is_error, msg.num_turns,
                     msg.total_cost_usd, msg.duration_ms, msg.stop_reason)
        return

    logger.debug("    (未知类型) {}", tname)


def log_agui_event(sse: str) -> None:
    """打印适配层输出的每个 AG-UI 事件"""
    STATS["agui_events"] += 1
    # 解析 SSE: "event: TYPE\ndata: JSON\n\n"
    lines = sse.strip().split("\n")
    evt_type = ""
    data = {}
    for line in lines:
        if line.startswith("event: "):
            evt_type = line[7:]
        elif line.startswith("data: "):
            try:
                data = json.loads(line[6:])
            except Exception:
                data = {"raw": line[6:]}

    STATS["agui_by_type"][evt_type] = STATS["agui_by_type"].get(evt_type, 0) + 1

    # 追踪统计
    if evt_type == "TextMessageContent":
        STATS["text_chars"] += len(data.get("content", ""))
    if evt_type == "ActionExecutionStart":
        STATS["tool_calls"] += 1

    # 精简打印 data
    data_preview = short(json.dumps(data, ensure_ascii=False), 100)
    logger.info(">>> AG-UI 事件 #{}: {} | {}", STATS["agui_events"], evt_type, data_preview)


async def logging_wrapper(sdk_gen):
    """包装 SDK 消息流，每条消息打 log 后再 yield"""
    idx = 0
    async for msg in sdk_gen:
        idx += 1
        log_sdk_message(idx, msg)
        yield msg


def build_env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_")
    }
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-block3-probe/0.1"
    env["CLAUDE_CONFIG_DIR"] = str(LEARNING_DIR / "examples" / "01_claude_config_sandbox")
    return env


async def run(scenario: str) -> bool:
    load_profile_env("copilot_sonnet")

    sandbox = Path(__file__).parent / f"sandbox_dataflow_{scenario}"
    prepare_clean_dir(sandbox)

    if scenario == "text":
        prompt = "你好，请用一句话介绍你自己"
    else:
        # 工具场景：放个文件让 Read 读
        (sandbox / "target.txt").write_text("ANIFORCE Block3 数据流探针目标文件。\n", encoding="utf-8")
        prompt = "请读取 target.txt 并用一句话总结内容"

    options = ClaudeAgentOptions(
        cwd=str(sandbox),
        model=os.getenv("CLAUDE_AGENT_MODEL", "claude-sonnet-4-6"),
        max_turns=3 if scenario == "tool" else 2,
        allowed_tools=["Read", "Glob"] if scenario == "tool" else [],
        disallowed_tools=["Write", "Edit", "Bash"],
        permission_mode="dontAsk",
        system_prompt="You are a dataflow probe. Reply briefly in Chinese.",
        env=build_env(),
        thinking={"type": "disabled"},
        effort="low",
        include_partial_messages=True,
    )

    logger.info("═══ Block 3 数据流探针启动 ═══")
    logger.info("场景: {}", scenario)
    logger.info("Prompt: {}", prompt)
    logger.info("模型: {}", os.getenv("CLAUDE_AGENT_MODEL"))
    logger.info("sandbox: {}", sandbox)
    logger.info("")

    # 1. 启动 SDK 消息流
    logger.info("▶ 启动 Claude SDK query()...")
    sdk_messages = query(prompt=prompt, options=options)

    # 2. 包一层打 log
    wrapped = logging_wrapper(sdk_messages)

    # 3. 喂给适配层，消费 SSE 输出
    logger.info("▶ 喂给 CopilotKitAdapter.stream_ag_ui_events()...")
    logger.info("")
    try:
        async for sse in CopilotKitAdapter.stream_ag_ui_events("probe_task_001", wrapped):
            log_agui_event(sse)
    except Exception as e:
        logger.error("适配层异常: {}", e, exc_info=True)
        return False

    # 4. 汇总
    logger.info("")
    logger.info("═══ 数据流汇总 ═══")
    logger.info("SDK 消息总数: {}", STATS["sdk_messages"])
    logger.info("SDK 消息类型分布: {}", json.dumps(STATS["sdk_by_type"], ensure_ascii=False))
    logger.info("AG-UI 事件总数: {}", STATS["agui_events"])
    logger.info("AG-UI 事件类型分布: {}", json.dumps(STATS["agui_by_type"], ensure_ascii=False))
    logger.info("文本字符数: {}", STATS["text_chars"])
    logger.info("工具调用数: {}", STATS["tool_calls"])
    logger.info("═══ 探针结束 ═══")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["text", "tool"], default="text")
    args = parser.parse_args()
    log_path = setup_logger(args.scenario)
    ok = asyncio.run(run(args.scenario))
    print(f"\n日志已写入: {log_path}")
    sys.exit(0 if ok else 1)
