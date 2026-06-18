#!/usr/bin/env python
"""第 8 章：Hooks 系统验证

对比 Permissions callback (can_use_tool) 与 Hooks 的职责边界和使用场景。

Hooks 提供更全面的拦截能力：
- PreToolUse: 工具执行前（可以 allow/deny/ask/defer，修改参数，注入上下文）
- PostToolUse: 工具执行后（可以修改输出，注入上下文）
- PostToolUseFailure: 工具执行失败后
- UserPromptSubmit: 用户提交 prompt 后
- Stop/SubagentStop: 会话结束时
- PreCompact: 上下文压缩前
- Notification: 收到通知时
- SubagentStart: 子 Agent 启动时
- PermissionRequest: 权限请求时

验证目标：
1. PreToolUse 可以 block/allow/修改参数
2. PostToolUse 可以修改输出
3. Hooks 可以注入 additionalContext
4. Hooks 的 matcher 机制（工具名匹配）
5. 对比 can_use_tool callback 和 PreToolUse hook 的触发时机差异
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# 添加 SDK 到 sys.path
sdk_path = Path(__file__).resolve().parents[3] / "resources" / "claude-agent-sdk-python" / "src"
if str(sdk_path) not in sys.path:
    sys.path.insert(0, str(sdk_path))

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    HookContext,
    HookInput,
    HookJSONOutput,
    HookMatcher,
    Message,
    PermissionResult,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolPermissionContext,
)

# 全局统计
hook_stats = {
    "PreToolUse_triggered": 0,
    "PostToolUse_triggered": 0,
    "PreToolUse_denied": 0,
    "PreToolUse_allowed": 0,
    "PreToolUse_modified": 0,
    "PostToolUse_modified": 0,
}

callback_stats = {
    "can_use_tool_triggered": 0,
    "can_use_tool_allowed": 0,
    "can_use_tool_denied": 0,
    "can_use_tool_modified": 0,
}


# ========== Hook Callbacks ==========
async def audit_pretooluse(
    input_data: HookInput, tool_use_id: str | None, context: HookContext
) -> HookJSONOutput:
    """PreToolUse 审计：记录所有工具调用"""
    hook_stats["PreToolUse_triggered"] += 1

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    print(f"[PreToolUse Hook] 工具={tool_name}, 输入={tool_input}")

    # 拒绝写入 /etc 目录
    if tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        if "/etc/" in file_path or file_path.startswith("/etc"):
            hook_stats["PreToolUse_denied"] += 1
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "禁止写入系统目录 /etc",
                },
                "systemMessage": "🚫 Hook 拒绝写入系统目录",
            }

    # 重定向 sandbox 外的文件写入
    if tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        if not file_path.startswith("sandbox/"):
            hook_stats["PreToolUse_modified"] += 1
            new_path = f"sandbox/{Path(file_path).name}"
            print(f"[PreToolUse Hook] 重定向文件路径: {file_path} → {new_path}")
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "updatedInput": {
                        "file_path": new_path,
                        "content": tool_input.get("content", ""),
                    },
                    "permissionDecision": "allow",
                },
            }

    hook_stats["PreToolUse_allowed"] += 1
    return {}


async def monitor_posttooluse(
    input_data: HookInput, tool_use_id: str | None, context: HookContext
) -> HookJSONOutput:
    """PostToolUse 监控：记录工具输出"""
    hook_stats["PostToolUse_triggered"] += 1

    tool_name = input_data.get("tool_name", "")
    tool_response = input_data.get("tool_response", "")

    print(f"[PostToolUse Hook] 工具={tool_name}, 输出长度={len(str(tool_response))}")

    # 如果 Bash 命令失败，注入帮助信息
    if tool_name == "Bash" and isinstance(tool_response, dict):
        if tool_response.get("interrupted") or "error" in str(tool_response).lower():
            hook_stats["PostToolUse_modified"] += 1
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "命令执行失败。建议检查命令语法或文件路径。",
                },
                "systemMessage": "⚠️ Hook 检测到命令执行失败",
            }

    return {}


# ========== Permission Callback ==========
async def custom_permission_callback(
    tool_name: str, tool_input: dict[str, Any], context: ToolPermissionContext
) -> PermissionResult:
    """can_use_tool callback：只在 permission_mode="default" 时触发"""
    callback_stats["can_use_tool_triggered"] += 1

    print(f"[can_use_tool Callback] 工具={tool_name}, 输入={tool_input}")

    # 拒绝读取 /root 目录
    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        if file_path.startswith("/root/"):
            callback_stats["can_use_tool_denied"] += 1
            return PermissionResultDeny(
                behavior="deny",
                message="Callback 拒绝读取 /root 目录",
            )

    callback_stats["can_use_tool_allowed"] += 1
    return PermissionResultAllow(behavior="allow")


# ========== 测试场景 ==========
async def test_hook_only(test_name: str, prompt: str, options: ClaudeAgentOptions):
    """只使用 Hooks，不使用 can_use_tool callback"""
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"Prompt: {prompt}")
    print(f"{'='*60}\n")

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text[:200]}...")
            elif isinstance(msg, ResultMessage):
                print(f"Result: stop_reason={msg.stop_reason}, is_error={msg.is_error}")


async def test_callback_and_hook(test_name: str, prompt: str, options: ClaudeAgentOptions):
    """同时使用 can_use_tool callback 和 Hooks"""
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"Prompt: {prompt}")
    print(f"注意: 同时有 callback 和 hook")
    print(f"{'='*60}\n")

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text[:200]}...")
            elif isinstance(msg, ResultMessage):
                print(f"Result: stop_reason={msg.stop_reason}, is_error={msg.is_error}")


async def main():
    """主测试流程"""

    # 创建 sandbox 目录
    sandbox_dir = Path("sandbox")
    sandbox_dir.mkdir(exist_ok=True)

    print("第 8 章：Hooks 系统验证")
    print("=" * 80)

    # ========== 测试 A：PreToolUse Hook 拦截写入 /etc ==========
    options_a = ClaudeAgentOptions(
        permission_mode="acceptEdits",  # 自动接受编辑，不触发 callback
        tools=["Write", "Read"],
        cwd=str(Path.cwd()),
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Write|Read", hooks=[audit_pretooluse]),
            ],
        },
    )

    await test_hook_only(
        "测试 A: PreToolUse Hook 拒绝写入 /etc",
        "Write the text 'test' to /etc/test.txt",
        options_a,
    )

    # ========== 测试 B：PreToolUse Hook 重定向文件路径 ==========
    options_b = ClaudeAgentOptions(
        permission_mode="acceptEdits",
        tools=["Write", "Read"],
        cwd=str(Path.cwd()),
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Write", hooks=[audit_pretooluse]),
            ],
        },
    )

    await test_hook_only(
        "测试 B: PreToolUse Hook 重定向文件路径到 sandbox/",
        "Write the text 'Hello from hook redirect' to output.txt",
        options_b,
    )

    # ========== 测试 C：PostToolUse Hook 监控 Bash 失败 ==========
    options_c = ClaudeAgentOptions(
        allowed_tools=["Bash"],
        tools=["Bash"],
        cwd=str(Path.cwd()),
        hooks={
            "PostToolUse": [
                HookMatcher(matcher="Bash", hooks=[monitor_posttooluse]),
            ],
        },
    )

    await test_hook_only(
        "测试 C: PostToolUse Hook 监控 Bash 失败",
        "Run this bash command: ls /nonexistent_directory_12345",
        options_c,
    )

    # ========== 测试 D：can_use_tool callback + PreToolUse Hook 共存 ==========
    # permission_mode="default" 才会触发 can_use_tool callback
    options_d = ClaudeAgentOptions(
        permission_mode="default",  # 触发 callback
        allowed_tools=["Bash"],  # Write/Read 需要 callback 批准
        tools=["Write", "Read", "Bash"],
        cwd=str(Path.cwd()),
        can_use_tool=custom_permission_callback,
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Write|Read", hooks=[audit_pretooluse]),
            ],
        },
    )

    await test_callback_and_hook(
        "测试 D: callback 拒绝读取 /root，Hook 记录调用",
        "Read the file /root/.bashrc",
        options_d,
    )

    # ========== 输出统计 ==========
    print("\n" + "=" * 80)
    print("统计结果:")
    print(json.dumps(hook_stats, indent=2, ensure_ascii=False))
    print(json.dumps(callback_stats, indent=2, ensure_ascii=False))

    # ========== 保存结果 ==========
    output_dir = Path("drafts/260615_claude_sdk_learning/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "hook_stats": hook_stats,
        "callback_stats": callback_stats,
        "conclusions": {
            "hook_pretooluse_can_deny": hook_stats["PreToolUse_denied"] > 0,
            "hook_pretooluse_can_modify": hook_stats["PreToolUse_modified"] > 0,
            "hook_posttooluse_can_inject_context": hook_stats["PostToolUse_modified"] > 0,
            "callback_triggered_with_default_mode": callback_stats["can_use_tool_triggered"] > 0,
        }
    }

    output_file = output_dir / "08_hooks_probe_summary.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
