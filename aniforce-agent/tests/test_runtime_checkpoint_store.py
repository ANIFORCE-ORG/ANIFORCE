from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

agent_root = Path(__file__).parent.parent
sys.path.insert(0, str(agent_root))

from app.agent.checkpoints import RuntimeCheckpointClaimError, RuntimeCheckpointStore
from app.agent.runtime_migrations import RuntimeSchemaMigrator


def test_only_one_concurrent_resume_can_claim_checkpoint() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        store = RuntimeCheckpointStore(engine)
        try:
            await RuntimeSchemaMigrator(engine).migrate()
            checkpoint = await store.create(
                run_id="run_1",
                session_id="session_1",
                user_id="user_1",
                interruptions=[],
                run_state={},
            )

            first, second = await asyncio.gather(
                store.claim_for_resume(checkpoint["id"], "user_1"),
                store.claim_for_resume(checkpoint["id"], "user_1"),
            )

            claimed = [item for item in (first, second) if item is not None]
            assert len(claimed) == 1
            assert claimed[0]["status"] == "resuming"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_expired_checkpoint_cannot_be_claimed() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        store = RuntimeCheckpointStore(engine)
        try:
            await RuntimeSchemaMigrator(engine).migrate()
            checkpoint = await store.create(
                run_id="run_1",
                session_id="session_1",
                user_id="user_1",
                interruptions=[],
                run_state={},
            )
            expired_at = (datetime.utcnow() - timedelta(seconds=1)).isoformat()
            async with store.engine.begin() as conn:
                await conn.execute(
                    text("UPDATE runtime_checkpoints SET expires_at=:expires_at WHERE id=:id"),
                    {"expires_at": expired_at, "id": checkpoint["id"]},
                )

            claimed = await store.claim_for_resume(checkpoint["id"], "user_1")
            current = await store.get(checkpoint["id"], "user_1")

            assert claimed is None
            assert current is not None
            assert current["status"] == "expired"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_file_sqlite_allows_only_one_claim_across_engines() -> None:
    async def scenario() -> None:
        project_root = agent_root.parent
        db_path = project_root / "drafts" / "260710" / "260710_03_checkpoint_claim_test.db"
        db_path.unlink(missing_ok=True)
        db_url = f"sqlite+aiosqlite:///{db_path}"
        first_engine = create_async_engine(db_url, connect_args={"timeout": 5})
        second_engine = create_async_engine(db_url, connect_args={"timeout": 5})
        first_store = RuntimeCheckpointStore(first_engine)
        second_store = RuntimeCheckpointStore(second_engine)
        try:
            await RuntimeSchemaMigrator(first_engine).migrate()
            checkpoint = await first_store.create(
                run_id="run_1",
                session_id="session_1",
                user_id="user_1",
                interruptions=[],
                run_state={},
            )
            first, second = await asyncio.gather(
                first_store.claim_for_resume(checkpoint["id"], "user_1"),
                second_store.claim_for_resume(checkpoint["id"], "user_1"),
            )

            assert len([item for item in (first, second) if item is not None]) == 1
            current = await first_store.get(checkpoint["id"], "user_1")
            assert current is not None
            assert current["status"] == "resuming"
        finally:
            await first_engine.dispose()
            await second_engine.dispose()
            db_path.unlink(missing_ok=True)

    asyncio.run(scenario())


def test_mark_status_respects_expected_status() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        store = RuntimeCheckpointStore(engine)
        try:
            await RuntimeSchemaMigrator(engine).migrate()
            checkpoint = await store.create(
                run_id="run_1",
                session_id="session_1",
                user_id="user_1",
                interruptions=[],
                run_state={},
            )
            await store.mark_status(checkpoint["id"], "user_1", "expired")
            try:
                await store.mark_status(
                    checkpoint["id"],
                    "user_1",
                    "completed",
                    expected_status="resuming",
                )
            except RuntimeCheckpointClaimError as exc:
                assert exc.code == "CHECKPOINT_FENCED"
                assert exc.status_code == 409
            else:
                raise AssertionError("stale checkpoint completion must be fenced")
            current = await store.get(checkpoint["id"], "user_1")
            assert current is not None and current["status"] == "expired"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_stale_resuming_checkpoint_is_failed_without_replay() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        store = RuntimeCheckpointStore(engine)
        try:
            await RuntimeSchemaMigrator(engine).migrate()
            stale = await store.create(
                run_id="run_stale",
                session_id="session_1",
                user_id="user_1",
                interruptions=[],
                run_state={},
            )
            fresh = await store.create(
                run_id="run_fresh",
                session_id="session_1",
                user_id="user_1",
                interruptions=[],
                run_state={},
            )
            await store.claim_for_resume(stale["id"], "user_1")
            await store.claim_for_resume(fresh["id"], "user_1")
            async with engine.begin() as conn:
                await conn.execute(
                    text("UPDATE runtime_checkpoints SET claimed_at=:claimed_at WHERE id=:id"),
                    {
                        "claimed_at": (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
                        "id": stale["id"],
                    },
                )

            recovered = await store.recover_stale_resuming(datetime.utcnow() - timedelta(minutes=5))
            stale_current = await store.get(stale["id"], "user_1")
            fresh_current = await store.get(fresh["id"], "user_1")

            assert recovered == 1
            assert stale_current is not None
            assert stale_current["status"] == "failed"
            assert stale_current["error"]["code"] == "CHECKPOINT_RESUME_INTERRUPTED"
            assert fresh_current is not None
            assert fresh_current["status"] == "resuming"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_claim_persists_edited_arguments_atomically() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        store = RuntimeCheckpointStore(engine)
        try:
            await RuntimeSchemaMigrator(engine).migrate()
            checkpoint = await store.create(
                run_id="run_1",
                session_id="session_1",
                user_id="user_1",
                interruptions=[],
                run_state={},
            )

            claimed = await store.claim_for_resume(
                checkpoint["id"],
                "user_1",
                approved_arguments={"budget": 100},
                argument_diff=[{"field": "budget", "new": 100}],
            )

            assert claimed is not None
            assert claimed["status"] == "resuming"
            assert claimed["approved_arguments"] == {"budget": 100}
            assert claimed["argument_diff"] == [{"field": "budget", "new": 100}]
        finally:
            await engine.dispose()

    asyncio.run(scenario())
