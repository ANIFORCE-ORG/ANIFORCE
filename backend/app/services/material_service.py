from app.repositories.protocols import MaterialRepository


class MaterialService:
    """素材业务逻辑"""

    def __init__(self, material_repo: MaterialRepository):
        self._repo = material_repo

    async def generate(self, session_id: str, direction: str, user_id: str) -> dict:
        task_id = await self._repo.create_task(session_id, direction, user_id)
        task = await self._repo.get_task(task_id)
        return {
            "task_id": task_id,
            "materials": task.get("materials", []) if task else [],
        }

    async def get_task(self, task_id: str) -> dict:
        task = await self._repo.get_task(task_id)
        if not task:
            return {"materials": [], "status": "not_found"}
        return {"materials": task.get("materials", []), "status": task.get("status", "unknown")}
