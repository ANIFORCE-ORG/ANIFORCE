"""
MCP API 端点

提供标准 MCP 协议接口：
- GET /mcp/tools - 列出所有工具
- POST /mcp/tools/{tool_name} - 调用工具
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_current_user
from app.services.mcp_service import MCPService
from app.repositories.factory import (
    get_project_repo,
    get_campaign_repo,
    get_material_repo,
    get_platform_auth_repo,
)
from app.config.settings import get_settings

router = APIRouter(prefix="/mcp", tags=["mcp"])


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    name: str
    arguments: dict


def get_mcp_service(
    project_repo=Depends(get_project_repo),
    campaign_repo=Depends(get_campaign_repo),
    material_repo=Depends(get_material_repo),
    platform_auth_repo=Depends(get_platform_auth_repo),
) -> MCPService:
    """获取 MCP Service 实例"""
    return MCPService(
        project_repo=project_repo,
        campaign_repo=campaign_repo,
        material_repo=material_repo,
        platform_auth_repo=platform_auth_repo,
    )


def verify_internal_token(x_internal_token: Optional[str] = Header(None)):
    """验证内部服务 Token"""
    settings = get_settings()
    if x_internal_token != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid internal token")


@router.get("/tools")
async def list_tools(
    mcp_service: MCPService = Depends(get_mcp_service),
    _: None = Depends(verify_internal_token),
):
    """
    列出所有可用工具

    MCP 协议：tools/list
    """
    tools = mcp_service.list_tools()
    return {"tools": tools}


@router.post("/tools/{tool_name}")
async def call_tool(
    tool_name: str,
    request: ToolCallRequest,
    current_user: dict = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service),
    _: None = Depends(verify_internal_token),
):
    """
    调用工具

    MCP 协议：tools/call

    Args:
        tool_name: 工具名称（路径参数）
        request: 工具参数

    Returns:
        MCP 标准响应格式
    """
    result = await mcp_service.call_tool(
        tool_name=tool_name,
        arguments=request.arguments,
        user_id=current_user["id"],
    )
    return result
