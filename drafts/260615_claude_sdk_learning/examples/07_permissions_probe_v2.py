from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
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

# 第 7 章主题：Permissions 工具权限控制（强制工具调用版）
# 改进：
# 1. 创建真实测试文件，用强制性 prompt 确保模型调用工具
# 2. 启用 include_partial_messages=True 观察完整消息流
# 3. 记录回调是否真正被触发

CLAUDE_CONFIG_SANDBOX = LEARNING_DIR / "examples" / "07_permissions_sandbox"
TEST_DIR = OUT_DIR / "07_test_workspace"

# 全局统计
callback_stats = {
    "total_calls": 0,
    "allow_count": 0,
    "deny_count": 0,
    "redirect_count": 0,
    "tool_history": [],
}


async def logging_allow_callback(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    """记录并批准"""
    callback_stats["total_calls"] += 1
    callback_stats["allow_count"] += 1
    callback_stats["tool_history"].append({
        "tool": tool_name,
        "input": tool_input,
        "action": "allow"
    })
    logger.info("🔓 权限回调: 批准 {} with {}", tool_name, tool_input)
    return PermissionResultAllow()


async def deny_write_callback(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    """拒绝 Write 工具"""
    callback_stats["total_calls"] += 1

    if tool_name == "Write":
        callback_stats["deny_count"] += 1
        callback_stats["tool_history"].append({
            "tool": tool_name,
            "input": tool_input,
            "action": "deny"
        })
        logger.warning("🚫 权限回调: 拒绝 Write 工具 - {}", tool_input.get("file_path"))
        return PermissionResultDeny(
            message="Write tool is blocked by security policy",
            interrupt=False  # 不中断，让模型看到拒绝消息并调整策略
        )

    callback_stats["allow_count"] += 1
    callback_stats["tool_history"].append({
        "tool": tool_name,
        "input": tool_input,
        "action": "allow"
    })
    logger.info("🔓 权限回调: 批准 {} with {}", tool_name, tool_input)
    return PermissionResultAllow()


async def redirect_write_callback(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    """重定向 Write 到 sandbox"""
    callback_stats["total_calls"] += 1

    if tool_name == "Write":
        original_path = tool_input.get("file_path", "")
        # 提取文件名，重定向到 sandbox
        filename = Path(original_path).name
        safe_path = str(TEST_DIR / "sandbox" / filename)
        callback_stats["redirect_count"] += 1
        callback_stats["tool_history"].append({
            "tool": tool_name,
            "input": tool_input,
            "action": "redirect",
            "original": original_path,
            "redirected": safe_path
        })
        logger.warning("🔀 权限回调: 重定向 Write {} -> {}", original_path, safe_path)
        return PermissionResultAllow(
            updated_input={**tool_input, "file_path": safe_path}
        )

    callback_stats["allow_count"] += 1
    callback_stats["tool_history"].append({
        "tool": tool_name,
        "input": tool_input,
        "action": "allow"
    })
    return PermissionResultAllow()


def prepare_test_workspace():
    """准备测试工作区"""
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    sandbox_dir = TEST_DIR / "sandbox"
    sandbox_dir.mkdir(exist_ok=True)

    # 创建测试输入文件
    input_file = TEST_DIR / "input.txt"
    input_file.write_text("This is test input data.\nLine 2.\nLine 3.\n", encoding="utf-8")

    logger.info("测试工作区准备完毕: {}", TEST_DIR)
    return input_file


def build_options(profile: str, test_case: str, cwd: Path) -> ClaudeAgentOptions:
    load_profile_env(profile)
    env = {k: v for k, v in os.environ.items() if k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_")}
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-sdk-learning/0.7-permissions-probe-v2"
    env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_SANDBOX)
    model = os.getenv("CLAUDE_AGENT_MODEL", "claude-opus-4-6")

    base_opts = {
        "model": model,
        "max_turns": 5,  # 增加 turns 以便模型尝试多次
        "tools": ["Read", "Write"],
        "system_prompt": "You are a file processing assistant. Always use tools to read and write files, never rely on memory.",
        "env": env,
        "thinking": {"type": "disabled"},
        "effort": "low",
        "cwd": str(cwd),  # 设置工作目录
    }

    # 根据测试用例配置不同的权限选项
    if test_case == "accept_edits_with_callback":
        # 测试 A: acceptEdits + 记录回调
        return ClaudeAgentOptions(
            **base_opts,
            permission_mode="acceptEdits",
            can_use_tool=logging_allow_callback,
        )

    elif test_case == "callback_deny":
        # 测试 B: 回调拒绝 Write
        return ClaudeAgentOptions(
            **base_opts,
            permission_mode="acceptEdits",  # 用 acceptEdits 避免交互等待
            can_use_tool=deny_write_callback,
        )

    elif test_case == "callback_redirect":
        # 测试 C: 回调重定向 Write
        return ClaudeAgentOptions(
            **base_opts,
            permission_mode="acceptEdits",
            can_use_tool=redirect_write_callback,
        )

    else:
        raise ValueError(f"Unknown test case: {test_case}")


async def run_test(label: str, options: ClaudeAgentOptions, prompt: str) -> dict[str, Any]:
    """运行单个权限测试"""
    global callback_stats
    # 重置统计
    callback_stats = {
        "total_calls": 0,
        "allow_count": 0,
        "deny_count": 0,
        "redirect_count": 0,
        "tool_history": [],
    }

    logger.info("=" * 60)
    logger.info("测试: {}", label)
    logger.info("Prompt: {}", prompt)

    result = {
        "label": label,
        "prompt": prompt,
        "permission_mode": getattr(options, 'permission_mode', None),
        "has_callback": options.can_use_tool is not None,
        "success": False,
        "tool_calls": [],
        "tool_results": [],
        "permission_denials": [],
        "assistant_messages": [],
        "callback_stats": None,
        "error_message": None,
    }

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            # receive_messages() 默认包含所有消息
            async for message in client.receive_messages():
                if isinstance(message, AssistantMessage):
                    msg_summary = {"type": "AssistantMessage", "content_types": []}
                    for block in message.content:
                        if hasattr(block, 'type'):
                            msg_summary["content_types"].append(block.type)
                            if block.type == 'tool_use':
                                tool_call = {
                                    "id": block.id,
                                    "name": block.name,
                                    "input": block.input,
                                }
                                result["tool_calls"].append(tool_call)
                                logger.info("  🔧 工具调用: {} with {}", block.name, block.input)
                            elif block.type == 'text':
                                logger.info("  💬 文本响应: {}", block.text[:200])
                    result["assistant_messages"].append(msg_summary)

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
                            status = "❌ 错误" if block.is_error else "✅ 成功"
                            logger.info("  {} 工具结果: {}", status, str(block.content)[:100])

                elif isinstance(message, ResultMessage):
                    result["success"] = not message.is_error
                    if message.is_error:
                        result["error_message"] = str(message.result)[:500]

                    # 记录权限拒绝
                    if message.permission_denials:
                        result["permission_denials"] = message.permission_denials
                        logger.warning("  🚫 权限拒绝数: {}", len(message.permission_denials))

                    logger.info("  🏁 ResultMessage: success={}, permission_denials={}",
                               result["success"],
                               len(message.permission_denials or []))
                    break

    except Exception as e:
        result["error_message"] = str(e)
        logger.error("测试失败: {}", e)

    # 记录回调统计
    result["callback_stats"] = dict(callback_stats)

    logger.info("结果: success={}, tool_calls={}, callback_total={}",
                result["success"],
                len(result["tool_calls"]),
                callback_stats["total_calls"])

    if callback_stats["tool_history"]:
        logger.info("回调历史:")
        for idx, record in enumerate(callback_stats["tool_history"], 1):
            logger.info("  {}: {} {} -> {}", idx, record["tool"],
                       record["input"].get("file_path", "N/A"), record["action"])

    return result


async def main_async(args: argparse.Namespace) -> None:
    setup_logger("07_permissions_probe_v2")
    logger.info("开始第 7 章 Permissions 权限控制强制验证: profile=", args.profile)

    # 准备测试环境
    input_file = prepare_test_workspace()

    results = []

    # 强制性 prompt：明确要求使用工具
    prompt = f"Use the Read tool to read {input_file.name}, then use the Write tool to save the uppercase version to output.txt"

    # 测试 A: acceptEdits + 记录回调
    logger.info("\n" + "=" * 60)
    logger.info("测试 A: permission_mode='acceptEdits' + 记录回调")
    options_a = build_options(args.profile, "accept_edits_with_callback", TEST_DIR)
    result_a = await run_test("A_accept_edits_with_callback", options_a, prompt)
    results.append(result_a)

    # 测试 B: 回调拒绝 Write
    logger.info("\n" + "=" * 60)
    logger.info("测试 B: can_use_tool 回调拒绝 Write")
    options_b = build_options(args.profile, "callback_deny", TEST_DIR)
    result_b = await run_test("B_callback_deny", options_b, prompt)
    results.append(result_b)

    # 测试 C: 回调重定向 Write
    logger.info("\n" + "=" * 60)
    logger.info("测试 C: can_use_tool 回调重定向 Write 到 sandbox")
    options_c = build_options(args.profile, "callback_redirect", TEST_DIR)
    result_c = await run_test("C_callback_redirect", options_c, prompt)
    results.append(result_c)

    # 输出摘要
    summary = {
        "profile": args.profile,
        "test_prompt": prompt,
        "test_workspace": str(TEST_DIR),
        "test_results": results,
        "conclusions": {
            "A_callback_triggered": result_a["callback_stats"]["total_calls"] > 0,
            "B_write_denied": result_b["callback_stats"]["deny_count"] > 0,
            "C_write_redirected": result_c["callback_stats"]["redirect_count"] > 0,
        }
    }

    summary_path = OUT_DIR / "07_permissions_probe_v2_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成摘要:")
    for key, value in summary["conclusions"].items():
        logger.info("  {}: {}", key, value)
    logger.info("摘要已写出: {}", summary_path)

    # 检查生成的文件
    logger.info("\n生成的文件:")
    for f in TEST_DIR.rglob("*"):
        if f.is_file():
            logger.info("  - {} ({} bytes)", f.relative_to(TEST_DIR), f.stat().st_size)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 7: Permission control forced probe.")
    parser.add_argument("--profile", default="codefoxai_sonnet")
    return parser.parse_args()


def main() -> None:
    anyio.run(main_async, parse_args())


if __name__ == "__main__":
    main()
