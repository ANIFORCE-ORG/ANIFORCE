"""SDK 消息协议完整 dump 探针

目的：把 Claude SDK 返回的每种消息类型的完整字段结构 dump 成 JSON，
作为开发 AG-UI 适配器的协议依据。不复用学习手册已有的结论，而是
重新拿到权威的原始字段值。

场景：
  text   - 纯文本对话（无工具）：init / AssistantMessage / ResultMessage
  tool   - 工具调用：ToolUseBlock / ToolResultBlock / UserMessage
  stream - 流式：StreamEvent 的 event dict 所有子类型

用法：
  .venv/bin/python drafts/260617/260617_04_message_protocol_dump.py --scenario text
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

# 复用学习手册的通用模块（profile 加载 + 配置隔离）
LEARNING_DIR = Path(__file__).resolve().parents[1] / "260615_claude_sdk_learning"
sys.path.insert(0, str(LEARNING_DIR / "examples"))

from sdk_learning_common import load_profile_env, prepare_clean_dir, OUT_DIR  # noqa: E402
from claude_agent_sdk import (  # noqa: E402
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ResultMessage,
    StreamEvent,
    RateLimitEvent,
)


def to_serializable(obj: Any) -> Any:
    """把 dataclass / 嵌套结构转成可 JSON 序列化的 dict/list"""
    if is_dataclass(obj) and not isinstance(obj, type):
        d = asdict(obj)
        return d
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_serializable(x) for x in obj]
    return obj


def classify(msg: Any) -> str:
    """消息分类标签（用于按类型分组）"""
    tname = type(msg).__name__
    if isinstance(msg, SystemMessage):
        # SystemMessage 子类优先用具体类名
        return tname
    return tname


def build_env() -> dict[str, str]:
    """显式 env：只带 ANTHROPIC_* / CLAUDE_* + client app + 配置隔离"""
    env = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_")
    }
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-protocol-probe/0.1"
    env["CLAUDE_CONFIG_DIR"] = str(LEARNING_DIR / "examples" / "01_claude_config_sandbox")
    return env


async def run_text_scenario() -> dict[str, Any]:
    """场景1：纯文本对话，dump 完整字段"""
    print("\n[场景1] 纯文本对话（无工具）")
    sandbox = Path(__file__).parent / "sandbox_text"
    prepare_clean_dir(sandbox)

    opts = ClaudeAgentOptions(
        cwd=str(sandbox),
        model=os.getenv("CLAUDE_AGENT_MODEL", "claude-sonnet-4-6"),
        max_turns=2,
        allowed_tools=[],
        disallowed_tools=["Write", "Edit", "Bash"],
        permission_mode="dontAsk",
        system_prompt="You are a protocol probe. Reply briefly in Chinese.",
        env=build_env(),
        thinking={"type": "disabled"},
        effort="low",
    )

    messages_raw: list[dict[str, Any]] = []
    by_type: dict[str, list[int]] = {}

    async for msg in query(prompt="你好，请用一句话介绍你自己", options=opts):
        idx = len(messages_raw)
        record = {
            "index": idx,
            "class": classify(msg),
            "data": to_serializable(msg),
        }
        # 对 SystemMessage 记录 subtype
        if isinstance(msg, SystemMessage):
            record["subtype"] = msg.subtype
        messages_raw.append(record)
        by_type.setdefault(record["class"], []).append(idx)
        print(f"  [{idx}] {record['class']}" + (
            f" subtype={msg.subtype}" if isinstance(msg, SystemMessage) else ""
        ))

    return {
        "scenario": "text",
        "prompt": "你好，请用一句话介绍你自己",
        "message_count": len(messages_raw),
        "by_type": by_type,
        "messages": messages_raw,
    }


async def run_tool_scenario() -> dict[str, Any]:
    """场景2：工具调用，dump ToolUseBlock / ToolResultBlock / UserMessage"""
    print("\n[场景2] 工具调用（Read 文件）")
    sandbox = Path(__file__).parent / "sandbox_tool"
    prepare_clean_dir(sandbox)
    # 放一个文件让 Read 读取
    (sandbox / "target.txt").write_text("ANIFORCE protocol probe target file.\n", encoding="utf-8")

    opts = ClaudeAgentOptions(
        cwd=str(sandbox),
        model=os.getenv("CLAUDE_AGENT_MODEL", "claude-sonnet-4-6"),
        max_turns=3,
        allowed_tools=["Read"],
        disallowed_tools=["Write", "Edit", "Bash"],
        permission_mode="dontAsk",
        system_prompt="You are a protocol probe. Read target.txt then summarize it in one Chinese sentence.",
        env=build_env(),
        thinking={"type": "disabled"},
        effort="low",
    )

    messages_raw: list[dict[str, Any]] = []
    by_type: dict[str, list[int]] = {}

    async for msg in query(prompt="请读取 target.txt 并用一句话总结内容", options=opts):
        idx = len(messages_raw)
        record = {
            "index": idx,
            "class": classify(msg),
            "data": to_serializable(msg),
        }
        if isinstance(msg, SystemMessage):
            record["subtype"] = msg.subtype
        messages_raw.append(record)
        by_type.setdefault(record["class"], []).append(idx)
        # 对 AssistantMessage 标注 content block 类型
        if isinstance(msg, AssistantMessage):
            block_types = [type(b).__name__ for b in msg.content]
            print(f"  [{idx}] {record['class']} blocks={block_types}")
        else:
            print(f"  [{idx}] {record['class']}" + (
                f" subtype={msg.subtype}" if isinstance(msg, SystemMessage) else ""
            ))

    return {
        "scenario": "tool",
        "prompt": "请读取 target.txt 并用一句话总结内容",
        "message_count": len(messages_raw),
        "by_type": by_type,
        "messages": messages_raw,
    }


async def run_stream_scenario() -> dict[str, Any]:
    """场景3：流式，dump StreamEvent 的 event dict 所有子类型"""
    print("\n[场景3] 流式（include_partial_messages=True）")
    sandbox = Path(__file__).parent / "sandbox_stream"
    prepare_clean_dir(sandbox)

    opts = ClaudeAgentOptions(
        cwd=str(sandbox),
        model=os.getenv("CLAUDE_AGENT_MODEL", "claude-sonnet-4-6"),
        max_turns=1,
        allowed_tools=[],
        disallowed_tools=["Write", "Edit", "Bash"],
        permission_mode="dontAsk",
        system_prompt="You are a protocol probe. Reply with one short Chinese sentence.",
        env=build_env(),
        thinking={"type": "disabled"},
        effort="low",
        include_partial_messages=True,  # 关键：启用流式
    )

    messages_raw: list[dict[str, Any]] = []
    by_type: dict[str, list[int]] = {}
    stream_event_types: dict[str, list[int]] = {}

    async for msg in query(prompt="你好", options=opts):
        idx = len(messages_raw)
        record = {
            "index": idx,
            "class": classify(msg),
            "data": to_serializable(msg),
        }
        if isinstance(msg, SystemMessage):
            record["subtype"] = msg.subtype
        # 对 StreamEvent 提取 event.type
        if isinstance(msg, StreamEvent):
            etype = msg.event.get("type", "unknown")
            record["stream_event_type"] = etype
            stream_event_types.setdefault(etype, []).append(idx)
        messages_raw.append(record)
        by_type.setdefault(record["class"], []).append(idx)
        label = record["class"]
        if isinstance(msg, SystemMessage):
            label += f" subtype={msg.subtype}"
        elif isinstance(msg, StreamEvent):
            label += f" event_type={msg.event.get('type')}"
        print(f"  [{idx}] {label}")

    return {
        "scenario": "stream",
        "prompt": "你好",
        "message_count": len(messages_raw),
        "by_type": by_type,
        "stream_event_types": stream_event_types,
        "messages": messages_raw,
    }


async def main(scenario: str):
    load_profile_env("copilot_sonnet")

    if scenario == "text":
        result = await run_text_scenario()
    elif scenario == "tool":
        result = await run_tool_scenario()
    elif scenario == "stream":
        result = await run_stream_scenario()
    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    # 写入输出（覆盖模式）
    out_file = OUT_DIR / f"260617_04_protocol_dump_{scenario}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print(f"场景: {scenario}")
    print(f"消息总数: {result['message_count']}")
    print(f"按类型分组: {result['by_type']}")
    if scenario == "stream":
        print(f"StreamEvent 子类型: {result.get('stream_event_types')}")
    print(f"输出: {out_file}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["text", "tool", "stream"], default="text")
    args = parser.parse_args()
    asyncio.run(main(args.scenario))
