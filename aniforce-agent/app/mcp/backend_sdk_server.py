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
"""

import httpx
from typing import Any, Dict
from loguru import logger

from claude_agent_sdk import tool, create_sdk_mcp_server
from app.config.settings import get_settings
from app.core.context import get_jwt_token


settings = get_settings()


async def call_backend_mcp_tool(
    tool_name: str,
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    调用 Backend MCP 工具的通用函数
    
    Args:
        tool_name: 工具名称
        args: 工具参数
    
    Returns:
        MCP 标准响应格式
    """
    jwt_token = get_jwt_token()
    
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
                json={"name": tool_name, "arguments": args},  # 符合 Backend ToolCallRequest 格式
                headers=headers,
                timeout=30.0,
            )
            
            if response.status_code == 200:
                result = response.json()
                # Backend 返回格式: {"content": [...]}
                return result
            else:
                error_text = response.text
                logger.error(f"Backend MCP call failed: {tool_name}, status={response.status_code}, error={error_text}")
                return {
                    "content": [{"type": "text", "text": f"后端调用失败 ({response.status_code}): {error_text}"}],
                    "isError": True,
                }
    
    except Exception as e:
        logger.error(f"Backend MCP call exception: {tool_name}, error={e}")
        return {
            "content": [{"type": "text", "text": f"调用后端服务异常: {str(e)}"}],
            "isError": True,
        }


# ============================================================
# 项目管理工具
# ============================================================

@tool(
    "list_projects",
    "列出用户的广告投放项目列表（支持状态筛选）",
    {
        "status": {"type": "string", "description": "项目状态过滤（可选）：active, paused, completed"},
        "limit": {"type": "integer", "description": "返回项目数量上限", "default": 20},
    }
)
async def list_projects(args: Dict[str, Any]) -> Dict[str, Any]:
    """列出用户的广告项目"""
    return await call_backend_mcp_tool("list_projects", args)


@tool(
    "get_project",
    "获取指定项目的详细信息",
    {
        "project_id": {"type": "string", "description": "项目 ID"},
    }
)
async def get_project(args: Dict[str, Any]) -> Dict[str, Any]:
    """获取项目详情"""
    return await call_backend_mcp_tool("get_project", args)


# ============================================================
# 广告计划工具
# ============================================================

@tool(
    "list_campaigns",
    "列出指定项目下的广告计划列表",
    {
        "project_id": {"type": "string", "description": "项目 ID"},
        "status": {"type": "string", "description": "计划状态过滤（可选）：active, paused, completed"},
        "limit": {"type": "integer", "description": "返回计划数量上限", "default": 20},
    }
)
async def list_campaigns(args: Dict[str, Any]) -> Dict[str, Any]:
    """列出广告计划"""
    return await call_backend_mcp_tool("list_campaigns", args)


@tool(
    "get_campaign",
    "获取指定广告计划的详细信息",
    {
        "campaign_id": {"type": "string", "description": "计划 ID"},
    }
)
async def get_campaign(args: Dict[str, Any]) -> Dict[str, Any]:
    """获取广告计划详情"""
    return await call_backend_mcp_tool("get_campaign", args)


@tool(
    "create_campaign",
    "在指定项目下创建新的广告计划（写操作，通常需先调用 confirm_action 获取用户确认）",
    {
        "project_id": {"type": "string", "description": "项目 ID"},
        "name": {"type": "string", "description": "计划名称"},
        "platform": {"type": "string", "description": "投放平台：meta/google/tiktok"},
        "budget": {"type": "number", "description": "总预算"},
        "status": {"type": "string", "description": "初始状态（可选）：draft/active/paused", "default": "draft"},
    }
)
async def create_campaign(args: Dict[str, Any]) -> Dict[str, Any]:
    """创建广告计划"""
    return await call_backend_mcp_tool("create_campaign", args)


@tool(
    "update_campaign_budget",
    "更新广告计划的总预算（写操作，通常需先调用 confirm_action 获取用户确认）",
    {
        "campaign_id": {"type": "string", "description": "计划 ID"},
        "budget": {"type": "number", "description": "新的总预算"},
    }
)
async def update_campaign_budget(args: Dict[str, Any]) -> Dict[str, Any]:
    """更新广告计划预算"""
    return await call_backend_mcp_tool("update_campaign_budget", args)


# ============================================================
# 素材管理工具
# ============================================================

@tool(
    "list_materials",
    "列出用户的广告素材列表",
    {
        "type": {"type": "string", "description": "素材类型过滤（可选）：image, video, text"},
        "limit": {"type": "integer", "description": "返回素材数量上限", "default": 50},
    }
)
async def list_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """列出广告素材"""
    return await call_backend_mcp_tool("list_materials", args)


@tool(
    "get_material",
    "获取指定素材的详细信息",
    {
        "material_id": {"type": "string", "description": "素材 ID"},
    }
)
async def get_material(args: Dict[str, Any]) -> Dict[str, Any]:
    """获取素材详情"""
    return await call_backend_mcp_tool("get_material", args)


# ============================================================
# 创建 Backend MCP Server
# ============================================================

def create_backend_sdk_mcp_server():
    """
    创建 Backend SDK MCP Server
    
    Returns:
        SDK MCP Server 实例
    """
    return create_sdk_mcp_server(
        name="backend",
        version="1.0.0",
        tools=[
            list_projects,
            get_project,
            list_campaigns,
            get_campaign,
            create_campaign,
            update_campaign_budget,
            list_materials,
            get_material,
        ],
    )


def get_backend_mcp_config():
    """
    获取 Backend MCP 配置（用于 Runtime）
    
    Returns:
        MCP Server 配置字典: {"backend": <server_instance>}
    """
    server = create_backend_sdk_mcp_server()
    return {"backend": server}
