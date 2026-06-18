"""Repository 测试"""
import pytest
import aiosqlite
from uuid import uuid4
from app.models import AgentTask, AgentEvent, TaskStatus
from app.repositories import TaskRepository, EventRepository


@pytest.fixture
async def test_db():
    """测试数据库"""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    
    # 创建表
    await db.execute("""
        CREATE TABLE tasks (
            task_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            session_id TEXT,
            input_data TEXT,
            result TEXT,
            error TEXT,
            context TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    await db.execute("""
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    await db.commit()
    
    yield db
    
    await db.close()


@pytest.mark.asyncio
async def test_task_create_and_get(test_db):
    """测试创建和获取任务"""
    repo = TaskRepository(test_db)
    
    task = AgentTask(
        task_id=str(uuid4()),
        user_id="user123",
        task_type="conversation",
        status=TaskStatus.PENDING,
        title="测试任务",
    )
    
    created_task = await repo.create(task)
    assert created_task.task_id == task.task_id
    assert created_task.created_at is not None
    
    fetched_task = await repo.get_by_id(task.task_id, "user123")
    assert fetched_task is not None
    assert fetched_task.user_id == "user123"
    assert fetched_task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_task_permission_filter(test_db):
    """测试任务权限过滤"""
    repo = TaskRepository(test_db)
    
    task = AgentTask(
        task_id=str(uuid4()),
        user_id="user123",
        task_type="conversation",
        status=TaskStatus.PENDING,
        title="测试任务",
    )
    
    await repo.create(task)
    
    # 正确的用户可以访问
    fetched = await repo.get_by_id(task.task_id, "user123")
    assert fetched is not None
    
    # 错误的用户无法访问
    fetched = await repo.get_by_id(task.task_id, "user456")
    assert fetched is None


@pytest.mark.asyncio
async def test_event_append_and_list(test_db):
    """测试追加和列出事件"""
    repo = EventRepository(test_db)
    
    task_id = str(uuid4())
    
    event1 = AgentEvent(
        event_id=str(uuid4()),
        task_id=task_id,
        event_type="message.started",
        payload={"content": "Hello"},
        sequence=0,
    )
    
    event2 = AgentEvent(
        event_id=str(uuid4()),
        task_id=task_id,
        event_type="message.completed",
        payload={"content": "Hello World"},
        sequence=1,
    )
    
    await repo.append(event1)
    await repo.append(event2)
    
    events = await repo.list_by_task(task_id)
    assert len(events) == 2
    assert events[0].sequence == 0
    assert events[1].sequence == 1


@pytest.mark.asyncio
async def test_event_after_sequence(test_db):
    """测试断点续传"""
    repo = EventRepository(test_db)
    
    task_id = str(uuid4())
    
    for i in range(5):
        event = AgentEvent(
            event_id=str(uuid4()),
            task_id=task_id,
            event_type=f"event_{i}",
            payload={"index": i},
            sequence=i,
        )
        await repo.append(event)
    
    # 获取序号 2 之后的事件
    events = await repo.list_by_task(task_id, after_sequence=2)
    assert len(events) == 2  # 序号 3 和 4
    assert events[0].sequence == 3
    assert events[1].sequence == 4
