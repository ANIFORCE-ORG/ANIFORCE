from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
project_root = backend_root.parent
sys.path.insert(0, str(backend_root))

from app.config.database import Base
from app.models import AgentSession
from app.repositories.impl.sqlite_agent_fact_repo import SqliteAgentArtifactRepository, SqliteAgentToolCallRepository
from app.repositories.impl.sqlite_agent_message_repo import SqliteAgentMessageRepository
from app.repositories.impl.sqlite_agent_run_event_repo import SqliteAgentRunEventRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.agent.services.run import AgentRunService
from app.agent.services.snapshot import AgentSnapshotService


def test_phase1_facts_replay_snapshot_and_lease_claim() -> None:
    async def scenario() -> None:
        db_path = project_root / "drafts" / "260710" / "260710_11_phase1_recovery_test.db"
        db_path.unlink(missing_ok=True)
        engine_a = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        engine_b = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        maker_a = async_sessionmaker(engine_a, expire_on_commit=False)
        maker_b = async_sessionmaker(engine_b, expire_on_commit=False)
        try:
            async with engine_a.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with maker_a() as session:
                session.add(
                    AgentSession(
                        session_id="session_phase1",
                        user_id="user_1",
                        title="Phase 1",
                        status="active",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                service = AgentRunService(SqliteAgentRunRepository(session))
                run, reused = await service.create_or_reuse(
                    session_id="session_phase1",
                    user_id="user_1",
                    input_text="hello",
                    idempotency_key="phase1-key",
                    execution_context={"task_type": "conversation"},
                )
                assert reused is False
                await SqliteAgentMessageRepository(session).create(
                    session_id="session_phase1",
                    user_id="user_1",
                    role="user",
                    content_json={"blocks": [{"type": "text", "text": "hello"}]},
                    run_id=run["run_id"],
                )
                await session.commit()

            async def claim(maker, worker_id):
                async with maker() as session:
                    claimed = await SqliteAgentRunRepository(session).claim_next(worker_id)
                    await session.commit()
                    return claimed

            claims = await asyncio.gather(claim(maker_a, "worker-a"), claim(maker_b, "worker-b"))
            winners = [item for item in claims if item]
            assert len(winners) == 1
            worker_id = winners[0]["lease_owner"]

            async with maker_a() as session:
                repo = SqliteAgentRunRepository(session)
                assert await repo.heartbeat(run["run_id"], worker_id) is True
                service = AgentRunService(repo)
                started = await service.mark_running(run["run_id"], "user_1")
                assert started and started["status"] == "running"
                await SqliteAgentToolCallRepository(session).upsert_started(
                    run_id=run["run_id"], tool_call_id="call_1", tool_name="search", arguments={"q": "x"}
                )
                await SqliteAgentToolCallRepository(session).complete(tool_call_id="call_1", result={"ok": True})
                await SqliteAgentArtifactRepository(session).create_projection(
                    session_id="session_phase1",
                    run_id=run["run_id"],
                    source_tool_call_id="call_1",
                    surface="project.list",
                    payload={"surface": "project.list", "items": []},
                )
                await SqliteAgentMessageRepository(session).create(
                    session_id="session_phase1",
                    user_id="user_1",
                    role="assistant",
                    content_json={"blocks": [{"type": "text", "text": "done"}]},
                    run_id=run["run_id"],
                )
                completed = await service.mark_completed(
                    run["run_id"], "user_1", usage={"total_tokens": 2}, final_output="done"
                )
                assert completed and completed["status"] == "completed"
                await session.commit()

            async with maker_b() as session:
                events = await SqliteAgentRunEventRepository(session).list_after(run["run_id"], 1, limit=1)
                assert [item["event_type"] for item in events] == ["run.completed"]
                assert events[0]["payload"]["final_output"] == "done"
                assert events[0]["is_terminal"] is True
                snapshot = await AgentSnapshotService(session).build("session_phase1", "user_1")
                assert snapshot is not None
                assert snapshot["latest_run"]["status"] == "completed"
                assert snapshot["last_persisted_sequence"] == 2
                assert [message["role"] for message in snapshot["messages"]] == ["user", "assistant"]
                assert snapshot["tool_calls"][0]["status"] == "completed"
                assert snapshot["artifacts"][0]["surface"] == "project.list"
                assert await AgentSnapshotService(session).build("session_phase1", "user_2") is None
        finally:
            await engine_a.dispose()
            await engine_b.dispose()
            db_path.unlink(missing_ok=True)

    asyncio.run(scenario())
