"""
MCP Service - 业务工具注册与路由

核心职责：
- 将后端 API 封装为 MCP 工具
- 提供统一的工具调用接口
- 处理权限验证（JWT Token）
- 返回 MCP 标准格式响应
"""

import logging
import time
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
            # ============================================================
            # Mock 工具（用于 Agent 长程任务能力展示，数据非真实）
            # ============================================================
            "create_material": {
                "description": "创建广告素材（Mock）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "项目 ID"},
                        "name": {"type": "string", "description": "素材名称"},
                        "material_type": {
                            "type": "string",
                            "description": "素材类型：image/video/text",
                        },
                        "content_url": {
                            "type": "string",
                            "description": "素材内容 URL（可选）",
                        },
                    },
                    "required": ["project_id", "name", "material_type"],
                },
                "handler": self.mock_create_material,
            },
            "generate_material_ai": {
                "description": "AI 生成广告素材（Mock：返回占位 URL）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "项目 ID"},
                        "prompt": {"type": "string", "description": "生成提示词"},
                        "material_type": {
                            "type": "string",
                            "description": "生成类型：image/video/text",
                            "default": "image",
                        },
                        "count": {
                            "type": "integer",
                            "description": "生成数量",
                            "default": 1,
                        },
                    },
                    "required": ["project_id", "prompt"],
                },
                "handler": self.mock_generate_material_ai,
            },
            "update_campaign_status": {
                "description": "更新广告计划状态（启动/暂停/结束）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string", "description": "计划 ID"},
                        "status": {
                            "type": "string",
                            "description": "目标状态：draft/active/paused/completed",
                        },
                    },
                    "required": ["campaign_id", "status"],
                },
                "handler": self.mock_update_campaign_status,
            },
            "get_campaign_performance": {
                "description": "获取广告计划投放数据（Mock：生成模拟数据）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string", "description": "计划 ID"},
                        "date_range": {
                            "type": "string",
                            "description": "时间范围：last_7d/last_30d/custom",
                            "default": "last_7d",
                        },
                    },
                    "required": ["campaign_id"],
                },
                "handler": self.mock_get_campaign_performance,
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

        start_time = time.monotonic()
        logger.info(
            "[MCP_ACTION_START] tool=%s user_id=%s args_keys=%s",
            tool_name,
            user_id,
            sorted(arguments.keys()),
        )

        try:
            # 调用处理器
            handler = tool["handler"]
            result = await handler(user_id=user_id, **arguments)

            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.info(
                "[MCP_ACTION_DONE] tool=%s user_id=%s duration_ms=%s result_keys=%s",
                tool_name,
                user_id,
                duration_ms,
                sorted(result.keys()) if isinstance(result, dict) else [],
            )

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
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(
                "[MCP_ACTION_ERROR] tool=%s user_id=%s duration_ms=%s error=%s",
                tool_name,
                user_id,
                duration_ms,
                e,
                exc_info=True,
            )
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

    # ============================================================
    # Mock 工具实现（用于 Agent 长程任务能力展示）
    # ============================================================

    async def mock_create_material(
        self,
        user_id: str,
        project_id: str,
        name: str,
        material_type: str,
        content_url: Optional[str] = None,
    ) -> dict:
        """
        Mock: 创建广告素材

        注意：此工具为 Mock 实现，返回模拟数据用于 Agent 能力展示
        """
        # 验证项目权限
        await self.get_project(user_id, project_id)

        import uuid

        material_id = str(uuid.uuid4())
        mock_url = content_url or f"https://mock-cdn.aniforce.com/materials/{material_id}.jpg"

        material = {
            "id": material_id,
            "project_id": project_id,
            "name": name,
            "type": material_type,
            "url": mock_url,
            "status": "active",
            "created_at": "2026-06-17T12:00:00Z",
            "note": "⚠️ Mock 数据，非真实素材",
        }

        logger.info(f"[Mock] Created material: {material_id} for project {project_id}")
        return material

    async def mock_generate_material_ai(
        self,
        user_id: str,
        project_id: str,
        prompt: str,
        material_type: str = "image",
        count: int = 1,
    ) -> dict:
        """
        Mock: AI 生成广告素材

        注意：此工具为 Mock 实现，返回模拟 AI 生成结果
        """
        # 验证项目权限
        await self.get_project(user_id, project_id)

        import uuid

        # Agent/LLM 有时会把 JSON integer 参数传成字符串，Mock 工具兼容数字字符串
        try:
            count_int = int(count)
        except (TypeError, ValueError):
            count_int = 1
        count_int = max(1, min(count_int, 10))

        materials = []
        for i in range(count_int):
            material_id = str(uuid.uuid4())
            mock_url = f"https://mock-cdn.aniforce.com/ai-generated/{material_id}.{material_type[:3]}"
            materials.append(
                {
                    "id": material_id,
                    "project_id": project_id,
                    "name": f"AI_{material_type}_{i+1}",
                    "type": material_type,
                    "url": mock_url,
                    "prompt": prompt,
                    "status": "active",
                    "created_at": "2026-06-17T12:00:00Z",
                    "note": "⚠️ Mock AI 生成，非真实素材",
                }
            )

        logger.info(
            f"[Mock] AI generated {count_int} materials for project {project_id}: prompt='{prompt[:50]}...'"
        )
        return {"materials": materials, "count": count_int}

    async def mock_update_campaign_status(
        self, user_id: str, campaign_id: str, status: str
    ) -> dict:
        """
        Mock: 更新广告计划状态

        注意：实际应该调用广告平台 API，此处为 Mock 实现
        """
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # 验证项目权限
        await self.get_project(user_id, campaign["project_id"])

        # Mock: 真实更新本地 DB 状态，但不调用外部广告平台 API
        status_map = {
            "active": "running",  # 前端/业务话术兼容：active 表示已开始投放
            "running": "running",
            "draft": "draft",
            "paused": "paused",
            "completed": "completed",
        }
        normalized_status = status_map.get(str(status).lower())
        if not normalized_status:
            raise HTTPException(status_code=400, detail=f"Invalid campaign status: {status}")

        await self.campaign_repo.update_status(campaign_id, normalized_status)
        await self.campaign_repo.session.commit()
        updated = await self.campaign_repo.get_by_id(campaign_id)

        logger.info(
            f"[Mock] Update campaign {campaign_id} status: {campaign['status']} -> {normalized_status}"
        )

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign["name"],
            "old_status": campaign["status"],
            "new_status": normalized_status,
            "updated_at": updated.get("updated_at") if updated else "2026-06-17T12:00:00Z",
            "note": "⚠️ Mock 更新：已更新本地 DB，未真实调用广告平台 API",
        }

    async def mock_get_campaign_performance(
        self, user_id: str, campaign_id: str, date_range: str = "last_7d"
    ) -> dict:
        """
        Mock: 获取广告计划投放数据

        注意：此工具返回模拟数据，用于 Agent 能力展示
        真实场景应该调用广告平台 API 获取真实数据
        """
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # 验证项目权限
        await self.get_project(user_id, campaign["project_id"])

        # Mock 数据：用 campaign_id 哈希生成稳定的假数据
        import hashlib

        seed = int(hashlib.md5(campaign_id.encode()).hexdigest()[:8], 16)

        # 根据种子生成模拟数据（同一 campaign_id 每次返回相同数据）
        impressions = (seed % 100000) + 50000  # 5万-15万展示
        clicks = impressions // ((seed % 30) + 20)  # CTR 2-5%
        spent = campaign["budget"] * ((seed % 80) + 20) / 100  # 花了 20-100%
        conversions = clicks // ((seed % 20) + 10)  # CVR 5-10%

        ctr = round(clicks / impressions * 100, 2) if impressions > 0 else 0
        cpc = round(spent / clicks, 2) if clicks > 0 else 0
        cpa = round(spent / conversions, 2) if conversions > 0 else 0
        # 假设每个转化价值 100 元
        roi = (
            round((conversions * 100 - spent) / spent * 100, 2) if spent > 0 else 0
        )

        logger.info(
            f"[Mock] Get campaign performance: {campaign_id}, impressions={impressions}, roi={roi}%"
        )

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign["name"],
            "platform": campaign["platform"],
            "date_range": date_range,
            "metrics": {
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "spent": round(spent, 2),
                "ctr": ctr,  # Click-Through Rate
                "cpc": cpc,  # Cost Per Click
                "cpa": cpa,  # Cost Per Acquisition
                "roi": roi,  # Return on Investment (%)
            },
            "note": "⚠️ Mock 数据，用于 Agent 能力展示，非真实投放结果",
        }
