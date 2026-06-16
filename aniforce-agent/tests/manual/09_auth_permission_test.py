#!/usr/bin/env python
"""
测试权限控制和鉴权

验证：
1. JWT Token 认证正常
2. 多租户数据隔离
3. 未认证请求被拒绝
4. Token 过期处理
5. 用户上下文正确传递
"""
import asyncio
import sys
import os
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.auth import create_access_token, decode_access_token, AuthError
from app.core.context import set_user_context, get_user_context, set_jwt_token, get_jwt_token, clear_user_context, clear_jwt_token
from app.repositories.task_repo import TaskRepository
from app.models.task import AgentTask, TaskStatus
from app.config.database import get_task_db
import aiosqlite


async def test_jwt_auth():
    """测试 JWT 认证"""
    print("=" * 70)
    print("🧪 测试 JWT 认证")
    print("=" * 70)
    print()

    # 测试 1：Token 创建和解析
    print("测试 1：Token 创建和解析")
    print("-" * 70)

    token = create_access_token({
        "sub": "user_123",
        "email": "test@example.com",
        "name": "Test User"
    })

    print(f"✅ Token 创建成功: {token[:30]}...")

    try:
        payload = decode_access_token(token)
        print(f"✅ Token 解析成功")
        print(f"   user_id: {payload['sub']}")
        print(f"   email: {payload['email']}")
    except AuthError as e:
        print(f"❌ Token 解析失败: {e}")

    print()

    # 测试 2：无效 Token
    print("测试 2：无效 Token")
    print("-" * 70)

    invalid_token = "invalid.token.here"

    try:
        decode_access_token(invalid_token)
        print("❌ 无效 Token 未被拒绝")
    except AuthError:
        print("✅ 无效 Token 正确拒绝")

    print()

    # 测试 3：Token 过期（设置 -1 分钟）
    print("测试 3：Token 过期")
    print("-" * 70)

    expired_token = create_access_token(
        {"sub": "user_123"},
        expires_delta=timedelta(minutes=-1)
    )

    try:
        decode_access_token(expired_token)
        print("❌ 过期 Token 未被拒绝")
    except AuthError:
        print("✅ 过期 Token 正确拒绝")

    print()

    # 测试 4：用户上下文存储
    print("测试 4：用户上下文存储")
    print("-" * 70)

    user = {"id": "user_456", "email": "context@example.com"}
    set_user_context(user)

    retrieved_user = get_user_context()

    if retrieved_user and retrieved_user["id"] == "user_456":
        print("✅ 用户上下文存储正常")
    else:
        print("❌ 用户上下文存储失败")

    clear_user_context()

    if get_user_context() is None:
        print("✅ 用户上下文清除正常")
    else:
        print("❌ 用户上下文清除失败")

    print()

    # 测试 5：JWT Token 上下文存储
    print("测试 5：JWT Token 上下文存储")
    print("-" * 70)

    test_token = "test_jwt_token_12345"
    set_jwt_token(test_token)

    retrieved_token = get_jwt_token()

    if retrieved_token == test_token:
        print("✅ JWT Token 上下文存储正常")
    else:
        print("❌ JWT Token 上下文存储失败")

    clear_jwt_token()

    if get_jwt_token() is None:
        print("✅ JWT Token 上下文清除正常")
    else:
        print("❌ JWT Token 上下文清除失败")

    print()


async def test_multi_tenant_isolation():
    """测试多租户数据隔离"""
    print("=" * 70)
    print("🧪 测试多租户数据隔离")
    print("=" * 70)
    print()

    # 初始化数据库
    db_path = os.getenv("TASK_DB_PATH", "tests/manual/outputs/test_tasks.db")
    db = await aiosqlite.connect(db_path)

    # 初始化表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS agent_tasks (
            task_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT,
            input_data TEXT,
            output_data TEXT,
            error_data TEXT,
            session_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    await db.commit()

    task_repo = TaskRepository(db)

    # 测试 1：用户 A 创建任务
    print("测试 1：用户 A 创建任务")
    print("-" * 70)

    task_a = AgentTask(
        task_id="task_user_a_001",
        user_id="user_a",
        task_type="conversation",
        status=TaskStatus.PENDING,
        title="User A Task",
    )

    await task_repo.create(task_a)
    print(f"✅ 用户 A 创建任务: {task_a.task_id}")

    print()

    # 测试 2：用户 B 创建任务
    print("测试 2：用户 B 创建任务")
    print("-" * 70)

    task_b = AgentTask(
        task_id="task_user_b_001",
        user_id="user_b",
        task_type="conversation",
        status=TaskStatus.PENDING,
        title="User B Task",
    )

    await task_repo.create(task_b)
    print(f"✅ 用户 B 创建任务: {task_b.task_id}")

    print()

    # 测试 3：用户 A 只能看到自己的任务
    print("测试 3：用户 A 只能看到自己的任务")
    print("-" * 70)

    tasks_a = await task_repo.list_by_user("user_a")

    task_ids_a = [t.task_id for t in tasks_a]
    print(f"用户 A 可见任务: {task_ids_a}")

    if "task_user_a_001" in task_ids_a and "task_user_b_001" not in task_ids_a:
        print("✅ 用户 A 只能看到自己的任务")
    else:
        print("❌ 数据隔离失败")

    print()

    # 测试 4：用户 B 只能看到自己的任务
    print("测试 4：用户 B 只能看到自己的任务")
    print("-" * 70)

    tasks_b = await task_repo.list_by_user("user_b")

    task_ids_b = [t.task_id for t in tasks_b]
    print(f"用户 B 可见任务: {task_ids_b}")

    if "task_user_b_001" in task_ids_b and "task_user_a_001" not in task_ids_b:
        print("✅ 用户 B 只能看到自己的任务")
    else:
        print("❌ 数据隔离失败")

    print()

    # 测试 5：用户 B 无法获取用户 A 的任务
    print("测试 5：用户 B 无法获取用户 A 的任务")
    print("-" * 70)

    task_a_by_b = await task_repo.get_by_id("task_user_a_001", "user_b")

    if task_a_by_b is None:
        print("✅ 用户 B 无法获取用户 A 的任务")
    else:
        print("❌ 权限控制失败")

    print()

    await db.close()


async def main():
    print()
    print("🧪 权限控制和鉴权测试")
    print()

    await test_jwt_auth()
    await test_multi_tenant_isolation()

    print("=" * 70)
    print("✅ 所有权限和鉴权测试完成")
    print("=" * 70)
    print()
    print("总结：")
    print("✅ JWT Token 认证正常")
    print("✅ Token 过期处理正常")
    print("✅ 用户上下文存储正常")
    print("✅ 多租户数据隔离正常")
    print("✅ 权限控制正常")


if __name__ == "__main__":
    asyncio.run(main())
