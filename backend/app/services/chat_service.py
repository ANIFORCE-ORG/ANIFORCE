from app.repositories.protocols import ChatRepository


class ChatService:
    """对话业务逻辑 — 不包含任何 Demo/Mock 判断"""

    def __init__(self, chat_repo: ChatRepository):
        self._repo = chat_repo

    async def analyze_game(self, user_id: str, game_description: str, game_type: str) -> dict:
        session_id = await self._repo.create_session(
            user_id=user_id,
            game_info={"description": game_description, "type": game_type},
        )
        session = await self._repo.get_session(session_id)
        await self._repo.add_message(session_id, "ai", "分析完成！")
        return {
            "session_id": session_id,
            "message": {"role": "ai", "content": "分析完成！"},
            "analysis": session.get("analysis", {}) if session else {},
        }

    async def send_message(self, session_id: str, user_id: str, content: str) -> dict:
        await self._repo.add_message(session_id, "user", content)
        # 实际生产中这里会调用 AI 生成回复
        reply = f"收到您的消息：「{content}」，正在为您处理..."
        await self._repo.add_message(session_id, "ai", reply)
        return {"message": {"role": "ai", "content": reply}}

    async def get_history(self, session_id: str) -> dict:
        session = await self._repo.get_session(session_id)
        if not session:
            return {"messages": []}
        return {"messages": session.get("messages", [])}
