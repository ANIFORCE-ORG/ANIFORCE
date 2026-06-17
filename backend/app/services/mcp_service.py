"""
MCP Service - 业务工具注册与路由

核心职责：
- 将后端 API 封装为 MCP 工具
- 提供统一的工具调用接口
- 处理权限验证（JWT Token）
- 返回 MCP 标准格式响应
"""

import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException

from app.repositories.protocols import (
    ProjectRepository,
    CampaignRepository,
    MaterialRepository,
    PlatformAuthRepository,
)

logger = logging.getLogger(__name__)


class MCPService:
    """MCP 工具服务"""

    def __init__(
        self,
        project_repo: ProjectRepository,
        campaign_repo: CampaignRepository,
        material_repo: MaterialRepository,
        platform_auth_repo: PlatformAuthRepository,
    ):
        self.project_repo = project_repo
        self.campaign_repo = campaign_repo
        self.material_repo = material_repo
        self.platform_auth_repo = platform_auth_repo

        # 注册所有工具
        self._tools = self._register_tools()

    def _register_tools(self) -> Dict[str, dict]:
        """注册所有 MCP 工具"""
        return {
            # 项目管理
            "list_projects": {
                "description": "List user's projects with optional status filter",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by project status (optional)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of projects",
                            "default": 20,
                        },
                    },
                },
                "handler": self.list_projects,
            },
            "get_project": {
                "description": "Get project details by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID",
                        },
                    },
                    "required": ["project_id"],
                },
                "handler": self.get_project,
            },
            "create_project": {
                "description": "Create a new project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Project name"},
                        "total_budget": {
                            "type": "number",
                            "description": "Total budget",
                        },
                        "description": {
                            "type": "string",
                            "description": "Project description (optional)",
                        },
                        "game_type": {
                            "type": "string",
                            "description": "Game type (optional)",
                        },
                        "target_market": {
                            "type": "string",
                            "description": "Target market (optional)",
                        },
                    },
                    "required": ["name", "total_budget"],
                },
                "handler": self.create_project,
            },
            # 广告计划
            "list_campaigns": {
                "description": "List campaigns for a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of campaigns",
                            "default": 20,
                        },
                    },
                    "required": ["project_id"],
                },
                "handler": self.list_campaigns,
            },
            "get_campaign": {
                "description": "Get campaign details by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "Campaign ID",
                        },
                    },
                    "required": ["campaign_id"],
                },
                "handler": self.get_campaign,
            },
            "create_campaign": {
                "description": "Create a new ad campaign under a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "name": {"type": "string", "description": "Campaign name"},
                        "platform": {"type": "string", "description": "Ad platform: meta/google/tiktok"},
                        "budget": {"type": "number", "description": "Total budget"},
                        "status": {"type": "string", "description": "Initial status (optional): draft/active/paused", "default": "draft"},
                    },
                    "required": ["project_id", "name", "platform", "budget"],
                },
                "handler": self.create_campaign,
            },
            "update_campaign_budget": {
                "description": "Update a campaign's total budget",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string", "description": "Campaign ID"},
                        "budget": {"type": "number", "description": "New total budget"},
                    },
                    "required": ["campaign_id", "budget"],
                },
                "handler": self.update_campaign_budget,
            },
            # 素材管理
            "list_materials": {
                "description": "List materials for a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID",
                        },
                        "material_type": {
                            "type": "string",
                            "description": "Filter by material type (optional)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of materials",
                            "default": 20,
                        },
                    },
                    "required": ["project_id"],
                },
                "handler": self.list_materials,
            },
            # 平台授权
            "list_platform_auths": {
                "description": "List user's platform authorizations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "platform": {
                            "type": "string",
                            "description": "Filter by platform (optional)",
                        },
                    },
                },
                "handler": self.list_platform_auths,
            },
        }

    def list_tools(self) -> list[dict]:
        """列出所有可用工具（MCP tools/list 协议）"""
        tools = []
        for name, tool in self._tools.items():
            tools.append(
                {
                    "name": name,
                    "description": tool["description"],
                    "inputSchema": tool["inputSchema"],
                }
            )
        return tools

    async def call_tool(
        self, tool_name: str, arguments: dict, user_id: str
    ) -> dict:
        """
        调用工具（MCP tools/call 协议）

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            user_id: 用户 ID（从 JWT 提取）

        Returns:
            MCP 标准响应
        """
        tool = self._tools.get(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

        try:
            # 调用处理器
            handler = tool["handler"]
            result = await handler(user_id=user_id, **arguments)

            # 返回 MCP 标准格式
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result),
                    }
                ]
            }

        except Exception as e:
            logger.error(f"Tool call error: tool={tool_name}, error={e}", exc_info=True)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}",
                    }
                ],
                "isError": True,
            }

    # ========== 工具实现 ==========

    async def list_projects(
        self, user_id: str, status: Optional[str] = None, limit: int = 20
    ) -> dict:
        """列出用户项目"""
        projects = await self.project_repo.list_by_user(
            user_id=user_id, status=status, limit=limit
        )
        return {"projects": projects}

    async def get_project(self, user_id: str, project_id: str) -> dict:
        """获取项目详情"""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 权限验证
        if project["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Permission denied")

        return project

    async def create_project(
        self,
        user_id: str,
        name: str,
        total_budget: float,
        description: Optional[str] = None,
        game_type: Optional[str] = None,
        target_market: Optional[str] = None,
    ) -> dict:
        """创建项目"""
        project = await self.project_repo.create(
            user_id=user_id,
            name=name,
            total_budget=total_budget,
            description=description,
            game_type=game_type,
            target_market=target_market,
        )
        await self.project_repo.session.commit()
        return project

    async def list_campaigns(
        self, user_id: str, project_id: str, limit: int = 20
    ) -> dict:
        """列出广告计划"""
        # 先验证项目权限
        await self.get_project(user_id, project_id)

        campaigns = await self.campaign_repo.list_by_project(
            project_id=project_id, limit=limit
        )
        return {"campaigns": campaigns}

    async def get_campaign(self, user_id: str, campaign_id: str) -> dict:
        """获取广告计划详情"""
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # 验证项目权限
        await self.get_project(user_id, campaign["project_id"])

        return campaign

    async def create_campaign(
        self,
        user_id: str,
        project_id: str,
        name: str,
        platform: str,
        budget: float,
        status: Optional[str] = "draft",
    ) -> dict:
        """创建广告计划"""
        # 验证项目权限
        await self.get_project(user_id, project_id)

        campaign = await self.campaign_repo.create(
            project_id=project_id,
            name=name,
            platform=platform,
            budget=budget,
            status=status,
        )
        await self.campaign_repo.session.commit()
        return campaign

    async def update_campaign_budget(
        self, user_id: str, campaign_id: str, budget: float
    ) -> dict:
        """更新广告计划预算"""
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # 验证项目权限
        await self.get_project(user_id, campaign["project_id"])

        await self.campaign_repo.update_budget(campaign_id, budget)
        await self.campaign_repo.session.commit()

        updated = await self.campaign_repo.get_by_id(campaign_id)
        return updated

    async def list_materials(
        self,
        user_id: str,
        project_id: str,
        material_type: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """列出素材"""
        # 先验证项目权限
        await self.get_project(user_id, project_id)

        materials = await self.material_repo.list_by_project(
            project_id=project_id, material_type=material_type, limit=limit
        )
        return {"materials": materials}

    async def list_platform_auths(
        self, user_id: str, platform: Optional[str] = None
    ) -> dict:
        """列出平台授权"""
        auths = await self.platform_auth_repo.list_by_user(
            user_id=user_id, platform=platform
        )
        return {"platform_auths": auths}
