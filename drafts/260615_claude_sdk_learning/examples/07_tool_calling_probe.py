from __future__ import annotations

import argparse
import json
import os
from typing import Any

import anyio
from loguru import logger
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, StreamEvent, ResultMessage
from claude_agent_sdk.types import ToolPermissionContext, PermissionResultAllow


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

# 第 7 章主题：Tool Calling 工具调用。
# 验证目标：
# 1. 工具调用消息流：ToolUseBlock 何时出现？是否增量？
# 2. 工具执行结果：ToolResultBlock 何时出现？格式是什么？
# 3. 多轮工具调用：一个 response 可能包含多少次工具调用？
# 4. 工具调用与 thinking 的交互：是否先 thinking 再 tool_use？
#
# 策略：
# - 配置一个简单工具（get_current_time）
# - 用一个会触发工具调用的 prompt
# - 详细记录所有消息，特别关注 ToolUseBlock / ToolResultBlock

CLAUDE_CONFIG_SANDBOX = LEARNING_DIR / "examples" / "07_claude_config_sandbox"


async def auto_allow_permission(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    """自动批准所有工具调用"""
    logger.debug("自动批准工具调用: tool={}, input={}", tool_name, tool_input)
    return PermissionResultAllow()


def build_options(profile: str) -> ClaudeAgentOptions:
    load_profile_env(profile)
    env = {k: v for k, v in os.environ.items() if k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_")}
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-sdk-learning/0.7-tool-calling-probe"
    env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_SANDBOX)
    model = os.getenv("CLAUDE_AGENT_MODEL", "claude-opus-4-6")

    # 使用内置工具：Bash, Read, Write
    # SDK 的 tools 参数是内置工具名称列表，不是自定义工具定义
    tools = ["Bash", "Read"]

    return ClaudeAgentOptions(
        model=model,
        max_turns=5,
        tools=tools,
        system_prompt="You are a helpful assistant with access to tools.",
        env=env,
        thinking={"type": "adaptive"},
        effort="low",
        can_use_tool=auto_allow_permission,  # 自动批准回调
        include_partial_messages=True,  # 🔑 启用流式，观察工具调用的流式行为
    )


async def main_async(args: argparse.Namespace) -> None:
    setup_logger("07_tool_calling_probe")
    logger.info("开始第 7 章 Tool Calling 工具调用验证: profile={}", args.profile)
    options = build_options(args.profile)

    output_path = OUT_DIR / "07_tool_calling_probe.jsonl"
    output_path.unlink(missing_ok=True)
    records: list = []
    log_state = LogState()

    # 用一个会触发工具调用的 prompt（使用 Read 和 Bash）
    prompt = "Read the file /etc/hostname and tell me what's in it."

    async with ClaudeSDKClient(options=options) as client:
        logger.info("发出 query: {}", prompt)
        await client.query(prompt)

        tool_use_blocks = []
        tool_result_blocks = []
        stream_events = []  # 记录流式事件

        async for message in client.receive_messages():  # 改用 receive_messages 才能收到 StreamEvent
            record = summarize_message(len(records), message)
            records.append(record)
            log_message(record, log_state)
            write_record(output_path, record)

            # 记录 StreamEvent
            if isinstance(message, StreamEvent):
                event_type = message.event.get('type')
                stream_events.append({
                    "type": event_type,
                    "event": message.event,
                })
                logger.info("StreamEvent | type={}", event_type)

                # 特别关注 tool_use 相关的流式事件
                if 'tool' in event_type.lower():
                    logger.info("  工具相关事件: {}", str(message.event)[:300])

            # 收集 ToolUseBlock 和 ToolResultBlock
            if record.class_name == "AssistantMessage":
                for block in record.summary.get("content", []):
                    if block["type"] == "tool_use":
                        tool_use_blocks.append({
                            "message_index": record.index,
                            "id": block.get("id"),
                            "name": block.get("name"),
                            "input": block.get("input"),
                        })
            elif record.class_name == "UserMessage":
                # UserMessage 的 content 可能是字符串表示或列表，需要检查
                content = record.summary.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            tool_result_blocks.append({
                                "message_index": record.index,
                                "tool_use_id": block.get("tool_use_id"),
                                "is_error": block.get("is_error"),
                                "content_preview": str(block.get("content"))[:200],
                            })
                # 如果 content 是字符串（序列化的 repr），记录但不解析
                elif isinstance(content, str) and "ToolResultBlock" in content:
                    tool_result_blocks.append({
                        "message_index": record.index,
                        "raw_content_preview": content[:200],
                    })

    summary = {
        "profile": args.profile,
        "prompt": prompt,
        "total_messages": len(records),
        "tool_use_count": len(tool_use_blocks),
        "tool_result_count": len(tool_result_blocks),
        "tool_use_blocks": tool_use_blocks,
        "tool_result_blocks": tool_result_blocks,
        "message_class_counts": count_message_classes(records),
    }

    summary_path = OUT_DIR / "07_tool_calling_probe_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    logger.info("总消息数: {}", len(records))
    logger.info("ToolUse 数量: {}", len(tool_use_blocks))
    logger.info("ToolResult 数量: {}", len(tool_result_blocks))
    logger.info("第 7 章摘要已写出: {}", summary_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 7: Tool calling behavior probe.")
    parser.add_argument("--profile", default="codefoxai_sonnet")
    return parser.parse_args()


def main() -> None:
    anyio.run(main_async, parse_args())


if __name__ == "__main__":
    main()
