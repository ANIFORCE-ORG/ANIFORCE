"""
端到端测试（E2E）

测试完整的用户流程：
1. 创建任务
2. 查询任务列表
3. 获取任务详情
4. 查询事件流（断点续传）
5. 多租户隔离
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.repositories.task_repo import TaskRepository
from app.repositories.event_repo import EventRepository
from app.services.task_service import TaskService
from app.agent.runtime import AgentRuntime
from app.models.task import TaskStatus


@pytest.fixture
async def task_service(test_db):
    """创建 TaskService 实例"""
    task_repo = TaskRepository(test_db)
    event_repo = EventRepository(test_db)
    agent_runtime = AgentRuntime()
    return TaskService(
        task_repo=task_repo,
        event_repo=event_repo,
        agent_runtime=agent_runtime,
    )


@pytest.mark.asyncio
async def test_full_task_lifecycle(task_service):
    """测试完整任务生命周期"""
    user_id = "user_001"

    # 1. 创建任务
    task = await task_service.create_task(
        user_id=user_id,
        task_type="conversation",
        title="测试对话",
        input_data={"prompt": "Hello"},
        session_id="session_001",
    )

    assert task.task_id is not None
    assert task.status == TaskStatus.PENDING
    assert task.user_id == user_id
    assert task.session_id == "session_001"

    # 2. 查询任务列表
    tasks = await task_service.list_tasks(user_id, limit=10)
    assert len(tasks) == 1
    assert tasks[0].task_id == task.task_id

    # 3. 获取任务详情
    retrieved_task = await task_service.get_task(task.task_id, user_id)
    assert retrieved_task is not None
    assert retrieved_task.task_id == task.task_id
    assert retrieved_task.title == "测试对话"


@pytest.mark.asyncio
async def test_multi_tenant_isolation(task_service):
    """测试多租户数据隔离"""
    user_a = "user_a"
    user_b = "user_b"

    # 用户 A 创建任务
    task_a = await task_service.create_task(
        user_id=user_a,
        task_type="conversation",
        title="用户 A 的任务",
        session_id="session_a",
    )

    # 用户 B 创建任务
    task_b = await task_service.create_task(
        user_id=user_b,
        task_type="conversation",
        title="用户 B 的任务",
        session_id="session_b",
    )

    # 用户 A 只能看到自己的任务
    tasks_a = await task_service.list_tasks(user_a, limit=10)
    assert len(tasks_a) == 1
    assert tasks_a[0].task_id == task_a.task_id

    # 用户 B 只能看到自己的任务
    tasks_b = await task_service.list_tasks(user_b, limit=10)
    assert len(tasks_b) == 1
    assert tasks_b[0].task_id == task_b.task_id

    # 用户 A 无法获取用户 B 的任务详情
    task_b_as_a = await task_service.get_task(task_b.task_id, user_a)
    assert task_b_as_a is None

    # 用户 B 无法获取用户 A 的任务详情
    task_a_as_b = await task_service.get_task(task_a.task_id, user_b)
    assert task_a_as_b is None


@pytest.mark.asyncio
async def test_event_stream_with_resume(task_service):
    """测试事件流断点续传"""
    user_id = "user_001"

    # 创建任务
    task = await task_service.create_task(
        user_id=user_id,
        task_type="conversation",
        title="事件流测试",
        session_id="session_001",
    )

    # 模拟添加多个事件
    from app.models.event import AgentEvent
    from datetime import datetime, timezone
    from uuid import uuid4

    for i in range(5):
        event = AgentEvent(
            event_id=f"evt_{uuid4().hex[:8]}",
            task_id=task.task_id,
            event_type="test_event",
            payload={"index": i},
            sequence=i,
            created_at=datetime.now(timezone.utc),
        )
        await task_service.event_repo.append(event)

    # 获取全部事件
    all_events = await task_service.get_task_events(task.task_id, user_id)
    assert len(all_events) == 5

    # 断点续传：从 sequence=2 之后开始
    resumed_events = await task_service.get_task_events(
        task.task_id, user_id, after_sequence=2
    )
    assert len(resumed_events) == 2  # sequence 3 和 4
    assert resumed_events[0].sequence == 3
    assert resumed_events[1].sequence == 4


@pytest.mark.asyncio
async def test_task_type_filtering(task_service):
    """测试按任务类型过滤"""
    user_id = "user_001"

    # 创建不同类型的任务
    await task_service.create_task(
        user_id=user_id,
        task_type="conversation",
        title="对话任务 1",
        session_id="session_001",
    )

    await task_service.create_task(
        user_id=user_id,
        task_type="conversation",
        title="对话任务 2",
        session_id="session_002",
    )

    await task_service.create_task(
        user_id=user_id,
        task_type="analysis",
        title="分析任务",
        session_id="session_003",
    )

    # 查询所有任务
    all_tasks = await task_service.list_tasks(user_id, limit=10)
    assert len(all_tasks) == 3

    # 只查询 conversation 类型
    conversation_tasks = await task_service.list_tasks(
        user_id, task_type="conversation", limit=10
    )
    assert len(conversation_tasks) == 2
    assert all(t.task_type == "conversation" for t in conversation_tasks)

    # 只查询 analysis 类型
    analysis_tasks = await task_service.list_tasks(
        user_id, task_type="analysis", limit=10
    )
    assert len(analysis_tasks) == 1
    assert analysis_tasks[0].task_type == "analysis"


@pytest.mark.asyncio
async def test_session_continuity(task_service):
    """测试会话延续性"""
    user_id = "user_001"
    session_id = "session_continuous"

    # 同一 session 创建多个任务（模拟多轮对话）
    task1 = await task_service.create_task(
        user_id=user_id,
        task_type="conversation",
        title="第一轮对话",
        input_data={"prompt": "你好"},
        session_id=session_id,
    )

    task2 = await task_service.create_task(
        user_id=user_id,
        task_type="conversation",
        title="第二轮对话",
        input_data={"prompt": "继续聊"},
        session_id=session_id,
    )

    # 查询该会话的所有任务
    tasks = await task_service.list_tasks(user_id, limit=10)
    session_tasks = [t for t in tasks if t.session_id == session_id]

    assert len(session_tasks) == 2
    assert session_tasks[0].session_id == session_id
    assert session_tasks[1].session_id == session_id
