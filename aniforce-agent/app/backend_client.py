"""Backend REST API 客户端

agent-service 内部的 MCP 工具通过这个客户端调用 backend REST API。
JWT token 从 MCP context 透传，保证用户身份隔离。
"""

import httpx
from loguru import logger

from app.config.settings import settings


class BackendClient:
    """Backend REST API 客户端"""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.BACKEND_BASE_URL).rstrip("/")

    async def _request(
        self,
        method: str,
        path: str,
        token: str | None = None,
        json: dict | None = None,
        params: dict | None = None,
        timeout: float = 30.0,
        extra_headers: dict | None = None,
    ) -> dict:
        """发起 backend 请求"""
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if extra_headers:
            headers.update(extra_headers)

        logger.debug(f"[BACKEND] {method} {url}")

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
            )

        if resp.status_code >= 400:
            logger.warning(f"[BACKEND] {method} {url} → {resp.status_code}: {resp.text[:200]}")
            return {"error": True, "status": resp.status_code, "message": resp.text[:500]}

        try:
            return resp.json()
        except Exception:
            return {"raw": resp.text[:1000]}

    # ---- Projects ----

    async def list_projects(self, token: str, limit: int = 20) -> dict:
        return await self._request("GET", "/api/v1/projects", token=token, params={"limit": limit})

    async def get_project(self, token: str, project_id: str) -> dict:
        return await self._request("GET", f"/api/v1/projects/{project_id}", token=token)

    async def create_project(self, token: str, data: dict, extra_headers: dict | None = None) -> dict:
        return await self._request("POST", "/api/v1/projects", token=token, json=data, extra_headers=extra_headers)

    async def update_project(self, token: str, project_id: str, data: dict, extra_headers: dict | None = None) -> dict:
        return await self._request("PUT", f"/api/v1/projects/{project_id}", token=token, json=data, extra_headers=extra_headers)

    async def delete_project(self, token: str, project_id: str, extra_headers: dict | None = None) -> dict:
        return await self._request("DELETE", f"/api/v1/projects/{project_id}", token=token, extra_headers=extra_headers)

    # ---- Campaigns ----

    async def list_campaigns(self, token: str, project_id: str | None = None, status: str | None = None, limit: int = 20) -> dict:
        params = {"limit": limit}
        if project_id:
            params["project_id"] = project_id
        if status:
            params["status"] = status
        return await self._request("GET", "/api/v1/campaigns", token=token, params=params)

    async def get_campaign(self, token: str, campaign_id: str) -> dict:
        return await self._request("GET", f"/api/v1/campaigns/{campaign_id}", token=token)

    async def create_campaign(self, token: str, data: dict, extra_headers: dict | None = None) -> dict:
        return await self._request("POST", "/api/v1/campaigns", token=token, json=data, extra_headers=extra_headers)

    async def update_campaign(self, token: str, campaign_id: str, data: dict, extra_headers: dict | None = None) -> dict:
        return await self._request("PUT", f"/api/v1/campaigns/{campaign_id}", token=token, json=data, extra_headers=extra_headers)

    async def update_campaign_status(self, token: str, campaign_id: str, status: str, extra_headers: dict | None = None) -> dict:
        return await self._request("PUT", f"/api/v1/campaigns/{campaign_id}/status", token=token, json={"status": status}, extra_headers=extra_headers)

    async def get_campaign_materials(self, token: str, campaign_id: str) -> dict:
        return await self._request("GET", f"/api/v1/campaigns/{campaign_id}/materials", token=token)

    async def add_material_to_campaign(self, token: str, campaign_id: str, material_id: str, extra_headers: dict | None = None) -> dict:
        return await self._request("POST", f"/api/v1/campaigns/{campaign_id}/materials/{material_id}", token=token, extra_headers=extra_headers)

    async def remove_material_from_campaign(self, token: str, campaign_id: str, material_id: str, extra_headers: dict | None = None) -> dict:
        return await self._request("DELETE", f"/api/v1/campaigns/{campaign_id}/materials/{material_id}", token=token, extra_headers=extra_headers)

    async def delete_campaign(self, token: str, campaign_id: str, extra_headers: dict | None = None) -> dict:
        return await self._request("DELETE", f"/api/v1/campaigns/{campaign_id}", token=token, extra_headers=extra_headers)

    # ---- Materials ----

    async def list_materials(self, token: str, project_id: str | None = None, campaign_id: str | None = None, type: str | None = None, limit: int = 20) -> dict:
        params = {"limit": limit}
        if project_id:
            params["project_id"] = project_id
        if campaign_id:
            params["campaign_id"] = campaign_id
        if type:
            params["type"] = type
        return await self._request("GET", "/api/v1/materials", token=token, params=params)

    async def get_material(self, token: str, material_id: str) -> dict:
        return await self._request("GET", f"/api/v1/materials/{material_id}", token=token)

    async def update_material(self, token: str, material_id: str, data: dict, extra_headers: dict | None = None) -> dict:
        return await self._request("PATCH", f"/api/v1/materials/{material_id}", token=token, json=data, extra_headers=extra_headers)

    async def create_material(self, token: str, data: dict, extra_headers: dict | None = None) -> dict:
        return await self._request("POST", "/api/v1/materials", token=token, json=data, extra_headers=extra_headers)

    async def get_material_image(self, token: str, material_id: str, thumbnail: bool = False) -> dict:
        return await self._request("GET", f"/api/v1/materials/{material_id}/image", token=token, params={"thumbnail": thumbnail})

    async def list_available_images(self, token: str) -> dict:
        return await self._request("GET", "/api/v1/materials/images/list", token=token)

    async def add_material_to_project(self, token: str, material_id: str, project_id: str, extra_headers: dict | None = None) -> dict:
        return await self._request("POST", f"/api/v1/materials/{material_id}/projects/{project_id}", token=token, extra_headers=extra_headers)

    async def remove_material_from_project(self, token: str, material_id: str, project_id: str, extra_headers: dict | None = None) -> dict:
        return await self._request("DELETE", f"/api/v1/materials/{material_id}/projects/{project_id}", token=token, extra_headers=extra_headers)

    async def delete_material(self, token: str, material_id: str, extra_headers: dict | None = None) -> dict:
        return await self._request("DELETE", f"/api/v1/materials/{material_id}", token=token, extra_headers=extra_headers)


# 全局单例
backend_client = BackendClient()
