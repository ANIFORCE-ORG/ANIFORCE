import asyncio
import uuid
from app.config.settings import get_settings

MOCK_ANALYSIS = {
    "trends": [
        {"id": "1", "name": "Boss挑战", "growth": 45, "description": "RPG玩家喜欢高难度Boss战展示"},
        {"id": "2", "name": "装备展示", "growth": 38, "description": "稀有装备获取瞬间"},
        {"id": "3", "name": "PVP对决", "growth": 32, "description": "实时PVP高光时刻"},
    ],
    "recommendations": [
        {
            "id": "1", "direction": "Boss战+夸张奖励", "ctr_estimate": 3.2,
            "tags": ["Boss挑战", "高奖励", "视觉冲击"], "description": "开场3秒Boss战高光时刻",
        },
        {
            "id": "2", "direction": "装备收集+稀有掉落", "ctr_estimate": 2.8,
            "tags": ["装备展示", "稀有掉落", "收集欲"], "description": "展示稀有装备获取过程",
        },
    ],
}


class MockChatRepository:
    """对话 Mock 实现 — 内存存储 + 模拟延迟"""

    def __init__(self):
        self._sessions: dict[str, dict] = {}

    async def create_session(self, user_id: str, game_info: dict) -> str:
        settings = get_settings()
        await asyncio.sleep(settings.DEMO_DELAY_ANALYSIS)
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "game_info": game_info,
            "messages": [],
            "analysis": MOCK_ANALYSIS,
        }
        return session_id

    async def add_message(self, session_id: str, role: str, content: str, metadata: dict | None = None) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["messages"].append(
                {"role": role, "content": content, "metadata": metadata}
            )

    async def get_session(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)

    async def list_sessions(self, user_id: str, limit: int = 20) -> list[dict]:
        return [s for s in self._sessions.values() if s["user_id"] == user_id][:limit]
