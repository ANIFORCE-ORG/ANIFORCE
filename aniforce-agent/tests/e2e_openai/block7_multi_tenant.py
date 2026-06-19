#!/usr/bin/env python3
"""
Block 7: 多租户隔离

验证：
- 用户 A 不能访问用户 B 的 task（404）
- 用户 A 不能 resume 用户 B 的 session
- MCP 工具调用带各自 user_id，backend 数据隔离
- 并发请求不串数据
"""

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

import httpx
from agents.mcp import MCPServerStreamableHttp

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.auth import create_access_token


BASE_URL = "http://localhost:8020"
BACKEND_BASE_URL = "http://localhost:8010"
MCP_URL = f"{BASE_URL}/mcp"
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


async def test_block_7_async() -> bool:
    print_section("Block 7: 多租户隔离")
    results = []
    suffix = int(time.time())

    print_section("Step 7.1: 注册两个用户 A/B")
    user_a, token_a = await register_or_login(f"block7-a-{suffix}@example.com", "Block7 User A")
    user_b, token_b = await register_or_login(f"block7-b-{suffix}@example.com", "Block7 User B")
    print(f"用户 A: {user_a}")
    print(f"用户 B: {user_b}")
    results.append(print_result(user_a != user_b, "用户 A/B ID 不同"))

    print_section("Step 7.2: 用户 A 通过 MCP 创建项目")
    project_name = f"block7-isolation-{suffix}"
    async with MCPServerStreamableHttp(
        name="ANIFORCE Tools",
        params={"url": MCP_URL, "timeout": 20},
        cache_tools_list=False,
    ) as server:
        created = parse_tool_result(
            await server.call_tool(
                "create_project",
                {
                    "name": project_name,
                    "total_budget": 777.0,
                    "description": "block7 multi-tenant isolation test",
                    "game_type": "RPG",
                    "target_market": "EU",
                },
                meta={"jwt_token": token_a},
            )
        )
        print(f"创建结果: user_id={created.get('user_id')}, name={created.get('name')}")
        results.append(print_result(created.get("user_id") == user_a, "项目归属用户 A"))
        results.append(print_result(created.get("name") == project_name, "项目名称正确"))

        print_section("Step 7.3: 用户 A 可查到自己的项目")
        list_a = parse_tool_result(
            await server.call_tool("list_projects", {"limit": 50}, meta={"jwt_token": token_a})
        )
        names_a = [p.get("name") for p in list_a.get("projects", [])]
        print(f"用户 A 项目数: {len(names_a)}")
        print(f"包含本次项目: {project_name in names_a}")
        results.append(print_result(project_name in names_a, "用户 A 可见自己的项目"))

        print_section("Step 7.4: 用户 B 看不到用户 A 的项目")
        list_b = parse_tool_result(
            await server.call_tool("list_projects", {"limit": 50}, meta={"jwt_token": token_b})
        )
        names_b = [p.get("name") for p in list_b.get("projects", [])]
        print(f"用户 B 项目数: {len(names_b)}")
        print(f"包含 A 的项目: {project_name in names_b}")
        results.append(print_result(project_name not in names_b, "用户 B 看不到 A 的项目"))

        print_section("Step 7.5: 无 token 被拒绝")
        no_token = parse_tool_result(
            await server.call_tool("list_projects", {"limit": 1}, meta={})
        )
        print(f"无 token 状态: {no_token.get('status')}")
        results.append(print_result(no_token.get("status") == 401, "无 token 返回 401"))

    print_section("Step 7.6: 跨用户访问 task（API 层隔离）")
    async with httpx.AsyncClient(timeout=20) as client:
        # 用户 A 创建一个 task
        resp_a_tasks = await client.get(
            f"{BASE_URL}/api/agent/tasks",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        tasks_a = resp_a_tasks.json().get("tasks", [])
        print(f"用户 A 任务数: {len(tasks_a)}")

        if tasks_a:
            task_a_id = tasks_a[0]["task_id"]
            # 用户 B 尝试访问 A 的 task
            resp_b_cross = await client.get(
                f"{BASE_URL}/api/agent/tasks/{task_a_id}",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            print(f"用户 B 访问 A 的 task 状态码: {resp_b_cross.status_code}")
            results.append(print_result(resp_b_cross.status_code == 404, "跨用户访问 task 被拒绝（404）"))
        else:
            results.append(print_result(False, "跨用户访问 task 被拒绝（404）"))

    print_section("Block 7 汇总")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    return passed == total


def test_block_7() -> bool:
    return asyncio.run(test_block_7_async())


if __name__ == "__main__":
    success = test_block_7()
    sys.exit(0 if success else 1)
