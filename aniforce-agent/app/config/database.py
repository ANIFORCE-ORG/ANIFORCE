"""SQLite 数据库连接管理"""
import aiosqlite
from pathlib import Path
from app.config.settings import get_settings


async def get_task_db():
    """获取 Task 数据库连接（依赖注入）"""
    settings = get_settings()
    db_path = Path(settings.TASK_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_task_db():
    """初始化 Task 数据库表"""
    settings = get_settings()
    db_path = Path(settings.TASK_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(str(db_path)) as db:
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

        # 创建 task_outputs 表（通用任务产物）
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_outputs (
                output_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                output_type TEXT NOT NULL,
                category TEXT,
                content TEXT NOT NULL,
                confidence REAL,
                importance TEXT,
                actionable INTEGER DEFAULT 0,
                requires_review INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending_review',
                verified_by TEXT,
                verified_at TEXT,
                supersedes TEXT,
                superseded_by TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
                FOREIGN KEY (supersedes) REFERENCES task_outputs(output_id),
                FOREIGN KEY (superseded_by) REFERENCES task_outputs(output_id)
            )
        """)

        # 创建事件索引
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_events_task_seq ON events(task_id, sequence)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id)")

        # 创建产物索引
        await db.execute("CREATE INDEX IF NOT EXISTS idx_task_outputs_task ON task_outputs(task_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_task_outputs_type ON task_outputs(output_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_task_outputs_status ON task_outputs(status)")

        await db.commit()
        print("✅ Task database initialized")
