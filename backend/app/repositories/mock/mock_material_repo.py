import asyncio
import uuid
from app.config.settings import get_settings

MOCK_MATERIALS = [
    {
        "id": "1", "type": "a_segment", "url": "", "thumbnail_url": "",
        "duration": 5, "ctr": 3.2, "tags": ["Boss战", "高光"],
    },
    {
        "id": "2", "type": "b_segment", "url": "", "thumbnail_url": "",
        "duration": 10, "ctr": 2.8, "tags": ["装备", "稀有"],
    },
    {
        "id": "3", "type": "c_segment", "url": "", "thumbnail_url": "",
        "duration": 5, "ctr": 2.5, "tags": ["CTA", "下载"],
    },
]


class MockMaterialRepository:
    def __init__(self):
        self._tasks: dict[str, dict] = {}

    async def create_task(self, session_id: str, direction: str, user_id: str) -> str:
        settings = get_settings()
        await asyncio.sleep(settings.DEMO_DELAY_MATERIAL)
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {
            "task_id": task_id, "session_id": session_id,
            "direction": direction, "user_id": user_id,
            "materials": MOCK_MATERIALS, "status": "completed",
        }
        return task_id

    async def get_task(self, task_id: str) -> dict | None:
        return self._tasks.get(task_id)

    async def update_task(self, task_id: str, materials: list[dict], status: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["materials"] = materials
            self._tasks[task_id]["status"] = status
