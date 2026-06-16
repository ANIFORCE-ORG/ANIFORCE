"""
SQLite 实现的 SessionStore（Claude SDK 会话持久化）

关键设计：
- 基于 claude_agent_sdk.SessionStore 接口
- 数据表：sessions (project_key, session_id, subpath, seq, entry, created_at)
- 序列号递增：每个 session 的 entry 按 seq 顺序存储
- 支持 subpath：多层会话结构
"""

import aiosqlite
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from claude_agent_sdk import SessionStore, SessionKey, SessionStoreEntry


class SQLiteSessionStore(SessionStore):
    """SQLite 实现的 SessionStore（本地持久化）"""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    async def _init_db(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    project_key TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    subpath TEXT NOT NULL DEFAULT '',
                    seq INTEGER NOT NULL,
                    entry TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (project_key, session_id, subpath, seq)
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_lookup
                ON sessions(project_key, session_id, subpath)
            """)
            await db.commit()

    async def append(self, key: SessionKey, entries: list[SessionStoreEntry]):
        """追加 Session 条目"""
        if not entries:
            return

        await self._init_db()

        project_key = key["project_key"]
        session_id = key["session_id"]
        subpath = key.get("subpath", "")

        async with aiosqlite.connect(self.db_path) as db:
            # 获取当前最大序号
            cursor = await db.execute(
                """
                SELECT COALESCE(MAX(seq), -1) FROM sessions
                WHERE project_key = ? AND session_id = ? AND subpath = ?
                """,
                (project_key, session_id, subpath)
            )
            row = await cursor.fetchone()
            max_seq = row[0] if row else -1

            # 批量插入
            values = [
                (
                    project_key,
                    session_id,
                    subpath,
                    max_seq + i + 1,
                    json.dumps(entry, ensure_ascii=False)
                )
                for i, entry in enumerate(entries)
            ]
            await db.executemany(
                "INSERT INTO sessions (project_key, session_id, subpath, seq, entry) VALUES (?, ?, ?, ?, ?)",
                values
            )
            await db.commit()

    async def load(self, key: SessionKey) -> list[SessionStoreEntry] | None:
        """加载 Session 条目"""
        await self._init_db()

        project_key = key["project_key"]
        session_id = key["session_id"]
        subpath = key.get("subpath", "")

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT entry FROM sessions
                WHERE project_key = ? AND session_id = ? AND subpath = ?
                ORDER BY seq ASC
                """,
                (project_key, session_id, subpath)
            )
            rows = await cursor.fetchall()
            return [json.loads(row[0]) for row in rows] if rows else None

    async def list_sessions(self, project_key: str) -> list[str]:
        """列出项目下所有 session ID"""
        await self._init_db()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT DISTINCT session_id FROM sessions
                WHERE project_key = ?
                ORDER BY session_id
                """,
                (project_key,)
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def delete(self, key: SessionKey):
        """删除 Session"""
        await self._init_db()

        project_key = key["project_key"]
        session_id = key["session_id"]
        subpath = key.get("subpath")

        async with aiosqlite.connect(self.db_path) as db:
            if subpath is not None:
                # 删除特定 subpath
                await db.execute(
                    "DELETE FROM sessions WHERE project_key = ? AND session_id = ? AND subpath = ?",
                    (project_key, session_id, subpath)
                )
            else:
                # 删除整个 session（所有 subpath）
                await db.execute(
                    "DELETE FROM sessions WHERE project_key = ? AND session_id = ?",
                    (project_key, session_id)
                )
            await db.commit()

    async def list_subkeys(self, key: SessionKey) -> list[str]:
        """列出 session 下所有 subpath"""
        await self._init_db()

        project_key = key["project_key"]
        session_id = key["session_id"]

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT DISTINCT subpath FROM sessions
                WHERE project_key = ? AND session_id = ? AND subpath != ''
                ORDER BY subpath
                """,
                (project_key, session_id)
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
