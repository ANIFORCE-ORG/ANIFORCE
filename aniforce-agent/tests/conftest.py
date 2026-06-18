"""
Pytest 配置和共享 fixtures
"""
import pytest
import aiosqlite


@pytest.fixture
async def test_db():
    """创建测试数据库"""
    # 使用内存数据库
    db = await aiosqlite.connect(":memory:")

    # 创建 tasks 表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
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

    # 创建索引
    await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_type ON tasks(user_id, task_type)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC)")

    # 创建 events 表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
        )
    """)

    # 创建事件索引
    await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_events_task_seq ON events(task_id, sequence)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id)")

    await db.commit()

    yield db

    # 关闭连接
    await db.close()

