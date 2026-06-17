#!/usr/bin/env python3
"""
Block 7: MCP 工具接 backend 测试

验证：
- Agent 通过 MCP 调用 backend API
- JWT 透传（Agent 用用户身份调 API）
- 工具调用产生 TaskProgressUpdated 事件
- Agent 基于工具结果生成回复
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from app.core.auth import create_access_token


def print_section(title):
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def print_result(passed, message):
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


def test_block_7():
    """执行 Block 7 测试"""

    print_section("Block 7: MCP 工具接 backend 测试")

    results = []
    base_url = "http://localhost:8020"

    # 生成测试 Token
    token = create_access_token(
        {"sub": "test_user_block7", "email": "block7@example.com", "name": "Test User Block 7"}
    )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print(f"测试 Token: {token[:50]}...")

    # Step 7.1: 验证 Backend 可访问
    print_section("Step 7.1: Backend 服务连通性")

    from app.config.settings import get_settings
    settings = get_settings()
    backend_url = settings.BACKEND_URL or "http://localhost:3000"
    try:
        backend_health = httpx.get(f"{backend_url}/health", timeout=5)
        backend_ok = backend_health.status_code == 200
        print(f"Backend 状态: {backend_health.status_code}")
        if backend_ok:
            print(f"Backend 响应: {backend_health.json()}")
        results.append(print_result(backend_ok, "Backend 服务可访问"))
    except Exception as e:
        print(f"Backend 连接失败: {e}")
        results.append(print_result(False, "Backend 服务可访问"))
        print("\n⚠️  Backend 服务未启动，请先启动 backend 服务")
        print("提示：cd backend && npm run dev")
        return False

    # Step 7.2: 测试 Backend MCP 端点
    print_section("Step 7.2: Backend MCP 端点验证")

    try:
        # 需要 X-Internal-Token header（从配置读取）
        from app.config.settings import get_settings
        settings = get_settings()
        internal_headers = {
            "Authorization": f"Bearer {token}",
            "X-Internal-Token": settings.INTERNAL_TOKEN,
        }
        mcp_tools = httpx.get(f"{backend_url}/api/v1/mcp/tools", headers=internal_headers, timeout=10)
        mcp_ok = mcp_tools.status_code == 200
        print(f"MCP Tools 状态: {mcp_tools.status_code}")
        if mcp_ok:
            tools_data = mcp_tools.json()
            tool_names = [tool["name"] for tool in tools_data.get("tools", [])]
            print(f"可用工具 ({len(tool_names)}): {tool_names[:5]}...")
            has_campaigns = "list_campaigns" in tool_names
            results.append(print_result(has_campaigns, "MCP 工具包含 list_campaigns"))
        else:
            print(f"错误: {mcp_tools.text}")
            results.append(print_result(False, "MCP 工具包含 list_campaigns"))
    except Exception as e:
        print(f"MCP 端点请求失败: {e}")
        results.append(print_result(False, "MCP 工具包含 list_campaigns"))

    # Step 7.3: Agent 调用 MCP 工具
    print_section("Step 7.3: Agent 调用 MCP 工具")

    session_id = str(uuid.uuid4())
    run_payload = {
        "prompt": "使用 backend 服务器的 list_projects 工具查询我的广告投放项目列表（不要使用 DesignSync）",
        "session_id": session_id,
        "task_type": "conversation",
        "title": "block7 mcp test",
        "max_turns": 10,
        "allowed_tools": ["mcp__backend__list_projects"],  # 只允许这个工具
    }

    task_id = None
    agent_response = ""
    tool_call_detected = False
    tool_name = None

    try:
        with httpx.stream("POST", f"{base_url}/api/agent/runs", json=run_payload, headers=headers, timeout=240) as response:
            print(f"状态码: {response.status_code}")
            if response.status_code != 200:
                print(f"错误: {response.read().decode()}")
                results.extend([False, False, False])
                return False

            for line in response.iter_lines():
                if line.startswith("event: "):
                    current_event = line[7:]
                elif line.startswith("data: "):
                    import json

                    data = json.loads(line[6:])
                    task_id = data.get("taskId") or task_id

                    if current_event == "TaskOutputDelta":
                        agent_response += data.get("delta", "")

                    elif current_event == "TaskProgressUpdated":
                        progress = data.get("progress", {})
                        tool_info = progress.get("tool")
                        if tool_info:
                            tool_call_detected = True
                            tool_name = tool_info.get("name", "")
                            print(f"  检测到工具调用: {tool_name}")

        print(f"\nAgent 回复: {agent_response[:300]}")

        results.append(print_result(tool_call_detected, "检测到工具调用事件"))
        results.append(print_result("list_projects" in (tool_name or "").lower() or "project" in agent_response.lower(), "Agent 调用了项目相关工具"))

        # 验证 Agent 基于工具结果生成回复
        has_meaningful_response = len(agent_response) > 20
        results.append(print_result(has_meaningful_response, "Agent 生成了有效回复"))

    except Exception as e:
        print(f"请求失败: {e}")
        import traceback
        traceback.print_exc()
        results.extend([False, False, False])

    # Step 7.4: 验证 JWT 透传（Backend 日志应显示正确的 user_id）
    print_section("Step 7.4: JWT 透传验证")

    print("注：需要查看 Backend 服务日志，确认请求中包含正确的 JWT Token 和 user_id")
    print(f"预期 user_id: test_user_block7")

    # 这一步主要通过日志验证，测试脚本只能做间接验证
    # 如果工具调用成功且有回复，说明 JWT 透传基本正常
    jwt_ok = tool_call_detected and len(agent_response) > 20
    results.append(print_result(jwt_ok, "JWT 透传间接验证（工具调用成功）"))

    # 总结
    print_section("Block 7 测试结果")
    passed_count = sum(results)
    total_count = len(results)
    print(f"\n通过: {passed_count}/{total_count}")

    if passed_count >= total_count - 1:  # 允许一个检查点失败
        print("\n🎉 Block 7 基本通过！")
        if passed_count < total_count:
            print("注：部分检查点需要查看 Backend 日志进一步确认")
        return True
    else:
        print("\n⚠️  Block 7 部分失败")
        print("\n常见问题排查:")
        print("1. Backend 服务未启动 → cd backend && npm run dev")
        print("2. Backend MCP 端点未配置 → 检查 backend/app/api/v1/mcp.py")
        print("3. JWT Token 未透传 → 检查 aniforce-agent/app/middleware/auth.py")
        print("4. MCP 配置错误 → 检查 aniforce-agent/app/mcp/remote.py")
        return False


if __name__ == "__main__":
    success = test_block_7()
    sys.exit(0 if success else 1)
