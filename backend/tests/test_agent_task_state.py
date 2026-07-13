import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent.sessions.task_state import normalize_task_state, persist_task_state
from app.config.database import Base
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository


def test_normalize_task_state_rejects_unknown_status_and_limits_sensitive_shape():
    assert normalize_task_state({"active_skill": {"name": "x", "version": "1", "status": "unknown"}}) == {}
    normalized = normalize_task_state({
        "active_skill": {
            "name": "campaign_diagnosis",
            "version": "1.0",
            "status": "collecting_inputs",
            "slots": {"campaign_id": "c1", "time_range_hours": 168},
            "missing_slots": ["campaign_id"],
            "load_reason": "matched_user_intent",
            "pending_question": "请选择计划",
        },
        "confirmed_entities": {"campaign": "c1"},
    })
    assert normalized["active_skill"]["slots"]["time_range_hours"] == 168
    assert normalized["confirmed_entities"] == {"campaign": "c1"}


def test_task_state_persists_with_session_versioning():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            maker = async_sessionmaker(engine, expire_on_commit=False)
            async with maker() as session:
                repo = SqliteSessionStateRepository(session)
                created = await repo.create("s1", "u1")
                updated = await persist_task_state(repo, "s1", "u1", {
                    "active_skill": {
                        "name": "campaign_diagnosis",
                        "version": "1.0",
                        "status": "collecting_inputs",
                        "slots": {"time_range_hours": 168},
                        "missing_slots": ["campaign_id"],
                    }
                })
                await session.commit()
                assert updated is not None
                assert updated["version"] == created["version"] + 1
                assert updated["task_state"]["active_skill"]["missing_slots"] == ["campaign_id"]
            async with maker() as session:
                persisted = await SqliteSessionStateRepository(session).get("s1", "u1")
                assert persisted["task_state"]["active_skill"]["name"] == "campaign_diagnosis"
        finally:
            await engine.dispose()

    asyncio.run(scenario())
