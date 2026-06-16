"""
HTTP MCP 桥接

核心功能：
- 创建 HTTP MCP Server 配置，指向后端服务
- 透传 JWT Token 进行鉴权
- 支持调用后端业务工具（项目管理、广告计划等）

设计原则：
- 不在 Agent 服务侧实现业务逻辑
- 通过 HTTP MCP 协议调用后端 API
- JWT Token 通过 Header 透传
- Internal Token 用于服务间认证
"""

from typing import Optional
from app.config.settings import settings


def create_http_mcp_config(
    backend_url: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> dict:
    """
    创建 HTTP MCP Server 配置（调用后端服务）

    Args:
        backend_url: 后端服务 URL（默认使用配置）
        auth_token: JWT Token（用户鉴权）

    Returns:
        MCP Server 配置字典
    """
    url = backend_url or settings.BACKEND_URL

    headers = {
        "X-Internal-Token": settings.INTERNAL_TOKEN,
    }

    # 如果提供了 JWT Token，添加到请求头
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    return {
        "command": "http",
        "args": [url],
        "env": {
            "HTTP_MCP_HEADERS": "|".join([f"{k}:{v}" for k, v in headers.items()]),
        },
    }


def create_backend_mcp_servers(auth_token: Optional[str] = None) -> dict:
    """
    创建后端 MCP 服务器集合

    Args:
        auth_token: JWT Token

    Returns:
        MCP Servers 配置字典
    """
    return {
        "backend": create_http_mcp_config(auth_token=auth_token),
    }


# 后端工具名称枚举（与后端 API 对应）
class BackendToolName:
    """后端服务提供的工具名称"""

    # 项目管理
    LIST_PROJECTS = "list_projects"
    GET_PROJECT = "get_project"
    CREATE_PROJECT = "create_project"
    UPDATE_PROJECT = "update_project"
    DELETE_PROJECT = "delete_project"

    # 广告计划
    LIST_CAMPAIGNS = "list_campaigns"
    GET_CAMPAIGN = "get_campaign"
    CREATE_CAMPAIGN = "create_campaign"
    UPDATE_CAMPAIGN = "update_campaign"
    DELETE_CAMPAIGN = "delete_campaign"

    # 素材管理
    LIST_MATERIALS = "list_materials"
    GET_MATERIAL = "get_material"
    UPLOAD_MATERIAL = "upload_material"
    DELETE_MATERIAL = "delete_material"

    # 平台授权
    LIST_PLATFORM_AUTHS = "list_platform_auths"
    GET_PLATFORM_AUTH = "get_platform_auth"


def get_backend_tool_names() -> list[str]:
    """获取所有后端工具名称"""
    return [
        # 项目管理
        BackendToolName.LIST_PROJECTS,
        BackendToolName.GET_PROJECT,
        BackendToolName.CREATE_PROJECT,
        BackendToolName.UPDATE_PROJECT,
        BackendToolName.DELETE_PROJECT,

        # 广告计划
        BackendToolName.LIST_CAMPAIGNS,
        BackendToolName.GET_CAMPAIGN,
        BackendToolName.CREATE_CAMPAIGN,
        BackendToolName.UPDATE_CAMPAIGN,
        BackendToolName.DELETE_CAMPAIGN,

        # 素材管理
        BackendToolName.LIST_MATERIALS,
        BackendToolName.GET_MATERIAL,
        BackendToolName.UPLOAD_MATERIAL,
        BackendToolName.DELETE_MATERIAL,

        # 平台授权
        BackendToolName.LIST_PLATFORM_AUTHS,
        BackendToolName.GET_PLATFORM_AUTH,
    ]
