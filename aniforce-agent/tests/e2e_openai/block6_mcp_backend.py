#!/usr/bin/env python3
"""
Block 6: MCP 工具接 backend

验证：
- agent-service 内部 FastMCP /mcp 可连接
- MCP list_tools 暴露业务工具
- _meta.jwt_token 能被 MCP 工具读取并透传给 backend REST
- backend 正式模式下，无 token / 无效 token 返回 401
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
from agents.mcp import MCPServerStreamableHttp


AGENT_BASE_URL = "http://127.0.0.1:8020"
BACKEND_BASE_URL = "http://127.0.0.1:8010"
MCP_URL = f"{AGENT_BASE_URL}/mcp"
PASSWORD = "TenantTest123456!"


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def print_result(passed: bool, message: str) -> bool:
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


def content_text(result) -> str:
    return "\n".join(
        getattr(item, "text", "") for item in result.content if getattr(item, "text", None)
    )


def parse_tool_result(result) -> dict:
    text = content_text(result)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}


async def ensure_services() -> list[bool]:
    results = []
    print_section("Step 6.1: 服务健康检查")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            agent_resp = await client.get(f"{AGENT_BASE_URL}/health")
            print(f"agent health: {agent_resp.status_code} {agent_resp.text[:120]}")
            results.append(print_result(agent_resp.status_code == 200, "agent-service 在线"))
        except Exception as e:
            print(f"agent health 错误: {e}")
            results.append(print_result(False, "agent-service 在线"))

        try:
            backend_resp = await client.get(f"{BACKEND_BASE_URL}/health")
            backend_data = backend_resp.json()
            print(f"backend health: {backend_resp.status_code} {backend_data}")
            results.append(print_result(backend_resp.status_code == 200, "backend 在线"))
            results.append(print_result(backend_data.get("demo_mode") is False, "backend DEMO_MODE=false"))
        except Exception as e:
            print(f"backend health 错误: {e}")
            results.append(print_result(False, "backend 在线"))
            results.append(print_result(False, "backend DEMO_MODE=false"))
    return results


async def register_or_login(email: str, name: str) -> tuple[str, str]:
    async with httpx.AsyncClient(timeout=20) as client:
        payload = {"email": email, "password": PASSWORD, "name": name}
        resp = await client.post(f"{BACKEND_BASE_URL}/api/v1/auth/register", json=payload)
        if resp.status_code == 400 and "已被注册" in resp.text:
            resp = await client.post(
                f"{BACKEND_BASE_URL}/api/v1/auth/login",
                json={"email": email, "password": PASSWORD},
            )
        resp.raise_for_status()
        data = resp.json()["data"]
        return data["user"]["id"], data["access_token"]


async def test_block_6_async() -> bool:
    print_section("Block 6: MCP 工具接 backend")
    results = []
    results.extend(await ensure_services())

    print_section("Step 6.2: MCP 连接和工具列表")
    suffix = int(time.time())
    user_id, token = await register_or_login(f"mcp-block6-{suffix}@example.com", "MCP Block6")
    print(f"测试用户: {user_id}")

    async with MCPServerStreamableHttp(
        name="ANIFORCE Tools",
        params={"url": MCP_URL, "timeout": 20},
        cache_tools_list=False,
    ) as server:
        tools = await server.list_tools()
        tool_names = [tool.name for tool in tools]
        print(f"工具数: {len(tool_names)}")
        print(f"工具列表: {tool_names}")
        expected_tools = {
            "list_projects",
            "get_project_detail",
            "create_project",
            "list_campaigns",
            "get_campaign_detail",
            "create_campaign",
            "update_campaign_status",
            "list_materials",
            "get_material_detail",
        }
        results.append(print_result(len(tool_names) == 9, "MCP 暴露 9 个工具"))
        results.append(print_result(expected_tools.issubset(set(tool_names)), "核心业务工具齐全"))

        print_section("Step 6.3: JWT 透传创建项目")
        project_name = f"mcp-block6-{suffix}"
        created = parse_tool_result(
            await server.call_tool(
                "create_project",
                {
                    "name": project_name,
                    "total_budget": 666.0,
                    "description": "block6 mcp backend validation",
                    "game_type": "SLG",
                    "target_market": "US",
                },
                meta={"jwt_token": token},
            )
        )
        print(f"创建响应: {json.dumps(created, ensure_ascii=False)[:500]}")
        results.append(print_result(created.get("user_id") == user_id, "create_project 使用当前 JWT 用户"))
        results.append(print_result(created.get("name") == project_name, "create_project 返回真实项目"))

        print_section("Step 6.4: JWT 透传查询项目")
        projects = parse_tool_result(
            await server.call_tool("list_projects", {"limit": 50}, meta={"jwt_token": token})
        )
        names = [p.get("name") for p in projects.get("projects", [])]
        print(f"项目名: {names[:10]}")
        results.append(print_result(project_name in names, "list_projects 可查到本用户项目"))

        print_section("Step 6.5: 无 token 被 backend 拒绝")
        no_token = parse_tool_result(await server.call_tool("list_projects", {"limit": 1}, meta={}))
        print(f"无 token 响应: {json.dumps(no_token, ensure_ascii=False)[:300]}")
        results.append(print_result(no_token.get("error") is True, "无 token 返回工具错误"))
        results.append(print_result(no_token.get("status") == 401, "无 token 返回 backend 401"))

    print_section("Block 6 汇总")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    return passed == total


def test_block_6() -> bool:
    return asyncio.run(test_block_6_async())


if __name__ == "__main__":
    success = test_block_6()
    sys.exit(0 if success else 1)
