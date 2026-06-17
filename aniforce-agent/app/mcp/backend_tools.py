"""
MCP 工具 - Backend API 调用

连接 ANIFORCE Backend API，提供广告投放数据查询能力。

核心功能：
- list_campaigns: 列出用户的广告投放计划
- get_campaign: 获取广告投放详情
- list_projects: 列出用户的项目

设计原则：
- 通过环境变量获取 JWT Token（由 AgentRuntime 注入）
- 通过 HTTP 调用 Backend API
- 自动处理认证和错误
"""

import os
import json
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class BackendAPITools:
    """Backend API 调用工具集"""

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化

        Args:
            base_url: Backend API 基础 URL，默认从环境变量读取
        """
        self.base_url = base_url or os.environ.get(
            "ANIFORCE_BACKEND_URL", "http://localhost:3000"
        )

    def _get_jwt_token(self) -> str:
        """从环境变量获取 JWT Token"""
        token = os.environ.get("ANIFORCE_JWT_TOKEN")
        if not token:
            raise ValueError("ANIFORCE_JWT_TOKEN not set in environment")
        return token

    def _make_request(
        self, method: str, path: str, params: Optional[dict] = None, json_data: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        发起 HTTP 请求

        Args:
            method: HTTP 方法
            path: API 路径
            params: 查询参数
            json_data: JSON 请求体

        Returns:
            响应 JSON
        """
        token = self._get_jwt_token()
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = httpx.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Backend API error: {e.response.status_code} {e.response.text}")
            return {"error": f"API error: {e.response.status_code}", "detail": e.response.text}
        except Exception as e:
            logger.error(f"Backend API request failed: {e}", exc_info=True)
            return {"error": str(e)}

    async def list_campaigns(
        self, project_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50
    ) -> str:
        """
        列出用户的广告投放计划

        Args:
            project_id: 项目 ID（可选，为空则返回所有项目的广告）
            status: 状态过滤（可选：draft, active, paused, completed）
            limit: 最多返回数量

        Returns:
            JSON 格式的广告投放列表
        """
        params = {"limit": limit}
        if project_id:
            params["project_id"] = project_id
        if status:
            params["status"] = status

        result = self._make_request("GET", "/api/v1/campaigns", params=params)
        return json.dumps(result, ensure_ascii=False)

    async def get_campaign(self, campaign_id: str) -> str:
        """
        获取广告投放详情

        Args:
            campaign_id: 广告投放 ID

        Returns:
            JSON 格式的广告投放详情
        """
        result = self._make_request("GET", f"/api/v1/campaigns/{campaign_id}")
        return json.dumps(result, ensure_ascii=False)

    async def list_projects(self, limit: int = 50) -> str:
        """
        列出用户的项目

        Args:
            limit: 最多返回数量

        Returns:
            JSON 格式的项目列表
        """
        params = {"limit": limit}
        result = self._make_request("GET", "/api/v1/projects", params=params)
        return json.dumps(result, ensure_ascii=False)

    async def get_project(self, project_id: str) -> str:
        """
        获取项目详情

        Args:
            project_id: 项目 ID

        Returns:
            JSON 格式的项目详情
        """
        result = self._make_request("GET", f"/api/v1/projects/{project_id}")
        return json.dumps(result, ensure_ascii=False)


# 工具实例（由 AgentRuntime 初始化时创建）
_backend_tools: Optional[BackendAPITools] = None


def get_backend_tools() -> BackendAPITools:
    """获取 Backend API 工具实例"""
    global _backend_tools
    if _backend_tools is None:
        _backend_tools = BackendAPITools()
    return _backend_tools
