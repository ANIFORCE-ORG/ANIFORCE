"""
Block 1 功能验证脚本

验证：
1. 模型创建和序列化
2. Repository 权限隔离
3. Service 层业务逻辑
4. 错误处理
"""

import asyncio
from datetime import datetime

from app.agent_platform.models import AgentTask, AgentTaskEvent, AgentTaskStatus, EventType
from app.agent_platform.repositories.memory import MemoryAgentTaskRepository
from app.agent_platform.errors import AppError, AgentErrorCode
from app.services.agent_task_service import AgentTaskService


async def test_repository_isolation():
    """测试 Repository 权限隔离"""
    print("=" * 60)
    print("测试 1: Repository 权限隔离")
    print("=" * 60)
    
    repo = MemoryAgentTaskRepository()
    
    # 用户 A 创建任务
    task_a = AgentTask(
        task_id="task_001",
        user_id="user_a",
        task_type="conversation",
        title="User A's task",
        status=AgentTaskStatus.PENDING,
    )
    await repo.create(task_a)
    print(f"✓ User A 创建任务: {task_a.task_id}")
    
    # 用户 B 尝试访问用户 A 的任务
    task = await repo.get_user_task("user_b", "task_001")
    assert task is None, "用户 B 不应该能访问用户 A 的任务"
    print("✓ User B 无法访问 User A 的任务（权限隔离成功）")
    
    # 用户 A 可以访问自己的任务
    task = await repo.get_user_task("user_a", "task_001")
    assert task is not None, "用户 A 应该能访问自己的任务"
    print(f"✓ User A 成功访问自己的任务: {task.title}")
    
    print()


async def test_event_sequence():
    """测试事件序号和增量查询"""
    print("=" * 60)
    print("测试 2: 事件序号和增量查询")
    print("=" * 60)
    
    repo = MemoryAgentTaskRepository()
    
    # 创建任务
    task = AgentTask(
        task_id="task_002",
        user_id="user_a",
        task_type="conversation",
        title="Event test",
        status=AgentTaskStatus.RUNNING,
    )
    await repo.create(task)
    
    # 写入事件
    events = [
        AgentTaskEvent(
            event_id=f"event_{i}",
            task_id="task_002",
            event_type=EventType.MESSAGE_UPDATED,
            payload={"delta": f"chunk_{i}"},
            sequence=i,
        )
        for i in range(5)
    ]
    
    for event in events:
        await repo.append_event(event)
    
    print(f"✓ 写入 {len(events)} 个事件")
    
    # 查询所有事件
    all_events = await repo.list_user_task_events("user_a", "task_002")
    assert len(all_events) == 5
    print(f"✓ 查询所有事件: {len(all_events)} 个")
    
    # 增量查询（after_sequence=2）
    new_events = await repo.list_user_task_events("user_a", "task_002", after_sequence=2)
    assert len(new_events) == 2  # sequence 3, 4
    print(f"✓ 增量查询（after_sequence=2）: {len(new_events)} 个事件")
    print(f"  事件序号: {[e.sequence for e in new_events]}")
    
    print()


async def test_service_layer():
    """测试 Service 层"""
    print("=" * 60)
    print("测试 3: Service 层业务逻辑")
    print("=" * 60)
    
    repo = MemoryAgentTaskRepository()
    service = AgentTaskService(repo)
    
    # 创建任务
    task = await service.create_task(
        user_id="user_a",
        task_type="conversation",
        title="Service test task",
    )
    print(f"✓ 创建任务: {task.task_id}")
    
    # 查询任务
    task = await service.get_task("user_a", task.task_id)
    print(f"✓ 查询任务: {task.title}")
    
    # 尝试用其他用户访问
    try:
        await service.get_task("user_b", task.task_id)
        assert False, "应该抛出 TASK_NOT_FOUND 异常"
    except AppError as e:
        assert e.code == AgentErrorCode.TASK_NOT_FOUND
        print(f"✓ 权限校验成功: {e.message}")
    
    # 查询任务列表
    tasks, total = await service.list_tasks("user_a")
    assert len(tasks) == 1
    assert total == 1
    print(f"✓ 查询任务列表: {len(tasks)} 个任务")
    
    print()


async def test_timeout_recovery():
    """测试超时恢复"""
    print("=" * 60)
    print("测试 4: 超时任务恢复")
    print("=" * 60)
    
    repo = MemoryAgentTaskRepository()
    
    # 创建一个旧的 running 任务
    old_task = AgentTask(
        task_id="task_old",
        user_id="user_a",
        task_type="conversation",
        title="Old running task",
        status=AgentTaskStatus.RUNNING,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),  # 很久没更新
    )
    await repo.create(old_task)
    
    # 创建一个新的 running 任务
    new_task = AgentTask(
        task_id="task_new",
        user_id="user_a",
        task_type="conversation",
        title="New running task",
        status=AgentTaskStatus.RUNNING,
    )
    await repo.create(new_task)
    
    # 查询超时任务（超时 1 小时）
    timeout_tasks = await repo.list_timeout_tasks(timeout_ms=60 * 60 * 1000)
    
    assert len(timeout_tasks) == 1
    assert timeout_tasks[0].task_id == "task_old"
    print(f"✓ 查询超时任务: {len(timeout_tasks)} 个")
    print(f"  超时任务: {timeout_tasks[0].task_id} (updated_at: {timeout_tasks[0].updated_at})")
    
    print()


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Block 1 功能验证")
    print("=" * 60 + "\n")
    
    await test_repository_isolation()
    await test_event_sequence()
    await test_service_layer()
    await test_timeout_recovery()
    
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
