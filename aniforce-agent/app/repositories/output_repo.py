"""Task Output Repository - 任务产物数据访问层"""

import json
from datetime import datetime
from typing import List, Optional

import aiosqlite

from app.models.output import OutputStatus, OutputType, TaskOutput


class OutputRepository:
    """Task Output 数据访问"""

    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create(self, output: TaskOutput) -> TaskOutput:
        """创建任务产物"""
        now = datetime.utcnow().isoformat()
        output.created_at = datetime.fromisoformat(now)

        await self.db.execute(
            """
            INSERT INTO task_outputs (
                output_id, task_id, output_type, category, content,
                confidence, importance, actionable, requires_review, status,
                verified_by, verified_at, supersedes, superseded_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                output.output_id,
                output.task_id,
                output.output_type.value if isinstance(output.output_type, OutputType) else output.output_type,
                output.category,
                json.dumps(output.content, ensure_ascii=False),
                output.confidence,
                output.importance,
                int(output.actionable),
                int(output.requires_review),
                output.status.value if isinstance(output.status, OutputStatus) else output.status,
                output.verified_by,
                output.verified_at.isoformat() if output.verified_at else None,
                output.supersedes,
                output.superseded_by,
                now,
            ),
        )
        await self.db.commit()
        return output

    async def list_by_task(self, task_id: str) -> List[TaskOutput]:
        """列出任务产物"""
        cursor = await self.db.execute(
            """
            SELECT output_id, task_id, output_type, category, content,
                   confidence, importance, actionable, requires_review, status,
                   verified_by, verified_at, supersedes, superseded_by, created_at
            FROM task_outputs
            WHERE task_id = ?
            ORDER BY created_at ASC
            """,
            (task_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_output(row) for row in rows]

    async def get_by_id(self, output_id: str) -> Optional[TaskOutput]:
        """按 ID 获取任务产物"""
        cursor = await self.db.execute(
            """
            SELECT output_id, task_id, output_type, category, content,
                   confidence, importance, actionable, requires_review, status,
                   verified_by, verified_at, supersedes, superseded_by, created_at
            FROM task_outputs
            WHERE output_id = ?
            """,
            (output_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_output(row) if row else None

    async def update_status(
        self,
        output_id: str,
        status: OutputStatus,
        verified_by: Optional[str] = None,
    ) -> bool:
        """更新产物状态"""
        verified_at = datetime.utcnow().isoformat() if verified_by else None
        cursor = await self.db.execute(
            """
            UPDATE task_outputs
            SET status = ?, verified_by = ?, verified_at = ?
            WHERE output_id = ?
            """,
            (
                status.value if isinstance(status, OutputStatus) else status,
                verified_by,
                verified_at,
                output_id,
            ),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    def _row_to_output(self, row) -> TaskOutput:
        """数据库行转换为模型"""
        return TaskOutput(
            output_id=row[0],
            task_id=row[1],
            output_type=OutputType(row[2]),
            category=row[3],
            content=json.loads(row[4]) if row[4] else {},
            confidence=row[5],
            importance=row[6],
            actionable=bool(row[7]),
            requires_review=bool(row[8]),
            status=OutputStatus(row[9]),
            verified_by=row[10],
            verified_at=datetime.fromisoformat(row[11]) if row[11] else None,
            supersedes=row[12],
            superseded_by=row[13],
            created_at=datetime.fromisoformat(row[14]) if row[14] else None,
        )
