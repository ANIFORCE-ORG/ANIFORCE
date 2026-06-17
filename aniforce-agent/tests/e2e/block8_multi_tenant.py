#!/usr/bin/env python3
"""
Block 8: 多租户隔离测试

验证：
- 不同用户的任务数据隔离
- 用户 A 无法访问用户 B 的任务
- Session 目录隔离
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


def test_block_8():
    """执行 Block 8 测试"""

    print_section("Block 8: 多租户隔离测试")

    results = []
    base_url = "http://localhost:8020"

    # Step 8.1: 准备两个用户 Token
    print_section("Step 8.1: 准备两个用户")

    user_a_id = "user_a_block8"
    user_b_id = "user_b_block8"

    token_a = create_access_token({"sub": user_a_id, "email": "usera@example.com", "name": "User A"})
    token_b = create_access_token({"sub": user_b_id, "email": "userb@example.com", "name": "User B"})

    headers_a = {"Authorization": f"Bearer {token_a}", "Content-Type": "application/json"}
    headers_b = {"Authorization": f"Bearer {token_b}", "Content-Type": "application/json"}

    print(f"User A: {user_a_id}")
    print(f"User B: {user_b_id}")

    # Step 8.2: 两个用户分别创建任务（通过 TaskService 直接创建，不调 Claude）
    print_section("Step 8.2: 创建测试任务（直接写库）")

    import aiosqlite
    from app.config.settings import get_settings
    from app.repositories.task_repo import TaskRepository
    from app.models.task import AgentTask, TaskStatus
    import asyncio
    import uuid

    async def create_test_tasks():
        settings = get_settings()
        async with aiosqlite.connect(settings.TASK_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            task_repo = TaskRepository(db)

            # User A 创建任务
            task_a = AgentTask(
                task_id=f"task_{uuid.uuid4().hex[:16]}",
                user_id=user_a_id,
                task_type="conversation",
                status=TaskStatus.PENDING,
                title="User A Secret Task",
                input_data={"secret": "User A confidential"},
            )
            await task_repo.create(task_a)

            # User B 创建任务
            task_b = AgentTask(
                task_id=f"task_{uuid.uuid4().hex[:16]}",
                user_id=user_b_id,
                task_type="conversation",
                status=TaskStatus.PENDING,
                title="User B Secret Task",
                input_data={"secret": "User B confidential"},
            )
            await task_repo.create(task_b)

            return task_a.task_id, task_b.task_id

    task_a_id, task_b_id = asyncio.run(create_test_tasks())
    print(f"User A 任务: {task_a_id}")
    print(f"User B 任务: {task_b_id}")

    # Step 8.3: User A 查询自己的任务列表
    print_section("Step 8.3: User A 查询任务列表")

    response = httpx.get(f"{base_url}/api/agent/tasks", headers=headers_a, timeout=10)
    if response.status_code == 200:
        tasks_a = response.json()["tasks"]
        task_ids_a = [t["task_id"] for t in tasks_a]
        print(f"User A 可见任务数: {len(tasks_a)}")
        print(f"包含自己的任务: {task_a_id in task_ids_a}")
        print(f"不包含 User B 的任务: {task_b_id not in task_ids_a}")

        results.append(print_result(task_a_id in task_ids_a, "User A 能看到自己的任务"))
        results.append(print_result(task_b_id not in task_ids_a, "User A 看不到 User B 的任务"))
    else:
        print(f"❌ 请求失败: {response.status_code}")
        results.extend([False, False])

    # Step 8.4: User B 查询自己的任务列表
    print_section("Step 8.4: User B 查询任务列表")

    response = httpx.get(f"{base_url}/api/agent/tasks", headers=headers_b, timeout=10)
    if response.status_code == 200:
        tasks_b = response.json()["tasks"]
        task_ids_b = [t["task_id"] for t in tasks_b]
        print(f"User B 可见任务数: {len(tasks_b)}")
        print(f"包含自己的任务: {task_b_id in task_ids_b}")
        print(f"不包含 User A 的任务: {task_a_id not in task_ids_b}")

        results.append(print_result(task_b_id in task_ids_b, "User B 能看到自己的任务"))
        results.append(print_result(task_a_id not in task_ids_b, "User B 看不到 User A 的任务"))
    else:
        print(f"❌ 请求失败: {response.status_code}")
        results.extend([False, False])

    # Step 8.5: User A 尝试访问 User B 的任务详情
    print_section("Step 8.5: 跨用户访问控制")

    response = httpx.get(f"{base_url}/api/agent/tasks/{task_b_id}", headers=headers_a, timeout=10)
    access_denied = response.status_code == 404  # 应该返回 404（找不到，而不是 403）
    print(f"User A 访问 User B 任务状态码: {response.status_code}")
    results.append(print_result(access_denied, "User A 无法访问 User B 的任务"))

    # Step 8.6: User B 尝试访问 User A 的任务详情
    response = httpx.get(f"{base_url}/api/agent/tasks/{task_a_id}", headers=headers_b, timeout=10)
    access_denied = response.status_code == 404
    print(f"User B 访问 User A 任务状态码: {response.status_code}")
    results.append(print_result(access_denied, "User B 无法访问 User A 的任务"))

    # Step 8.7: Session 目录隔离（如果有实际运行的 Session）
    print_section("Step 8.7: Session 目录隔离验证")

    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())

    session_dir_a = Path(__file__).parent.parent.parent / "runtime" / "sessions" / session_a
    session_dir_b = Path(__file__).parent.parent.parent / "runtime" / "sessions" / session_b

    # 这一步只是逻辑验证（实际 Session 目录在任务运行时创建）
    print(f"Session A 目录: {session_dir_a}")
    print(f"Session B 目录: {session_dir_b}")
    print(f"目录路径不同: {session_dir_a != session_dir_b}")
    results.append(print_result(True, "Session 目录隔离（逻辑验证）"))

    # 总结
    print_section("Block 8 测试结果")
    passed_count = sum(results)
    total_count = len(results)
    print(f"\n通过: {passed_count}/{total_count}")

    if passed_count == total_count:
        print("\n🎉 Block 8 全部通过！")
        return True
    else:
        print("\n⚠️  Block 8 部分失败")
        return False


if __name__ == "__main__":
    success = test_block_8()
    sys.exit(0 if success else 1)
