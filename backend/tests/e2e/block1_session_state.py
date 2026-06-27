"""Block 1 E2E: Minimal Session State repository."""

import asyncio
import os
import sys
import time
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.config.database import Base  # noqa: E402
from app.repositories.impl.sqlite_session_state_repo import (  # noqa: E402
    SessionStateVersionConflict,
    SqliteSessionStateRepository,
)

TEST_DB = ROOT / "data" / "sqlite" / "test_session_state.db"
LOG_PATH = ROOT / "logs" / "e2e_block1_session_state.log"


class CheckRunner:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.lines: list[str] = []
        self.started = time.time()

    def log(self, message: str) -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        print(line)
        self.lines.append(line)

    def check(self, condition: bool, label: str) -> None:
        if condition:
            self.passed += 1
            self.log(f"✓ {self.passed}/10 {label}")
            return
        self.failed += 1
        self.log(f"✗ {label}")
        raise AssertionError(label)

    def finish(self) -> None:
        elapsed = time.time() - self.started
        self.log(f"input=sqlite:///{TEST_DB}")
        self.log("output=Block 1 Session State repository verification")
        self.log(f"errors={self.failed}")
        self.log(f"elapsed={elapsed:.2f}s")
        self.log(f"summary=passed {self.passed}/10, failed {self.failed}")
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


async def main() -> None:
    runner = CheckRunner()
    TEST_DB.parent.mkdir(parents=True, exist_ok=True)
    if TEST_DB.exists():
        TEST_DB.unlink()

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{TEST_DB}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    session_id = "sess_block1_001"
    user_id = "user_block1_001"
    other_user_id = "user_block1_other"

    async with session_maker() as session:
        repo = SqliteSessionStateRepository(session)

        created = await repo.create(session_id=session_id, user_id=user_id)
        await session.commit()
        runner.check(created["session_id"] == session_id and created["version"] == 1, "创建 state 成功")

        fetched = await repo.get(session_id, user_id)
        runner.check(fetched is not None and fetched["user_id"] == user_id, "查询 state 成功")

        isolated = await repo.get(session_id, other_user_id)
        runner.check(isolated is None, "跨用户查询为空")

        updated = await repo.update_linked_entities(
            session_id,
            user_id,
            expected_version=fetched["version"],
            linked_entities={"project_id": "proj_block1", "campaign_ids": ["camp_a"]},
        )
        await session.commit()
        runner.check(updated["linked_entities"]["project_id"] == "proj_block1", "更新 linked_entities 成功")

        entry = {
            "id": "chg_block1_001",
            "run_id": "run_block1_001",
            "tool_call_id": "tool_block1_001",
            "entity_type": "project",
            "entity_id": "proj_block1",
            "action": "created",
            "field": None,
            "old_value": None,
            "new_value": {"name": "Block1 Project"},
            "rollbackable": False,
            "created_at": "2026-06-19T00:00:00",
        }
        changed = await repo.append_changelog(
            session_id,
            user_id,
            expected_version=updated["version"],
            entry=entry,
        )
        await session.commit()
        runner.check(len(changed["changelog"]) == 1 and changed["changelog"][0]["id"] == entry["id"], "append changelog 成功")

        snapshotted = await repo.update_ui_snapshot(
            session_id,
            user_id,
            expected_version=changed["version"],
            ui_snapshot={"route": "/projects/proj_block1", "activePanel": "context"},
        )
        await session.commit()
        runner.check(snapshotted["ui_snapshot"]["activePanel"] == "context", "update ui_snapshot 成功")

        runner.check(snapshotted["version"] == 4, "version 正常递增")

        try:
            await repo.update_with_version(
                session_id,
                user_id,
                expected_version=1,
                summary="stale update should fail",
            )
            await session.commit()
            version_conflict = False
        except SessionStateVersionConflict:
            await session.rollback()
            version_conflict = True
        runner.check(version_conflict, "version 冲突返回失败")

        current = await repo.get(session_id, user_id)
        errored = await repo.mark_error(
            session_id,
            user_id,
            expected_version=current["version"],
            error={"code": "TEST_ERROR", "message": "block1 expected error"},
        )
        await session.commit()
        runner.check(errored["status"] == "error" and errored["last_error"]["code"] == "TEST_ERROR", "mark_error 记录 last_error")

    async with session_maker() as session:
        repo = SqliteSessionStateRepository(session)
        persisted = await repo.get(session_id, user_id)
        runner.check(persisted is not None and persisted["status"] == "error", "重启后数据仍在")

    await engine.dispose()
    runner.finish()


if __name__ == "__main__":
    asyncio.run(main())
