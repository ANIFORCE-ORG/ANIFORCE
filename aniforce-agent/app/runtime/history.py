"""Read SDK session history with product-session ownership checks."""

from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession

from app.runtime.sessions import RuntimeSessionStore


class RuntimeHistoryReader:
    def __init__(self, adapter, database_url: str) -> None:
        self.adapter = adapter
        self.database_url = database_url

    async def read(self, session_id: str, user_id: str) -> list[dict]:
        sdk_session_id = session_id
        if self.adapter.api_mode == "chat_completions":
            sdk_session_id = f"chat_completions:{session_id}"

        engine = self.adapter._get_agent_db_engine(self.database_url)
        await RuntimeSessionStore(engine).require_owner(session_id, user_id)
        session = SQLAlchemySession(sdk_session_id, engine=engine, create_tables=False)
        items = await session.get_items()
        return [item if isinstance(item, dict) else dict(item) for item in items]
