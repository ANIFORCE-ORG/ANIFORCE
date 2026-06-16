"""Event Repository - 事件数据访问层"""
import json
from datetime import datetime
from typing import List, Optional
import aiosqlite
from app.models import AgentEvent


class EventRepository:
    """Event 数据访问"""
    
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
    
    async def append(self, event: AgentEvent) -> AgentEvent:
        """追加事件"""
        now = datetime.utcnow().isoformat()
        event.created_at = datetime.fromisoformat(now)
        
        await self.db.execute(
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
                now,
            ),
        )
        await self.db.commit()
        return event
    
    async def list_by_task(
        self, task_id: str, after_sequence: Optional[int] = None
    ) -> List[AgentEvent]:
        """列出任务的事件（支持断点续传）"""
        if after_sequence is not None:
            cursor = await self.db.execute(
                """
                SELECT event_id, task_id, event_type, payload, sequence, created_at
                FROM events
                WHERE task_id = ? AND sequence > ?
                ORDER BY sequence ASC
                """,
                (task_id, after_sequence),
            )
        else:
            cursor = await self.db.execute(
                """
                SELECT event_id, task_id, event_type, payload, sequence, created_at
                FROM events
                WHERE task_id = ?
                ORDER BY sequence ASC
                """,
                (task_id,),
            )
        rows = await cursor.fetchall()
        return [self._row_to_event(row) for row in rows]
    
    async def get_next_sequence(self, task_id: str) -> int:
        """获取任务的下一个序号"""
        cursor = await self.db.execute(
            """
            SELECT COALESCE(MAX(sequence), -1) + 1
            FROM events
            WHERE task_id = ?
            """,
            (task_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
    
    def _row_to_event(self, row) -> AgentEvent:
        """数据库行转换为模型"""
        return AgentEvent(
            event_id=row[0],
            task_id=row[1],
            event_type=row[2],
            payload=json.loads(row[3]),
            sequence=row[4],
            created_at=datetime.fromisoformat(row[5]) if row[5] else None,
        )
