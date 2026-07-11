from __future__ import annotations

import asyncio
import multiprocessing as mp
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

agent_root = Path(__file__).parent.parent
project_root = agent_root.parent
sys.path.insert(0, str(agent_root))

from app.agent.runtime_migrations import RuntimeSchemaMigrator
from app.agent.runtime_sessions import RuntimeSessionOwnerMismatch, RuntimeSessionStore


def _migrate_runtime_database(db_path: str, output) -> None:
    async def scenario() -> None:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 5})
        try:
            await RuntimeSchemaMigrator(engine).migrate()
            output.put(None)
        except Exception as exc:
            output.put(repr(exc))
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_runtime_migration_is_safe_across_processes() -> None:
    db_path = project_root / "drafts" / "260710" / f"260710_19_runtime_migration_race_{uuid4().hex}.db"
    context = mp.get_context("spawn")
    output = context.Queue()
    processes = [context.Process(target=_migrate_runtime_database, args=(str(db_path), output)) for _ in range(2)]
    try:
        for process in processes:
            process.start()
        results = [output.get(timeout=15) for _ in processes]
        for process in processes:
            process.join(15)
            assert process.exitcode == 0
        assert results == [None, None]
        async def verify() -> None:
            engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
            try:
                async with engine.connect() as conn:
                    rows = await conn.execute(text("SELECT version FROM runtime_schema_migrations ORDER BY version"))
                    assert [row[0] for row in rows.fetchall()] == [1, 2, 3]
            finally:
                await engine.dispose()
        asyncio.run(verify())
    finally:
        db_path.unlink(missing_ok=True)


def test_runtime_migration_upgrades_legacy_checkpoint_schema_idempotently() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "CREATE TABLE runtime_checkpoints ("
                        "id TEXT PRIMARY KEY, run_id TEXT NOT NULL, session_id TEXT NOT NULL, "
                        "user_id TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL, "
                        "interruptions_json TEXT NOT NULL, run_state_json TEXT NOT NULL, "
                        "sdk_version TEXT, agent_version TEXT, expires_at TEXT NOT NULL, "
                        "created_at TEXT NOT NULL, resolved_at TEXT, error_json TEXT)"
                    )
                )

            migrator = RuntimeSchemaMigrator(engine)
            await migrator.migrate()
            await migrator.migrate()

            async with engine.connect() as conn:
                columns = await conn.execute(text("PRAGMA table_info(runtime_checkpoints)"))
                names = {row[1] for row in columns.fetchall()}
                versions = await conn.execute(text("SELECT version FROM runtime_schema_migrations"))
                sessions = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='runtime_sessions'")
                )

            assert {
                "approved_arguments_json",
                "argument_diff_json",
                "version",
                "claimed_at",
                "claimed_by",
                "context_schema_version",
            }.issubset(names)
            assert [row[0] for row in versions.fetchall()] == [1, 2, 3]
            assert sessions.scalar_one() == "runtime_sessions"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_runtime_session_owner_is_atomic_across_engines() -> None:
    async def scenario() -> None:
        db_path = project_root / "drafts" / "260710" / "260710_05_runtime_owner_test.db"
        db_path.unlink(missing_ok=True)
        db_url = f"sqlite+aiosqlite:///{db_path}"
        first_engine = create_async_engine(db_url, connect_args={"timeout": 5})
        second_engine = create_async_engine(db_url, connect_args={"timeout": 5})
        try:
            await RuntimeSchemaMigrator(first_engine).migrate()
            first_store = RuntimeSessionStore(first_engine)
            second_store = RuntimeSessionStore(second_engine)

            results = await asyncio.gather(
                first_store.register_or_validate("session_1", "user_1"),
                second_store.register_or_validate("session_1", "user_2"),
                return_exceptions=True,
            )

            assert sum(item is None for item in results) == 1
            assert sum(isinstance(item, RuntimeSessionOwnerMismatch) for item in results) == 1
            async with first_engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT user_id FROM runtime_sessions WHERE session_id='session_1'")
                )
            assert result.scalar_one() in {"user_1", "user_2"}
        finally:
            await first_engine.dispose()
            await second_engine.dispose()
            db_path.unlink(missing_ok=True)

    asyncio.run(scenario())
