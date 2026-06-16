"""Task Repository - 任务数据访问层"""
import json
from datetime import datetime
from typing import Optional, List
import aiosqlite
from app.models import AgentTask, TaskStatus


class TaskRepository:
    """Task 数据访问"""
    
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
    
    async def create(self, task: AgentTask) -> AgentTask:
        """创建任务"""
        now = datetime.utcnow().isoformat()
        task.created_at = datetime.fromisoformat(now)
        task.updated_at = datetime.fromisoformat(now)
        
        await self.db.execute(
            """
            INSERT INTO tasks (
                task_id, user_id, task_type, status, title, session_id,
                input_data, result, error, context, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.task_id,
                task.user_id,
                task.task_type,
                task.status.value,
                task.title,
                task.session_id,
                json.dumps(task.input_data) if task.input_data else None,
                json.dumps(task.result) if task.result else None,
                json.dumps(task.error) if task.error else None,
                json.dumps(task.context) if task.context else None,
                now,
                now,
            ),
        )
        await self.db.commit()
        return task
    
    async def get_by_id(self, task_id: str, user_id: str) -> Optional[AgentTask]:
        """根据 ID 获取任务（权限过滤）"""
        cursor = await self.db.execute(
            """
            SELECT task_id, user_id, task_type, status, title, session_id,
                   input_data, result, error, context, created_at, updated_at
            FROM tasks
            WHERE task_id = ? AND user_id = ?
            """,
            (task_id, user_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_task(row)
    
    async def list_by_user(
        self, user_id: str, task_type: Optional[str] = None, limit: int = 50
    ) -> List[AgentTask]:
        """列出用户的任务"""
        if task_type:
            cursor = await self.db.execute(
                """
                SELECT task_id, user_id, task_type, status, title, session_id,
                       input_data, result, error, context, created_at, updated_at
                FROM tasks
                WHERE user_id = ? AND task_type = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, task_type, limit),
            )
        else:
            cursor = await self.db.execute(
                """
                SELECT task_id, user_id, task_type, status, title, session_id,
                       input_data, result, error, context, created_at, updated_at
                FROM tasks
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
        rows = await cursor.fetchall()
        return [self._row_to_task(row) for row in rows]
    
    async def update_status(
        self, task_id: str, user_id: str, status: TaskStatus
    ) -> Optional[AgentTask]:
        """更新任务状态"""
        now = datetime.utcnow().isoformat()
        await self.db.execute(
            """
            UPDATE tasks
            SET status = ?, updated_at = ?
            WHERE task_id = ? AND user_id = ?
            """,
            (status.value, now, task_id, user_id),
        )
        await self.db.commit()
        return await self.get_by_id(task_id, user_id)
    
    async def update_result(
        self, task_id: str, user_id: str, result: dict
    ) -> Optional[AgentTask]:
        """更新任务结果"""
        now = datetime.utcnow().isoformat()
        await self.db.execute(
            """
            UPDATE tasks
            SET result = ?, status = ?, updated_at = ?
            WHERE task_id = ? AND user_id = ?
            """,
            (json.dumps(result), TaskStatus.COMPLETED.value, now, task_id, user_id),
        )
        await self.db.commit()
        return await self.get_by_id(task_id, user_id)
    
    async def update_error(
        self, task_id: str, user_id: str, error: dict
    ) -> Optional[AgentTask]:
        """更新任务错误"""
        now = datetime.utcnow().isoformat()
        await self.db.execute(
            """
            UPDATE tasks
            SET error = ?, status = ?, updated_at = ?
            WHERE task_id = ? AND user_id = ?
            """,
            (json.dumps(error), TaskStatus.ERROR.value, now, task_id, user_id),
        )
        await self.db.commit()
        return await self.get_by_id(task_id, user_id)
    
    def _row_to_task(self, row) -> AgentTask:
        """数据库行转换为模型"""
        return AgentTask(
            task_id=row[0],
            user_id=row[1],
            task_type=row[2],
            status=TaskStatus(row[3]),
            title=row[4],
            session_id=row[5],
            input_data=json.loads(row[6]) if row[6] else None,
            result=json.loads(row[7]) if row[7] else None,
            error=json.loads(row[8]) if row[8] else None,
            context=json.loads(row[9]) if row[9] else None,
            created_at=datetime.fromisoformat(row[10]) if row[10] else None,
            updated_at=datetime.fromisoformat(row[11]) if row[11] else None,
        )
