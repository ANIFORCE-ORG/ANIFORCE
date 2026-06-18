#!/usr/bin/env python
"""
完整 API 测试：启动服务并测试所有端点

测试场景：
1. 健康检查端点
2. CopilotKit Info 端点
3. 创建任务（需要认证）
4. 查询任务列表
5. 获取任务详情
6. 多租户隔离验证
"""
import asyncio
import httpx
import sys
import os
import time
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.auth import create_access_token


BASE_URL = "http://localhost:8020"


async def test_health_check():
    """测试健康检查"""
    print("=" * 60)
    print("测试 1：健康检查")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")

            if response.status_code == 200:
                print("✅ 健康检查通过")
            else:
                print(f"❌ 健康检查失败")
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            print("   请确保服务已启动：uvicorn app.main:app --port 8020")
    print()


async def test_copilotkit_info():
    """测试 CopilotKit Info"""
    print("=" * 60)
    print("测试 2：CopilotKit Info")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/agent/copilotkit/info")
            print(f"状态码: {response.status_code}")
            data = response.json()
            print(f"响应: {data}")

            if response.status_code == 200 and "agents" in data:
                print("✅ CopilotKit Info 正常")
                print(f"   Agent 数量: {len(data['agents'])}")
            else:
                print("❌ CopilotKit Info 失败")
        except Exception as e:
            print(f"❌ 请求失败: {e}")
    print()


async def test_create_task_auth():
    """测试任务创建（需要认证）"""
    print("=" * 60)
    print("测试 3：任务创建（认证）")
    print("=" * 60)

    # 生成 JWT Token
    token = create_access_token({"sub": "test_user_api", "email": "test@example.com"})
    print(f"JWT Token: {token[:30]}...")

    async with httpx.AsyncClient() as client:
        try:
            # 无认证请求（应该失败）
            response_no_auth = await client.post(
                f"{BASE_URL}/api/agent/tasks",
                json={
                    "task_type": "conversation",
                    "title": "测试任务",
                    "input_data": {"prompt": "Hello"},
                    "session_id": str(uuid4()),
                }
            )
            print(f"无认证状态码: {response_no_auth.status_code}")
            if response_no_auth.status_code == 401:
                print("✅ 未认证请求正确拒绝")
            else:
                print(f"❌ 未认证请求未被拒绝: {response_no_auth.status_code}")

            # 有认证请求
            response_auth = await client.post(
                f"{BASE_URL}/api/agent/tasks",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "task_type": "conversation",
                    "title": "测试任务",
                    "input_data": {"prompt": "Hello"},
                    "session_id": str(uuid4()),
                }
            )
            print(f"\n有认证状态码: {response_auth.status_code}")

            if response_auth.status_code == 200:
                data = response_auth.json()
                print(f"响应: {data}")
                print(f"✅ 任务创建成功")
                print(f"   Task ID: {data.get('task_id')}")
                return data.get('task_id')
            else:
                print(f"❌ 任务创建失败: {response_auth.text}")
                return None
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None
    print()


async def test_list_tasks(token):
    """测试任务列表"""
    print("=" * 60)
    print("测试 4：查询任务列表")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/api/agent/tasks",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"任务数量: {len(data.get('tasks', []))}")
                print("✅ 任务列表查询成功")
            else:
                print(f"❌ 任务列表查询失败")
        except Exception as e:
            print(f"❌ 请求失败: {e}")
    print()


async def test_multi_tenant_isolation():
    """测试多租户隔离"""
    print("=" * 60)
    print("测试 5：多租户隔离")
    print("=" * 60)

    # 创建两个用户的 Token
    token_a = create_access_token({"sub": "user_a", "email": "a@example.com"})
    token_b = create_access_token({"sub": "user_b", "email": "b@example.com"})

    async with httpx.AsyncClient() as client:
        try:
            # 用户 A 创建任务
            response_a = await client.post(
                f"{BASE_URL}/api/agent/tasks",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "task_type": "conversation",
                    "title": "用户A的任务",
                    "session_id": str(uuid4()),
                }
            )

            if response_a.status_code == 200:
                task_id_a = response_a.json().get('task_id')
                print(f"✅ 用户 A 创建任务: {task_id_a}")

                # 用户 B 查询任务列表（应该看不到用户 A 的任务）
                response_b = await client.get(
                    f"{BASE_URL}/api/agent/tasks",
                    headers={"Authorization": f"Bearer {token_b}"}
                )

                if response_b.status_code == 200:
                    tasks_b = response_b.json().get('tasks', [])
                    task_ids_b = [t['task_id'] for t in tasks_b]

                    if task_id_a not in task_ids_b:
                        print("✅ 多租户隔离正常：用户 B 看不到用户 A 的任务")
                    else:
                        print("❌ 多租户隔离失败：用户 B 可以看到用户 A 的任务")
            else:
                print(f"❌ 用户 A 创建任务失败")
        except Exception as e:
            print(f"❌ 请求失败: {e}")
    print()


async def main():
    print()
    print("🧪 ANIFORCE Agent API 端点测试")
    print()
    print("⚠️  注意：此测试需要服务已启动")
    print("   启动命令：")
    print("   export $(cat .env.test | xargs) && \\")
    print("   .venv/bin/python -m uvicorn app.main:app --port 8020")
    print()

    await test_health_check()
    await test_copilotkit_info()

    task_id = await test_create_task_auth()

    token = create_access_token({"sub": "test_user_api", "email": "test@example.com"})
    await test_list_tasks(token)

    await test_multi_tenant_isolation()

    print("=" * 60)
    print("✅ 所有 API 端点测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
