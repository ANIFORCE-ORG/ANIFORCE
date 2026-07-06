"""MCP Server（路径 B + 多租户隔离）

agent-service 内部用 FastMCP 定义业务工具，工具内通过 backend_client 调 backend REST API。
Agent 通过 MCPServerStreamableHttp 连本进程的 /mcp 端点。

多租户隔离：
- agent runtime 把 JWT 放进 RunContext.context（dict，含 jwt_token）
- MCPServerStreamableHttp 的 tool_meta_resolver 从 RunContext 读 jwt_token，注入每次 call_tool 的 _meta
- server 端工具函数从 ctx.request_context.meta["jwt_token"] 读
- 每次 MCP 调用独立带 token，天然按请求隔离，多用户并发不串号
"""

import hashlib
import json
from typing import Optional

from loguru import logger
from mcp.server.fastmcp import FastMCP, Context

from app.backend_client import backend_client


# ---- FastMCP Server ----
mcp = FastMCP("ANIFORCE Tools")


def _get_meta(ctx) -> dict:
    """从 MCP Context 的 request_context.meta 读元信息"""
    try:
        meta = ctx.request_context.meta
        if isinstance(meta, dict):
            return meta
        if hasattr(meta, "model_dump"):
            return meta.model_dump() or {}
        if meta is not None:
            return {
                "jwt_token": getattr(meta, "jwt_token", "") or "",
                "session_id": getattr(meta, "session_id", "") or "",
                "run_id": getattr(meta, "run_id", "") or "",
                "user_id": getattr(meta, "user_id", "") or "",
            }
    except Exception as e:
        logger.warning(f"[MCP] 读取 meta 失败: {e}")
    return {}


def _get_token(ctx) -> str:
    """从 MCP Context 的 request_context.meta 读 JWT token"""
    token = _get_meta(ctx).get("jwt_token", "")
    if not token:
        logger.warning("[MCP] request_context.meta 无 jwt_token")
    return token


def _make_tool_call_id(ctx, tool_name: str, arguments: dict) -> str | None:
    meta = _get_meta(ctx)
    session_id = meta.get("session_id")
    run_id = meta.get("run_id")
    if not session_id or not run_id:
        return None
    raw = json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{session_id}:{run_id}:{tool_name}:{digest}"


def _get_backend_headers(ctx, tool_name: str | None = None, arguments: dict | None = None) -> dict[str, str]:
    meta = _get_meta(ctx)
    headers: dict[str, str] = {}
    if meta.get("session_id"):
        headers["X-Agent-Session-Id"] = str(meta["session_id"])
    if meta.get("run_id"):
        headers["X-Agent-Run-Id"] = str(meta["run_id"])
    if tool_name and arguments is not None:
        tool_call_id = _make_tool_call_id(ctx, tool_name, arguments)
        if tool_call_id:
            headers["X-Agent-Tool-Call-Id"] = tool_call_id
            headers["Idempotency-Key"] = tool_call_id
    return headers


async def _get_approved_arguments(ctx, tool_name: str) -> dict | None:
    """查询当前 run 的 checkpoint，读取用户编辑后的审批参数。

    Workspace 可编辑 HITL：用户在 Workspace 表单里改了参数后 approve，
    approved_arguments 存在 checkpoint metadata 里。
    MCP 工具执行前读出来覆盖原始 arguments。
    """
    meta = _get_meta(ctx)
    run_id = meta.get("run_id")
    if not run_id:
        return None
    try:
        import aiosqlite
        from app.config.settings import get_settings
        db_url = get_settings().AGENT_RUNTIME_DB_URL
        if "sqlite" not in db_url:
            return None
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT approved_arguments_json FROM runtime_checkpoints "
                "WHERE run_id = ? AND approved_arguments_json IS NOT NULL "
                "ORDER BY resolved_at DESC LIMIT 1",
                (run_id,),
            )
            row = await cursor.fetchone()
            if row and row["approved_arguments_json"]:
                return json.loads(row["approved_arguments_json"])
    except Exception as e:
        logger.warning(f"[MCP] 读取 approved_arguments 失败: {e}")
    return None


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
    # Workspace 可编辑 HITL：用用户确认后的参数覆盖原始 arguments
    approved = await _get_approved_arguments(ctx, "create_project")
    if approved:
        logger.info(f"[MCP] create_project 使用用户编辑后的参数: {approved}")
        data.update({k: v for k, v in approved.items() if v is not None})
    return await backend_client.create_project(
        token=token,
        data=data,
        extra_headers=_get_backend_headers(ctx, "create_project", data),
    )


@mcp.tool()
async def delete_project(ctx: Context, project_id: str) -> dict:
    """删除指定广告投放项目。

    Args:
        project_id: 项目 ID

    Returns:
        删除结果
    """
    token = _get_token(ctx)
    return await backend_client.delete_project(
        token=token,
        project_id=project_id,
        extra_headers=_get_backend_headers(ctx, "delete_project", {"project_id": project_id}),
    )


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
    return await backend_client.create_campaign(
        token=token,
        data=data,
        extra_headers=_get_backend_headers(ctx, "create_campaign", data),
    )


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
        token=token,
        campaign_id=campaign_id,
        status=status,
        extra_headers=_get_backend_headers(ctx, "update_campaign_status", {"campaign_id": campaign_id, "status": status}),
    )


@mcp.tool()
async def delete_campaign(ctx: Context, campaign_id: str) -> dict:
    """删除指定广告计划。

    Args:
        campaign_id: 计划 ID

    Returns:
        删除结果
    """
    token = _get_token(ctx)
    return await backend_client.delete_campaign(
        token=token,
        campaign_id=campaign_id,
        extra_headers=_get_backend_headers(ctx, "delete_campaign", {"campaign_id": campaign_id}),
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
