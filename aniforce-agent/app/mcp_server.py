"""MCP Server（路径 B + 多租户隔离）

agent-service 内部用 FastMCP 定义业务工具，工具内通过 backend_client 调 backend REST API。
Agent 通过 MCPServerStreamableHttp 连本进程的 /mcp 端点。

多租户隔离：
- agent runtime 把 JWT 放进 RunContext.context（dict，含 jwt_token）
- MCPServerStreamableHttp 的 tool_meta_resolver 从 RunContext 读 jwt_token，注入每次 call_tool 的 _meta
- server 端工具函数从 ctx.request_context.meta["jwt_token"] 读
- 每次 MCP 调用独立带 token，天然按请求隔离，多用户并发不串号
"""

from typing import Optional

from loguru import logger
from mcp.server.fastmcp import FastMCP, Context

from app.backend_client import backend_client


# ---- FastMCP Server ----
mcp = FastMCP("ANIFORCE Tools")


def _get_token(ctx) -> str:
    """从 MCP Context 的 request_context.meta 读 JWT token"""
    try:
        meta = ctx.request_context.meta
        token = ""

        if isinstance(meta, dict):
            token = meta.get("jwt_token", "")
        elif hasattr(meta, "model_dump"):
            token = (meta.model_dump() or {}).get("jwt_token", "")
        elif meta is not None:
            token = getattr(meta, "jwt_token", "") or ""

        if not token:
            logger.warning("[MCP] request_context.meta 无 jwt_token")
        return token
    except Exception as e:
        logger.warning(f"[MCP] 读取 token 失败: {e}")
        return ""


# ============ Project 工具 ============

@mcp.tool()
async def list_projects(ctx: Context, limit: int = 20) -> dict:
    """列出当前用户的广告投放项目。

    Args:
        limit: 返回数量上限，默认 20

    Returns:
        项目列表，包含 id/name/status/budget 等
    """
    token = _get_token(ctx)
    return await backend_client.list_projects(token=token, limit=limit)


@mcp.tool()
async def get_project_detail(ctx: Context, project_id: str) -> dict:
    """获取指定项目的详细信息。

    Args:
        project_id: 项目 ID

    Returns:
        项目详情，包含描述、预算、计划数等
    """
    token = _get_token(ctx)
    return await backend_client.get_project(token=token, project_id=project_id)


@mcp.tool()
async def create_project(
    ctx: Context,
    name: str,
    total_budget: float,
    description: str = "",
    game_type: str = "",
    target_market: str = "",
) -> dict:
    """创建新的广告投放项目。

    Args:
        name: 项目名称
        total_budget: 总预算
        description: 项目描述
        game_type: 游戏类型（如 RPG、SLG）
        target_market: 目标市场

    Returns:
        创建后的项目信息
    """
    token = _get_token(ctx)
    data = {
        "name": name,
        "total_budget": total_budget,
        "description": description or None,
        "game_type": game_type or None,
        "target_market": target_market or None,
    }
    return await backend_client.create_project(token=token, data=data)


# ============ Campaign 工具 ============

@mcp.tool()
async def list_campaigns(ctx: Context, project_id: str = "", limit: int = 20) -> dict:
    """列出广告计划（可按项目过滤）。

    Args:
        project_id: 可选，按项目 ID 过滤
        limit: 返回数量上限

    Returns:
        计划列表
    """
    token = _get_token(ctx)
    return await backend_client.list_campaigns(
        token=token,
        project_id=project_id or None,
        limit=limit,
    )


@mcp.tool()
async def get_campaign_detail(ctx: Context, campaign_id: str) -> dict:
    """获取指定广告计划的详情。

    Args:
        campaign_id: 计划 ID

    Returns:
        计划详情
    """
    token = _get_token(ctx)
    return await backend_client.get_campaign(token=token, campaign_id=campaign_id)


@mcp.tool()
async def create_campaign(
    ctx: Context,
    project_id: str,
    name: str,
    budget: float,
    platform: str = "Meta",
) -> dict:
    """在指定项目下创建新的广告计划。

    Args:
        project_id: 所属项目 ID
        name: 计划名称
        budget: 计划预算
        platform: 投放平台（Meta / Google）

    Returns:
        创建后的计划信息
    """
    token = _get_token(ctx)
    data = {
        "project_id": project_id,
        "name": name,
        "budget": budget,
        "platform": platform,
    }
    return await backend_client.create_campaign(token=token, data=data)


@mcp.tool()
async def update_campaign_status(ctx: Context, campaign_id: str, status: str) -> dict:
    """更新广告计划状态（如 active / paused / completed）。

    Args:
        campaign_id: 计划 ID
        status: 新状态

    Returns:
        更新后的计划信息
    """
    token = _get_token(ctx)
    return await backend_client.update_campaign_status(
        token=token, campaign_id=campaign_id, status=status
    )


# ============ Material 工具 ============

@mcp.tool()
async def list_materials(ctx: Context, limit: int = 20) -> dict:
    """列出广告素材。

    Args:
        limit: 返回数量上限

    Returns:
        素材列表
    """
    token = _get_token(ctx)
    return await backend_client.list_materials(token=token, limit=limit)


@mcp.tool()
async def get_material_detail(ctx: Context, material_id: str) -> dict:
    """获取指定素材的详情。

    Args:
        material_id: 素材 ID

    Returns:
        素材详情
    """
    token = _get_token(ctx)
    return await backend_client.get_material(token=token, material_id=material_id)


def get_mcp_starlette_app():
    """获取 FastMCP 的 streamable_http Starlette app，用于挂载到 FastAPI"""
    return mcp.streamable_http_app()
