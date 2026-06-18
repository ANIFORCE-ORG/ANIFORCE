from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import anyio
from loguru import logger
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, AssistantMessage, UserMessage, ResultMessage, SystemMessage
from claude_agent_sdk.types import ToolPermissionContext, PermissionResultAllow


from sdk_learning_common import (
    LEARNING_DIR,
    OUT_DIR,
    load_profile_env,
    setup_logger,
)

# 第 7.5 章主题：cwd 工作目录隔离验证
# 验证目标：
# 1. 不设置 cwd 时，能否读取项目外的系统文件（如 /etc/hostname）？
# 2. 设置 cwd 到 sandbox 后，能否读取 sandbox 外的文件？
# 3. 设置 cwd 后，能否读取 sandbox 内的文件？
# 4. add_dirs 参数的作用是什么？
#
# 策略：
# - 创建临时 sandbox 目录
# - 在 sandbox 内创建测试文件
# - 运行 3 个独立测试：
#   A. 无限制（不设置 cwd）- 尝试读 /etc/hostname
#   B. 有 cwd 限制 - 尝试读 sandbox 外的文件（项目根 README.md）
#   C. 有 cwd 限制 - 尝试读 sandbox 内的文件

CLAUDE_CONFIG_SANDBOX = LEARNING_DIR / "examples" / "07_claude_config_sandbox"  # 复用第 7 章配置
TEST_SANDBOX = OUT_DIR / "07.5_test_sandbox"


async def auto_allow_permission(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    """自动批准所有工具调用"""
    logger.debug("自动批准工具调用: tool={}, input={}", tool_name, tool_input)
    return PermissionResultAllow()


def prepare_sandbox():
    """准备测试 sandbox"""
    TEST_SANDBOX.mkdir(parents=True, exist_ok=True)

    # 在 sandbox 内创建测试文件
    test_file = TEST_SANDBOX / "allowed_file.txt"
    test_file.write_text("This file is INSIDE the sandbox.\n", encoding="utf-8")

    logger.info("测试 sandbox 已创建: {}", TEST_SANDBOX)
    logger.info("sandbox 内测试文件: {}", test_file)


def build_options(profile: str, cwd: str | None = None, add_dirs: list[str] | None = None) -> ClaudeAgentOptions:
    load_profile_env(profile)
    env = {k: v for k, v in os.environ.items() if k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_")}
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-sdk-learning/0.75-cwd-isolation-probe"
    env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_SANDBOX)
    model = os.getenv("CLAUDE_AGENT_MODEL", "claude-opus-4-6")

    tools = ["Read"]  # 只需要 Read 工具

    opts = {
        "model": model,
        "max_turns": 5,
        "tools": tools,
        "system_prompt": "You are a helpful assistant with access to tools.",
        "env": env,
        "thinking": {"type": "adaptive"},
        "effort": "low",
        "can_use_tool": auto_allow_permission,
        "include_partial_messages": True,  # 🔑 必须启用才能看到工具调用！
    }

    if cwd is not None:
        opts["cwd"] = cwd

    if add_dirs is not None:
        opts["add_dirs"] = add_dirs

    return ClaudeAgentOptions(**opts)


async def run_test(label: str, options: ClaudeAgentOptions, prompt: str) -> dict[str, Any]:
    """运行单个测试"""
    logger.info("=" * 60)
    logger.info("测试: {}", label)
    logger.info("Prompt: {}", prompt)
    logger.info("Options: cwd={}, add_dirs={}",
                getattr(options, 'cwd', None),
                getattr(options, 'add_dirs', None))

    result = {
        "label": label,
        "prompt": prompt,
        "cwd": getattr(options, 'cwd', None),
        "add_dirs": getattr(options, 'add_dirs', None),
        "success": False,
        "final_text": None,
        "error_message": None,
        "tool_calls": [],
        "tool_results": [],
    }

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            # 使用 receive_messages() 来捕获所有消息，包括工具调用
            async for message in client.receive_messages():
                if isinstance(message, SystemMessage):
                    continue  # 跳过系统消息

                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        if hasattr(block, 'type'):
                            if block.type == 'tool_use':
                                tool_call = {
                                    "name": block.name,
                                    "input": block.input,
                                }
                                result["tool_calls"].append(tool_call)
                                logger.info("  🔧 工具调用: {} with {}", block.name, block.input)
                            elif block.type == 'text':
                                result["final_text"] = block.text
                                logger.info("  💬 文本响应: {}", block.text[:200])

                elif isinstance(message, UserMessage):
                    # UserMessage.content 可能是列表
                    content = message.content if isinstance(message.content, list) else []
                    for block in content:
                        if hasattr(block, 'type') and block.type == 'tool_result':
                            tool_result = {
                                "tool_use_id": block.tool_use_id,
                                "is_error": block.is_error,
                                "content": str(block.content)[:500],
                            }
                            result["tool_results"].append(tool_result)
                            logger.info("  ✅ 工具结果: is_error={}, content={}",
                                       block.is_error,
                                       str(block.content)[:100])

                elif isinstance(message, ResultMessage):
                    result["success"] = not message.is_error
                    if not result["final_text"]:
                        result["final_text"] = message.result
                    if message.is_error:
                        result["error_message"] = str(message.result)[:500]
                    logger.info("  🏁 ResultMessage: success={}, turns={}",
                               result["success"],
                               message.num_turns)
                    break

    except Exception as e:
        result["error_message"] = str(e)
        logger.error("测试失败: {}", e)

    logger.info("结果: success={}, tool_calls={}, final_text={}",
                result["success"],
                len(result["tool_calls"]),
                result["final_text"][:100] if result["final_text"] else None)

    return result


async def main_async(args: argparse.Namespace) -> None:
    setup_logger("07.5_cwd_isolation_probe")
    logger.info("开始第 7.5 章 cwd 工作目录隔离验证: profile={}", args.profile)

    # 准备测试环境
    prepare_sandbox()

    results = []

    # 测试 A: 无限制 - 尝试读取系统文件
    logger.info("\n" + "=" * 60)
    logger.info("测试 A: 无 cwd 限制 - 尝试读取系统文件")
    options_a = build_options(args.profile, cwd=None)
    result_a = await run_test(
        label="A_no_restriction",
        options=options_a,
        prompt="Read the file /etc/hostname and tell me what's in it."  # 和第 7 章完全一致
    )
    results.append(result_a)

    # 测试 B: 有 cwd 限制 - 尝试读取 sandbox 外的文件
    logger.info("\n" + "=" * 60)
    logger.info("测试 B: 有 cwd 限制 - 尝试读取 sandbox 外的文件")
    options_b = build_options(args.profile, cwd=str(TEST_SANDBOX))
    result_b = await run_test(
        label="B_restricted_read_outside",
        options=options_b,
        prompt="Read the file ../README.md and tell me what's in it."
    )
    results.append(result_b)

    # 测试 C: 有 cwd 限制 - 尝试读取 sandbox 内的文件
    logger.info("\n" + "=" * 60)
    logger.info("测试 C: 有 cwd 限制 - 尝试读取 sandbox 内的文件")
    options_c = build_options(args.profile, cwd=str(TEST_SANDBOX))
    result_c = await run_test(
        label="C_restricted_read_inside",
        options=options_c,
        prompt="Read the file allowed_file.txt and tell me what's in it."
    )
    results.append(result_c)

    # 测试 D: 尝试用绝对路径逃逸 sandbox
    logger.info("\n" + "=" * 60)
    logger.info("测试 D: 有 cwd 限制 - 尝试用绝对路径逃逸")
    options_d = build_options(args.profile, cwd=str(TEST_SANDBOX))
    result_d = await run_test(
        label="D_restricted_absolute_path_escape",
        options=options_d,
        prompt="Read the file /etc/hostname and tell me what's in it."
    )
    results.append(result_d)

    # 输出摘要
    summary = {
        "profile": args.profile,
        "sandbox_path": str(TEST_SANDBOX),
        "test_results": results,
        "conclusions": {
            "A_no_restriction": "success" if result_a["success"] else "failed",
            "B_restricted_read_outside": "blocked" if not result_b["success"] or "error" in (result_b["final_text"] or "").lower() else "allowed",
            "C_restricted_read_inside": "success" if result_c["success"] else "failed",
            "D_restricted_absolute_path_escape": "blocked" if not result_d["success"] or "error" in (result_d["final_text"] or "").lower() else "allowed",
        }
    }

    summary_path = OUT_DIR / "07.5_cwd_isolation_probe_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成摘要:")
    logger.info("A (无限制读系统文件): {}", summary["conclusions"]["A_no_restriction"])
    logger.info("B (有限制读 sandbox 外): {}", summary["conclusions"]["B_restricted_read_outside"])
    logger.info("C (有限制读 sandbox 内): {}", summary["conclusions"]["C_restricted_read_inside"])
    logger.info("D (有限制用绝对路径逃逸): {}", summary["conclusions"]["D_restricted_absolute_path_escape"])
    logger.info("摘要已写出: {}", summary_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 7.5: cwd isolation behavior probe.")
    parser.add_argument("--profile", default="codefoxai_sonnet")
    return parser.parse_args()


def main() -> None:
    anyio.run(main_async, parse_args())


if __name__ == "__main__":
    main()
