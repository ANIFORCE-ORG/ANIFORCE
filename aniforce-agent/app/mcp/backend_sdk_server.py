"""
Backend API 适配为 SDK MCP Server

核心功能：
- 将 Backend REST API 包装为 Claude SDK MCP Server
- 每个工具调用 Backend HTTP 端点
- JWT Token 透传到 Backend
- 返回符合 MCP 协议的响应

设计原则：
- 薄适配层，不包含业务逻辑
- 工具定义与 Backend 保持一致
- 错误处理和日志记录

并发安全（P0）：
- 每次 query 创建独立的 MCP server 实例
- task_id / user_id / jwt_token 通过闭包注入到工具函数
- 不同请求的工具函数是不同实例，互不影响，无需锁
"""

import httpx
from typing import Any, Dict, Optional
from loguru import logger

from claude_agent_sdk import tool, create_sdk_mcp_server
from app.config.settings import get_settings


def _make_backend_tool_factory(jwt_token: str, user_id: str, task_id: str):
    """
    生成绑定本次请求上下文（jwt/user/task）的 backend 工具集

    每次 query 调用一次，返回的工具函数通过闭包捕获本次请求的
    jwt_token/user_id/task_id，保证多用户并发隔离。

    Args:
        jwt_token: 本次请求用户的 JWT（用于调用 backend）
        user_id: 本次请求用户 ID
        task_id: 本次请求任务 ID

    Returns:
        dict[tool_name, tool_func] 所有 backend 工具函数
    """
    settings = get_settings()

    async def call_backend(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """调用 Backend MCP 工具（闭包捕获 jwt_token）"""
        if not jwt_token:
            return {
                "content": [{"type": "text", "text": "错误：缺少认证信息"}],
                "isError": True,
            }

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "X-Internal-Token": settings.INTERNAL_TOKEN,
            "Content-Type": "application/json",
        }

        url = f"{settings.BACKEND_URL}/api/v1/mcp/tools/{tool_name}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={"name": tool_name, "arguments": args},
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    error_text = response.text
                    logger.error(
                        f"[Task {task_id}] Backend MCP call failed: {tool_name}, "
                        f"status={response.status_code}, error={error_text[:200]}"
                    )
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"后端调用失败 ({response.status_code}): {error_text[:500]}",
                            }
                        ],
                        "isError": True,
                    }

        except Exception as e:
            logger.error(f"[Task {task_id}] Backend MCP call exception: {tool_name}, error={e}")
            return {
                "content": [{"type": "text", "text": f"调用后端服务异常: {str(e)}"}],
                "isError": True,
            }

    # 每个工具用闭包绑定 call_backend，工具名固定
    tools: Dict[str, Any] = {}

    @tool(
        "list_projects",
        "列出用户的广告投放项目列表（支持状态筛选）",
        {
            "status": {"type": "string", "description": "项目状态过滤（可选）：active, paused, completed"},
            "limit": {"type": "integer", "description": "返回项目数量上限", "default": 20},
        },
    )
    async def list_projects(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("list_projects", args)

    @tool(
        "get_project",
        "获取指定项目的详细信息",
        {"project_id": {"type": "string", "description": "项目 ID"}},
    )
    async def get_project(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("get_project", args)

    @tool(
        "create_project",
        "创建新项目（写操作，通常需先调用 confirm_action 获取用户确认）",
        {
            "name": {"type": "string", "description": "项目名称"},
            "total_budget": {"type": "number", "description": "总预算"},
            "description": {"type": "string", "description": "项目描述（可选）"},
        },
    )
    async def create_project(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("create_project", args)

    @tool(
        "list_campaigns",
        "列出指定项目下的广告计划列表",
        {
            "project_id": {"type": "string", "description": "项目 ID"},
            "limit": {"type": "integer", "description": "返回计划数量上限", "default": 20},
        },
    )
    async def list_campaigns(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("list_campaigns", args)

    @tool(
        "get_campaign",
        "获取指定广告计划的详细信息",
        {"campaign_id": {"type": "string", "description": "计划 ID"}},
    )
    async def get_campaign(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("get_campaign", args)

    @tool(
        "create_campaign",
        "在指定项目下创建新的广告计划（写操作，通常需先调用 confirm_action 获取用户确认）",
        {
            "project_id": {"type": "string", "description": "项目 ID"},
            "name": {"type": "string", "description": "计划名称"},
            "platform": {"type": "string", "description": "投放平台：Meta/Google/TikTok（首字母大写）"},
            "budget": {"type": "number", "description": "总预算"},
            "status": {"type": "string", "description": "初始状态（可选）：draft/active/paused", "default": "draft"},
        },
    )
    async def create_campaign(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("create_campaign", args)

    @tool(
        "update_campaign_budget",
        "更新广告计划的总预算（写操作，通常需先调用 confirm_action 获取用户确认）",
        {
            "campaign_id": {"type": "string", "description": "计划 ID"},
            "budget": {"type": "number", "description": "新的总预算"},
        },
    )
    async def update_campaign_budget(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("update_campaign_budget", args)

    @tool(
        "list_materials",
        "列出用户的广告素材列表",
        {
            "project_id": {"type": "string", "description": "项目 ID"},
            "limit": {"type": "integer", "description": "返回素材数量上限", "default": 50},
        },
    )
    async def list_materials(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("list_materials", args)

    @tool(
        "get_material",
        "获取指定素材的详细信息",
        {"material_id": {"type": "string", "description": "素材 ID"}},
    )
    async def get_material(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("get_material", args)

    # ============================================================
    # Mock 工具（用于 Agent 长程任务能力展示）
    # ============================================================

    @tool(
        "create_material",
        "创建广告素材（Mock）",
        {
            "project_id": {"type": "string", "description": "项目 ID"},
            "name": {"type": "string", "description": "素材名称"},
            "material_type": {"type": "string", "description": "素材类型：image/video/text"},
            "content_url": {"type": "string", "description": "素材内容 URL（可选）"},
        },
    )
    async def create_material(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("create_material", args)

    @tool(
        "generate_material_ai",
        "AI 生成广告素材（Mock：返回占位 URL）",
        {
            "project_id": {"type": "string", "description": "项目 ID"},
            "prompt": {"type": "string", "description": "生成提示词"},
            "material_type": {"type": "string", "description": "生成类型：image/video/text", "default": "image"},
            "count": {"type": "integer", "description": "生成数量", "default": 1},
        },
    )
    async def generate_material_ai(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("generate_material_ai", args)

    @tool(
        "update_campaign_status",
        "更新广告计划状态（启动/暂停/结束）",
        {
            "campaign_id": {"type": "string", "description": "计划 ID"},
            "status": {"type": "string", "description": "目标状态：draft/active/paused/completed"},
        },
    )
    async def update_campaign_status(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("update_campaign_status", args)

    @tool(
        "get_campaign_performance",
        "获取广告计划投放数据（Mock：生成模拟数据）",
        {
            "campaign_id": {"type": "string", "description": "计划 ID"},
            "date_range": {"type": "string", "description": "时间范围：last_7d/last_30d/custom", "default": "last_7d"},
        },
    )
    async def get_campaign_performance(args: Dict[str, Any]) -> Dict[str, Any]:
        return await call_backend("get_campaign_performance", args)

    return [
        list_projects,
        get_project,
        create_project,
        list_campaigns,
        get_campaign,
        create_campaign,
        update_campaign_budget,
        list_materials,
        get_material,
        # Mock 工具（长程任务能力展示）
        create_material,
        generate_material_ai,
        update_campaign_status,
        get_campaign_performance,
    ]


def get_backend_mcp_config(jwt_token: str, user_id: str, task_id: str) -> dict:
    """
    获取 Backend MCP 配置（每次 query 调用，闭包绑定本次请求上下文）

    Args:
        jwt_token: 本次请求用户的 JWT
        user_id: 本次请求用户 ID
        task_id: 本次请求任务 ID

    Returns:
        MCP Server 配置字典: {"backend": <server_instance>}

    并发安全：
        每次调用创建独立的 server 和工具函数实例，
        jwt/user/task 通过闭包注入，多用户并发完全隔离。
    """
    tools = _make_backend_tool_factory(jwt_token, user_id, task_id)
    server = create_sdk_mcp_server(name="backend", version="1.0.0", tools=tools)
    return {"backend": server}
