from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

agent_root = Path(__file__).parent.parent
sys.path.insert(0, str(agent_root))

from app.agent.checkpoints import RuntimeCheckpointStore


def test_only_one_concurrent_resume_can_claim_checkpoint() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        store = RuntimeCheckpointStore(engine)
        try:
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


def test_claim_persists_edited_arguments_atomically() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        store = RuntimeCheckpointStore(engine)
        try:
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
