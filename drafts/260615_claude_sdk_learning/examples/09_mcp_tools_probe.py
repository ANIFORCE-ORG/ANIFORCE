#!/usr/bin/env python
"""第 9 章：MCP 自定义工具验证

验证 SDK 的 in-process MCP server 能力：
1. 使用 @tool 装饰器定义自定义工具
2. 使用 create_sdk_mcp_server() 创建 MCP server
3. 工具的输入校验和错误处理
4. MCP 工具与 Hooks/Permissions 的集成
5. 对比 SDK MCP vs 外部 stdio MCP 的差异

ANIFORCE 场景：
- 业务工具封装（数据库查询、API 调用、文件操作）
- Tenant 隔离（工具内部检查 tenant_id）
- 审计日志（工具调用记录）
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

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk.types import (
    AssistantMessage,
    HookContext,
    HookInput,
    HookJSONOutput,
    HookMatcher,
    Message,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

# 全局统计
mcp_stats = {
    "tenant_read_called": 0,
    "tenant_read_allowed": 0,
    "tenant_read_denied": 0,
    "tenant_write_called": 0,
    "tenant_write_allowed": 0,
    "tenant_write_denied": 0,
    "database_query_called": 0,
    "database_query_success": 0,
    "database_query_error": 0,
}

hook_stats = {
    "PreToolUse_triggered": 0,
    "mcp_tools_intercepted": 0,
}

# 模拟 Tenant 数据存储
tenant_data = {
    "tenant_001": {
        "files": {
            "config.json": '{"app": "demo", "version": "1.0"}',
            "data.txt": "Hello from tenant 001",
        }
    },
    "tenant_002": {
        "files": {
            "config.json": '{"app": "demo", "version": "2.0"}',
            "data.txt": "Hello from tenant 002",
        }
    },
}


# ========== MCP 工具定义 ==========
@tool(
    "tenant_read_file",
    "读取租户隔离的文件（需要 tenant_id 和 file_path）",
    {"tenant_id": str, "file_path": str},
)
async def tenant_read_file(args: dict[str, Any]) -> dict[str, Any]:
    """读取租户文件，内置 Tenant 隔离逻辑"""
    mcp_stats["tenant_read_called"] += 1

    tenant_id = args.get("tenant_id", "")
    file_path = args.get("file_path", "")

    print(f"[MCP Tool] tenant_read_file: tenant={tenant_id}, path={file_path}")

    # Tenant 隔离检查
    if tenant_id not in tenant_data:
        mcp_stats["tenant_read_denied"] += 1
        return {
            "content": [
                {"type": "text", "text": f"Error: Tenant '{tenant_id}' not found"}
            ],
            "is_error": True,
        }

    tenant_files = tenant_data[tenant_id]["files"]
    if file_path not in tenant_files:
        mcp_stats["tenant_read_denied"] += 1
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: File '{file_path}' not found in tenant '{tenant_id}'",
                }
            ],
            "is_error": True,
        }

    mcp_stats["tenant_read_allowed"] += 1
    content = tenant_files[file_path]
    return {
        "content": [
            {
                "type": "text",
                "text": f"File: {file_path}\nTenant: {tenant_id}\nContent:\n{content}",
            }
        ]
    }


@tool(
    "tenant_write_file",
    "写入租户隔离的文件（需要 tenant_id、file_path 和 content）",
    {"tenant_id": str, "file_path": str, "content": str},
)
async def tenant_write_file(args: dict[str, Any]) -> dict[str, Any]:
    """写入租户文件，内置 Tenant 隔离逻辑"""
    mcp_stats["tenant_write_called"] += 1

    tenant_id = args.get("tenant_id", "")
    file_path = args.get("file_path", "")
    content = args.get("content", "")

    print(f"[MCP Tool] tenant_write_file: tenant={tenant_id}, path={file_path}")

    # Tenant 隔离检查
    if tenant_id not in tenant_data:
        mcp_stats["tenant_write_denied"] += 1
        return {
            "content": [
                {"type": "text", "text": f"Error: Tenant '{tenant_id}' not found"}
            ],
            "is_error": True,
        }

    # 禁止写入系统文件
    if file_path.startswith("/") or ".." in file_path:
        mcp_stats["tenant_write_denied"] += 1
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: Invalid file path '{file_path}' (absolute paths and '..' not allowed)",
                }
            ],
            "is_error": True,
        }

    mcp_stats["tenant_write_allowed"] += 1
    tenant_data[tenant_id]["files"][file_path] = content
    return {
        "content": [
            {
                "type": "text",
                "text": f"Success: Written {len(content)} bytes to '{file_path}' in tenant '{tenant_id}'",
            }
        ]
    }


@tool(
    "database_query",
    "模拟数据库查询（支持 SQL 语句）",
    {"tenant_id": str, "sql": str},
)
async def database_query(args: dict[str, Any]) -> dict[str, Any]:
    """模拟数据库查询，演示错误处理"""
    mcp_stats["database_query_called"] += 1

    tenant_id = args.get("tenant_id", "")
    sql = args.get("sql", "")

    print(f"[MCP Tool] database_query: tenant={tenant_id}, sql={sql[:50]}...")

    # 模拟 SQL 注入检测
    dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "--", ";"]
    for keyword in dangerous_keywords:
        if keyword.upper() in sql.upper():
            mcp_stats["database_query_error"] += 1
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Dangerous SQL keyword detected: {keyword}",
                    }
                ],
                "is_error": True,
            }

    # 模拟查询结果
    if "SELECT" in sql.upper():
        mcp_stats["database_query_success"] += 1
        result = {
            "rows": [
                {"id": 1, "name": "Alice", "tenant_id": tenant_id},
                {"id": 2, "name": "Bob", "tenant_id": tenant_id},
            ]
        }
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Query result:\n{json.dumps(result, indent=2)}",
                }
            ]
        }

    mcp_stats["database_query_error"] += 1
    return {
        "content": [{"type": "text", "text": "Error: Only SELECT queries are supported"}],
        "is_error": True,
    }


# ========== PreToolUse Hook 审计 MCP 工具调用 ==========
async def audit_mcp_tools(
    input_data: HookInput, tool_use_id: str | None, context: HookContext
) -> HookJSONOutput:
    """审计所有 MCP 工具调用"""
    hook_stats["PreToolUse_triggered"] += 1

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # 只审计 MCP 工具（工具名前缀为 mcp__）
    if tool_name.startswith("mcp__"):
        hook_stats["mcp_tools_intercepted"] += 1
        print(f"[PreToolUse Hook] MCP工具={tool_name}, 输入={tool_input}")

    return {}


# ========== 测试场景 ==========
async def test_tenant_isolation(test_name: str, prompt: str, options: ClaudeAgentOptions):
    """测试 Tenant 隔离"""
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
                        print(f"Claude: {block.text[:300]}...")
                    elif isinstance(block, ToolUseBlock):
                        print(f"[Tool Call] {block.name} with input: {block.input}")
            elif isinstance(msg, ResultMessage):
                print(f"Result: stop_reason={msg.stop_reason}, is_error={msg.is_error}")


async def main():
    """主测试流程"""

    print("第 9 章：MCP 自定义工具验证")
    print("=" * 80)

    # 创建 MCP server
    tenant_server = create_sdk_mcp_server(
        name="tenant_tools",
        version="1.0.0",
        tools=[tenant_read_file, tenant_write_file, database_query],
    )

    # ========== 测试 A：读取租户文件（成功） ==========
    options_a = ClaudeAgentOptions(
        mcp_servers={"tenant": tenant_server},
        allowed_tools=[
            "mcp__tenant__tenant_read_file",
            "mcp__tenant__tenant_write_file",
            "mcp__tenant__database_query",
        ],
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="mcp__.*", hooks=[audit_mcp_tools]),
            ],
        },
    )

    await test_tenant_isolation(
        "测试 A: 读取 tenant_001 的 config.json",
        "Use tenant_read_file to read config.json from tenant_001",
        options_a,
    )

    # ========== 测试 B：跨租户访问（拒绝） ==========
    await test_tenant_isolation(
        "测试 B: 尝试读取不存在的租户 tenant_999",
        "Use tenant_read_file to read config.json from tenant_999",
        options_a,
    )

    # ========== 测试 C：写入租户文件 ==========
    await test_tenant_isolation(
        "测试 C: 写入新文件到 tenant_001",
        "Use tenant_write_file to write 'Hello ANIFORCE' to new_file.txt in tenant_001",
        options_a,
    )

    # ========== 测试 D：SQL 注入防护 ==========
    await test_tenant_isolation(
        "测试 D: 数据库查询（正常）",
        "Use database_query to SELECT * FROM users in tenant_001",
        options_a,
    )

    await test_tenant_isolation(
        "测试 E: 数据库查询（SQL 注入尝试）",
        "Use database_query with SQL: 'DROP TABLE users; --' in tenant_001",
        options_a,
    )

    # ========== 测试 F：路径遍历攻击防护 ==========
    await test_tenant_isolation(
        "测试 F: 写入文件（路径遍历尝试）",
        "Use tenant_write_file to write 'attack' to '../etc/passwd' in tenant_001",
        options_a,
    )

    # ========== 输出统计 ==========
    print("\n" + "=" * 80)
    print("MCP 工具统计:")
    print(json.dumps(mcp_stats, indent=2, ensure_ascii=False))
    print("\nHook 统计:")
    print(json.dumps(hook_stats, indent=2, ensure_ascii=False))

    # ========== 保存结果 ==========
    output_dir = Path("drafts/260615_claude_sdk_learning/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "mcp_stats": mcp_stats,
        "hook_stats": hook_stats,
        "tenant_data_after_test": tenant_data,
        "conclusions": {
            "tenant_isolation_works": mcp_stats["tenant_read_denied"] > 0,
            "mcp_tools_callable": mcp_stats["tenant_read_called"] > 0,
            "sql_injection_blocked": mcp_stats["database_query_error"] > 0,
            "path_traversal_blocked": mcp_stats["tenant_write_denied"] > 0,
            "hooks_intercept_mcp": hook_stats["mcp_tools_intercepted"] > 0,
        },
    }

    output_file = output_dir / "09_mcp_tools_probe_summary.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
