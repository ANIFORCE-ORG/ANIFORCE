#!/usr/bin/env python
"""
真实场景测试 3：HTTP MCP 工具调用

前置条件：
- 后端服务运行在 http://localhost:8010
- 设置 BACKEND_URL=http://localhost:8010
- 设置 INTERNAL_TOKEN=your-token

目标：验证 Agent 能否通过 HTTP MCP 调用后端工具

步骤：
1. 模拟用户登录（生成 JWT Token）
2. 设置 JWT Token 到 Context
3. 让 Agent "列出我的所有项目"
4. 观察是否调用 list_projects 工具
5. 观察后端返回结果

预期结果：
- 看到 tool_use 消息（调用 list_projects）
- 看到 tool_result 消息（后端返回）
- Agent 能整合结果给出回答
"""
import asyncio
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.runtime import AgentRuntime
from app.config.database import init_task_db
from app.core.auth import create_access_token
from app.core.context import set_jwt_token


async def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    backend_url = os.getenv("BACKEND_URL")

    if not api_key:
        print("❌ 错误：未设置 ANTHROPIC_API_KEY")
        return

    if not backend_url:
        print("⚠️  警告：未设置 BACKEND_URL，跳过 HTTP MCP 测试")
        print("   如需测试，请运行：export BACKEND_URL=http://localhost:8010")
        return

    print("=" * 60)
    print("真实场景测试 3：HTTP MCP 工具调用")
    print("=" * 60)
    print()

    # 生成 JWT Token
    print("🔐 生成测试 JWT Token...")
    token = create_access_token({"sub": "test_user_mcp", "email": "test@example.com"})
    print(f"✅ Token: {token[:20]}...")

    # 设置到 Context（模拟认证中间件）
    set_jwt_token(token)
    print("✅ Token 已设置到 Context")
    print()

    await init_task_db()
    runtime = AgentRuntime()
    session_id = str(uuid4())

    prompt = "列出我的所有项目，告诉我有多少个项目。"
    print(f"👤 用户: {prompt}")
    print()
    print("🔄 观察工具调用...")
    print("-" * 60)

    tool_calls = []
    tool_results = []

    async for message in runtime.query(
        session_id=session_id,
        user_id="test_user_mcp",
        task_id="task_mcp",
        prompt=prompt,
    ):
        msg_type = message.get("type")

        if msg_type == "assistant":
            for block in message.get("content", []):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        print(f"🤖 Claude: {text}")
                elif block.get("type") == "tool_use":
                    tool_name = block.get("name")
                    tool_input = block.get("input", {})
                    tool_calls.append({"name": tool_name, "input": tool_input})
                    print(f"\n🔧 调用工具: {tool_name}")
                    print(f"   参数: {tool_input}")

        elif msg_type == "user":
            for block in message.get("content", []):
                if block.get("type") == "tool_result":
                    result_content = block.get("content", [])
                    for content_block in result_content:
                        if content_block.get("type") == "text":
                            result_text = content_block.get("text", "")
                            tool_results.append(result_text)
                            print(f"✅ 工具返回: {result_text[:200]}")

    print()
    print("=" * 60)
    print("✅ 测试结果")
    print("=" * 60)
    print(f"🔧 工具调用次数: {len(tool_calls)}")
    print(f"✅ 工具返回次数: {len(tool_results)}")
    print()

    if len(tool_calls) > 0:
        print("✅ HTTP MCP 工具调用成功")
        print(f"   调用的工具: {[t['name'] for t in tool_calls]}")
        if "list_projects" in [t['name'] for t in tool_calls]:
            print("✅ list_projects 工具调用正确")
    else:
        print("❌ 未调用任何工具")
        print("   可能原因：")
        print("   1. 后端服务未运行")
        print("   2. MCP 配置错误")
        print("   3. JWT Token 未正确透传")

    await runtime.cleanup_all()


if __name__ == "__main__":
    asyncio.run(main())
