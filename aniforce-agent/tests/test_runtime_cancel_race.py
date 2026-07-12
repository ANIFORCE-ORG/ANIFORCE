import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.runtime.controls import RuntimeRunControlStore


def test_cancel_requested_before_runtime_start_survives_reset() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        store = RuntimeRunControlStore(engine)
        try:
            async with engine.begin() as conn:
                await conn.exec_driver_sql(
                    "CREATE TABLE runtime_run_controls ("
                    "run_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
                    "cancel_requested_at TEXT, updated_at TEXT NOT NULL)"
                )

            await store.reset("run_1", "user_1")
            assert await store.request_cancel("run_1", "user_1") is True
            await store.reset("run_1", "user_1")

            assert await store.is_cancel_requested("run_1", "user_1") is True
        finally:
            await engine.dispose()

    asyncio.run(scenario())
