"""
Agent Task Repository SQLite 实现

用于本地开发和单机部署，支持数据持久化。

遵循 Block 0 规范：
- 显式接收 user_id
- 查询时过滤 user_id
- 严格权限隔离
"""

import json
import sqlite3
from typing import Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio
from functools import wraps

from .base import AgentTaskRepository
from ..models import AgentTask, AgentTaskEvent, AgentTaskStatus


def async_to_sync(func):
    """装饰器：将同步方法包装为异步"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    return wrapper


class SQLiteAgentTaskRepository(AgentTaskRepository):
    """SQLite 版 Repository"""
    
    def __init__(self, db_path: str = "runtime/agent/tasks.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
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
                    rating INTEGER,
                    rating_comment TEXT,
                    public_share_token TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_user_type ON tasks(user_id, task_type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_task_sequence ON events(task_id, sequence)
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _task_from_row(self, row: sqlite3.Row) -> AgentTask:
        """从数据库行转换为 AgentTask"""
        return AgentTask(
            task_id=row["task_id"],
            user_id=row["user_id"],
            task_type=row["task_type"],
            status=AgentTaskStatus(row["status"]),
            title=row["title"],
            session_id=row["session_id"],
            input=json.loads(row["input_data"]) if row["input_data"] else None,
            result=json.loads(row["result"]) if row["result"] else None,
            error=json.loads(row["error"]) if row["error"] else None,
            rating=row["rating"],
            rating_comment=row["rating_comment"],
            public_share_token=row["public_share_token"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    
    def _event_from_row(self, row: sqlite3.Row) -> AgentTaskEvent:
        """从数据库行转换为 AgentTaskEvent"""
        return AgentTaskEvent(
            event_id=row["event_id"],
            task_id=row["task_id"],
            event_type=row["event_type"],
            payload=json.loads(row["payload"]),
            sequence=row["sequence"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
    
    @async_to_sync
    def _create_sync(self, task: AgentTask) -> AgentTask:
        """创建任务（同步）"""
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id, user_id, task_type, status, title, session_id,
                    input_data, result, error, rating, rating_comment,
                    public_share_token, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.user_id,
                    task.task_type,
                    task.status.value,
                    task.title,
                    task.session_id,
                    json.dumps(task.input) if task.input else None,
                    json.dumps(task.result) if task.result else None,
                    json.dumps(task.error) if task.error else None,
                    task.rating,
                    task.rating_comment,
                    task.public_share_token,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                ),
            )
            conn.commit()
            return task
        finally:
            conn.close()
    
    async def create(self, task: AgentTask) -> AgentTask:
        """创建任务"""
        return await self._create_sync(task)
    
    @async_to_sync
    def _get_user_task_sync(self, user_id: str, task_id: str) -> Optional[AgentTask]:
        """查询用户任务（同步）"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._task_from_row(row)
        finally:
            conn.close()
    
    async def get_user_task(self, user_id: str, task_id: str) -> Optional[AgentTask]:
        """查询用户任务（含权限校验）"""
        return await self._get_user_task_sync(user_id, task_id)
    
    @async_to_sync
    def _list_user_tasks_sync(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        task_type: Optional[str] = None,
        status: Optional[AgentTaskStatus] = None,
    ) -> List[AgentTask]:
        """查询用户任务列表（同步）"""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM tasks WHERE user_id = ?"
            params = [user_id]
            
            if task_type:
                query += " AND task_type = ?"
                params.append(task_type)
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            return [self._task_from_row(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    async def list_user_tasks(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        task_type: Optional[str] = None,
        status: Optional[AgentTaskStatus] = None,
    ) -> List[AgentTask]:
        """查询用户任务列表"""
        return await self._list_user_tasks_sync(
            user_id, limit, offset, task_type, status
        )
    
    @async_to_sync
    def _update_status_sync(
        self,
        task_id: str,
        status: AgentTaskStatus,
        updated_at: Optional[datetime] = None,
    ) -> None:
        """更新任务状态（同步）"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?",
                (
                    status.value,
                    (updated_at or datetime.utcnow()).isoformat(),
                    task_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    
    async def update_status(
        self,
        task_id: str,
        status: AgentTaskStatus,
        updated_at: Optional[datetime] = None,
    ) -> None:
        """更新任务状态"""
        await self._update_status_sync(task_id, status, updated_at)
    
    @async_to_sync
    def _update_task_error_sync(self, task_id: str, error: dict) -> None:
        """更新任务错误信息（同步）"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE tasks SET error = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(error), datetime.utcnow().isoformat(), task_id),
            )
            conn.commit()
        finally:
            conn.close()
    
    async def update_task_error(self, task_id: str, error: dict) -> None:
        """更新任务错误信息"""
        await self._update_task_error_sync(task_id, error)
    
    @async_to_sync
    def _update_task_result_sync(self, task_id: str, result: dict) -> None:
        """更新任务结果（同步）"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE tasks SET result = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(result), datetime.utcnow().isoformat(), task_id),
            )
            conn.commit()
        finally:
            conn.close()
    
    async def update_task_result(self, task_id: str, result: dict) -> None:
        """更新任务结果"""
        await self._update_task_result_sync(task_id, result)
    
    @async_to_sync
    def _append_event_sync(self, event: AgentTaskEvent) -> None:
        """追加事件（同步）"""
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO events (event_id, task_id, event_type, payload, sequence, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.task_id,
                    event.event_type,
                    json.dumps(event.payload),
                    event.sequence,
                    event.created_at.isoformat(),
                ),
            )
            # 同步更新 task 的 updated_at
            conn.execute(
                "UPDATE tasks SET updated_at = ? WHERE task_id = ?",
                (datetime.utcnow().isoformat(), event.task_id),
            )
            conn.commit()
        finally:
            conn.close()
    
    async def append_event(self, event: AgentTaskEvent) -> None:
        """追加事件"""
        await self._append_event_sync(event)
    
    @async_to_sync
    def _list_user_task_events_sync(
        self,
        user_id: str,
        task_id: str,
        after_sequence: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[AgentTaskEvent]:
        """查询用户任务事件（同步）"""
        conn = self._get_conn()
        try:
            # 先校验 task 归属
            task_cursor = conn.execute(
                "SELECT user_id FROM tasks WHERE task_id = ?", (task_id,)
            )
            task_row = task_cursor.fetchone()
            if not task_row or task_row["user_id"] != user_id:
                return []
            
            # 查询事件
            query = "SELECT * FROM events WHERE task_id = ?"
            params = [task_id]
            
            if after_sequence is not None:
                query += " AND sequence > ?"
                params.append(after_sequence)
            
            query += " ORDER BY sequence ASC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(query, params)
            return [self._event_from_row(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    async def list_user_task_events(
        self,
        user_id: str,
        task_id: str,
        after_sequence: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[AgentTaskEvent]:
        """查询用户任务事件（含权限校验）"""
        return await self._list_user_task_events_sync(
            user_id, task_id, after_sequence, limit
        )
    
    @async_to_sync
    def _count_user_tasks_sync(
        self,
        user_id: str,
        task_type: Optional[str] = None,
        status: Optional[AgentTaskStatus] = None,
    ) -> int:
        """统计用户任务数量（同步）"""
        conn = self._get_conn()
        try:
            query = "SELECT COUNT(*) as count FROM tasks WHERE user_id = ?"
            params = [user_id]
            
            if task_type:
                query += " AND task_type = ?"
                params.append(task_type)
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            cursor = conn.execute(query, params)
            return cursor.fetchone()["count"]
        finally:
            conn.close()
    
    async def count_user_tasks(
        self,
        user_id: str,
        task_type: Optional[str] = None,
        status: Optional[AgentTaskStatus] = None,
    ) -> int:
        """统计用户任务数量"""
        return await self._count_user_tasks_sync(user_id, task_type, status)
    
    @async_to_sync
    def _count_task_events_sync(self, task_id: str) -> int:
        """统计任务事件数量（同步）"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM events WHERE task_id = ?", (task_id,)
            )
            return cursor.fetchone()["count"]
        finally:
            conn.close()
    
    async def count_task_events(self, task_id: str) -> int:
        """统计任务事件数量"""
        return await self._count_task_events_sync(task_id)
    
    @async_to_sync
    def _list_timeout_tasks_sync(
        self,
        timeout_ms: int,
        status: AgentTaskStatus = AgentTaskStatus.RUNNING,
    ) -> List[AgentTask]:
        """查询超时任务（同步）"""
        conn = self._get_conn()
        try:
            timeout_date = datetime.utcnow() - timedelta(milliseconds=timeout_ms)
            cursor = conn.execute(
                """
                SELECT * FROM tasks
                WHERE status = ? AND updated_at < ?
                ORDER BY updated_at ASC
                """,
                (status.value, timeout_date.isoformat()),
            )
            return [self._task_from_row(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    async def list_timeout_tasks(
        self,
        timeout_ms: int,
        status: AgentTaskStatus = AgentTaskStatus.RUNNING,
    ) -> List[AgentTask]:
        """查询超时任务"""
        return await self._list_timeout_tasks_sync(timeout_ms, status)
