from __future__ import annotations

import argparse
import json
import os
from typing import Any

import anyio
from loguru import logger
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, AssistantMessage, UserMessage, ResultMessage
from claude_agent_sdk.types import (
    ToolPermissionContext,
    PermissionResultAllow,
    PermissionResultDeny,
)

from sdk_learning_common import (
    LEARNING_DIR,
    OUT_DIR,
    load_profile_env,
    setup_logger,
)

# 第 7 章主题：Permissions 工具权限控制
# 验证目标：
# 1. permission_mode 的 5 种模式行为差异
# 2. can_use_tool 回调拦截能力
# 3. allowed_tools vs disallowed_tools
# 4. 权限拒绝后的消息流

CLAUDE_CONFIG_SANDBOX = LEARNING_DIR / "examples" / "07_permissions_sandbox"


async def always_allow_callback(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    """总是批准"""
    logger.debug("权限回调: 批准 {} with {}", tool_name, tool_input)
    return PermissionResultAllow()


async def deny_write_callback(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    """拒绝 Write 工具"""
    if tool_name == "Write":
        logger.info("权限回调: 拒绝 Write 工具")
        return PermissionResultDeny(
            message="Write tool is not allowed in this session",
            interrupt=False  # 不中断，让 Claude 看到拒绝消息
        )
    return PermissionResultAllow()


async def redirect_write_callback(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    """重定向 Write 到 sandbox"""
    if tool_name == "Write":
        original_path = tool_input.get("file_path", "")
        safe_path = f"./sandbox/{original_path}"
        logger.info("权限回调: 重定向 Write {} -> {}", original_path, safe_path)
        return PermissionResultAllow(
            updated_input={**tool_input, "file_path": safe_path}
        )
    return PermissionResultAllow()


def build_options(profile: str, test_case: str) -> ClaudeAgentOptions:
    load_profile_env(profile)
    env = {k: v for k, v in os.environ.items() if k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_")}
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-sdk-learning/0.7-permissions-probe"
    env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_SANDBOX)
    model = os.getenv("CLAUDE_AGENT_MODEL", "claude-opus-4-6")

    base_opts = {
        "model": model,
        "max_turns": 3,
        "tools": ["Read", "Write"],  # 只测试这两个工具
        "system_prompt": "You are a helpful assistant.",
        "env": env,
        "thinking": {"type": "disabled"},
        "effort": "low",
    }

    # 根据测试用例配置不同的权限选项
    if test_case == "default":
        # 测试 A: 默认模式（会提示用户）
        return ClaudeAgentOptions(
            **base_opts,
            permission_mode="default",
        )

    elif test_case == "accept_edits":
        # 测试 B: 自动接受编辑
        return ClaudeAgentOptions(
            **base_opts,
            permission_mode="acceptEdits",
        )

    elif test_case == "allowed_tools":
        # 测试 C: allowed_tools（Read 自动批准，Write 走 permission_mode）
        return ClaudeAgentOptions(
            **base_opts,
            permission_mode="default",
            allowed_tools=["Read"],  # 只允许 Read
        )

    elif test_case == "disallowed_tools":
        # 测试 D: disallowed_tools（完全禁止 Write）
        return ClaudeAgentOptions(
            **base_opts,
            permission_mode="acceptEdits",
            disallowed_tools=["Write"],  # 禁止 Write
        )

    elif test_case == "callback_deny":
        # 测试 E: can_use_tool 回调拒绝
        return ClaudeAgentOptions(
            **base_opts,
            permission_mode="default",
            can_use_tool=deny_write_callback,
        )

    elif test_case == "callback_redirect":
        # 测试 F: can_use_tool 回调重定向
        return ClaudeAgentOptions(
            **base_opts,
            permission_mode="acceptEdits",
            can_use_tool=redirect_write_callback,
        )

    else:
        raise ValueError(f"Unknown test case: {test_case}")


async def run_test(label: str, options: ClaudeAgentOptions, prompt: str) -> dict[str, Any]:
    """运行单个权限测试"""
    logger.info("=" * 60)
    logger.info("测试: {}", label)
    logger.info("Prompt: {}", prompt)

    result = {
        "label": label,
        "prompt": prompt,
        "permission_mode": getattr(options, 'permission_mode', None),
        "allowed_tools": getattr(options, 'allowed_tools', []),
        "disallowed_tools": getattr(options, 'disallowed_tools', []),
        "has_callback": options.can_use_tool is not None,
        "success": False,
        "tool_calls": [],
        "tool_results": [],
        "permission_denials": [],
        "final_text": None,
        "error_message": None,
    }

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            async for message in client.receive_messages():
                if isinstance(message, AssistantMessage):
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
                    content = message.content if isinstance(message.content, list) else []
                    for block in content:
                        if hasattr(block, 'type') and block.type == 'tool_result':
                            tool_result = {
                                "tool_use_id": block.tool_use_id,
                                "is_error": block.is_error,
                                "content": str(block.content)[:200],
                            }
                            result["tool_results"].append(tool_result)
                            logger.info("  ✅ 工具结果: is_error={}", block.is_error)

                elif isinstance(message, ResultMessage):
                    result["success"] = not message.is_error
                    if not result["final_text"]:
                        result["final_text"] = message.result
                    if message.is_error:
                        result["error_message"] = str(message.result)[:500]

                    # 检查权限拒绝
                    if message.permission_denials:
                        result["permission_denials"] = message.permission_denials

                    logger.info("  🏁 ResultMessage: success={}, permission_denials={}",
                               result["success"],
                               len(message.permission_denials or []))
                    break

    except Exception as e:
        result["error_message"] = str(e)
        logger.error("测试失败: {}", e)

    logger.info("结果: success={}, tool_calls={}, permission_denials={}",
                result["success"],
                len(result["tool_calls"]),
                len(result["permission_denials"]))

    return result


async def main_async(args: argparse.Namespace) -> None:
    setup_logger("07_permissions_probe")
    logger.info("开始第 7 章 Permissions 工具权限控制验证: profile={}", args.profile)

    # 创建 sandbox 目录
    sandbox_dir = OUT_DIR / "sandbox"
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    results = []

    # 所有测试用同一个 prompt（尝试读取和写入）
    prompt = "Read the file README.md and create a summary in summary.txt"

    # 测试 A: 默认模式
    logger.info("\n" + "=" * 60)
    logger.info("测试 A: permission_mode='default'（会提示用户）")
    # 注意：default 模式会等待用户输入，SDK 环境下会超时或挂起
    # 跳过这个测试，或者用 dontAsk 模式模拟

    # 测试 B: 自动接受编辑
    logger.info("\n" + "=" * 60)
    logger.info("测试 B: permission_mode='acceptEdits'")
    options_b = build_options(args.profile, "accept_edits")
    result_b = await run_test("B_accept_edits", options_b, prompt)
    results.append(result_b)

    # 测试 C: allowed_tools
    logger.info("\n" + "=" * 60)
    logger.info("测试 C: allowed_tools=['Read']")
    options_c = build_options(args.profile, "allowed_tools")
    result_c = await run_test("C_allowed_tools", options_c, prompt)
    results.append(result_c)

    # 测试 D: disallowed_tools
    logger.info("\n" + "=" * 60)
    logger.info("测试 D: disallowed_tools=['Write']")
    options_d = build_options(args.profile, "disallowed_tools")
    result_d = await run_test("D_disallowed_tools", options_d, prompt)
    results.append(result_d)

    # 测试 E: can_use_tool 回调拒绝
    logger.info("\n" + "=" * 60)
    logger.info("测试 E: can_use_tool 回调拒绝 Write")
    options_e = build_options(args.profile, "callback_deny")
    result_e = await run_test("E_callback_deny", options_e, prompt)
    results.append(result_e)

    # 测试 F: can_use_tool 回调重定向
    logger.info("\n" + "=" * 60)
    logger.info("测试 F: can_use_tool 回调重定向 Write")
    options_f = build_options(args.profile, "callback_redirect")
    result_f = await run_test("F_callback_redirect", options_f, prompt)
    results.append(result_f)

    # 输出摘要
    summary = {
        "profile": args.profile,
        "test_prompt": prompt,
        "test_results": results,
        "conclusions": {
            "B_accept_edits": "accepted" if result_b["success"] else "failed",
            "C_allowed_tools": "partial_allowed" if result_c["tool_calls"] else "failed",
            "D_disallowed_tools": "blocked" if not any(t["name"] == "Write" for t in result_d["tool_calls"]) else "allowed",
            "E_callback_deny": "denied" if result_e["permission_denials"] else "allowed",
            "F_callback_redirect": "redirected" if result_f["success"] else "failed",
        }
    }

    summary_path = OUT_DIR / "07_permissions_probe_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成摘要:")
    for key, value in summary["conclusions"].items():
        logger.info("  {}: {}", key, value)
    logger.info("摘要已写出: {}", summary_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 7: Permission control behavior probe.")
    parser.add_argument("--profile", default="codefoxai_sonnet")
    return parser.parse_args()


def main() -> None:
    anyio.run(main_async, parse_args())


if __name__ == "__main__":
    main()
