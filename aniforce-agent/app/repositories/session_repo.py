"""Session Repository - 会话数据访问层"""
from datetime import datetime
from typing import Optional, List
import aiosqlite
from app.models import Session


class SessionRepository:
    """Session 数据访问"""

    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create(self, session: Session) -> Session:
        """创建会话"""
        now = datetime.utcnow()
        session.created_at = now
        session.updated_at = now

        await self.db.execute(
            """
            INSERT INTO sessions (
                session_id, user_id, title, status, last_task_id, last_active_at,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.user_id,
                session.title,
                session.status,
                session.last_task_id,
                session.last_active_at.isoformat() if session.last_active_at else None,
                now.isoformat(),
                now.isoformat(),
            ),
        )
        await self.db.commit()
        return session

    async def get_by_id(self, session_id: str, user_id: str) -> Optional[Session]:
        """根据 ID 获取会话（权限过滤）"""
        cursor = await self.db.execute(
            """
            SELECT session_id, user_id, title, status, last_task_id, last_active_at,
                   created_at, updated_at
            FROM sessions
            WHERE session_id = ? AND user_id = ?
            """,
            (session_id, user_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_session(row)

    async def list_by_user(self, user_id: str, status: str = "active", limit: int = 50) -> List[Session]:
        """列出用户的会话"""
        cursor = await self.db.execute(
            """
            SELECT session_id, user_id, title, status, last_task_id, last_active_at,
                   created_at, updated_at
            FROM sessions
            WHERE user_id = ? AND status = ?
            ORDER BY last_active_at DESC
            LIMIT ?
            """,
            (user_id, status, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_session(row) for row in rows]

    async def update_title(self, session_id: str, user_id: str, title: str) -> bool:
        """更新会话标题"""
        now = datetime.utcnow()
        cursor = await self.db.execute(
            """
            UPDATE sessions
            SET title = ?, updated_at = ?
            WHERE session_id = ? AND user_id = ?
            """,
            (title, now.isoformat(), session_id, user_id),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def update_last_task(
        self, session_id: str, user_id: str, last_task_id: str, last_active_at: datetime
    ) -> bool:
        """更新会话最后 task 和最后活跃时间"""
        now = datetime.utcnow()
        cursor = await self.db.execute(
            """
            UPDATE sessions
            SET last_task_id = ?, last_active_at = ?, updated_at = ?
            WHERE session_id = ? AND user_id = ?
            """,
            (last_task_id, last_active_at.isoformat(), now.isoformat(), session_id, user_id),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def archive(self, session_id: str, user_id: str) -> bool:
        """归档会话"""
        now = datetime.utcnow()
        cursor = await self.db.execute(
            """
            UPDATE sessions
            SET status = ?, updated_at = ?
            WHERE session_id = ? AND user_id = ?
            """,
            ("archived", now.isoformat(), session_id, user_id),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    def _row_to_session(self, row) -> Session:
        """数据库行转换为模型"""
        return Session(
            session_id=row[0],
            user_id=row[1],
            title=row[2],
            status=row[3],
            last_task_id=row[4],
            last_active_at=datetime.fromisoformat(row[5]) if row[5] else None,
            created_at=datetime.fromisoformat(row[6]) if row[6] else None,
            updated_at=datetime.fromisoformat(row[7]) if row[7] else None,
        )
