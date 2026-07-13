"""Project MCP tools."""

from typing import Optional

from loguru import logger
from mcp.server.fastmcp import Context

from app.backend_client import backend_client
from app.mcp.approval import get_approved_arguments as _get_approved_arguments
from app.mcp.context import (
    backend_headers as _get_backend_headers,
    compact_payload as _compact_payload,
    get_token as _get_token,
)
from app.mcp.server import mcp
from app.mcp.verification import verify_absent, verify_fields

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
async def get_project_performance(ctx: Context, project_id: str, hours: int = 168) -> dict:
    """获取项目下广告计划的投放指标汇总，供项目复盘和计划对比使用。

    Args:
        project_id: 项目 ID
        hours: 查询时间窗口小时数，默认 168（最近 7 天），范围 1 至 2160

    Returns:
        项目指标汇总、各计划最新指标、无数据数量和 ROI 排序。data_available=false 表示没有指标，不能推断表现为零。
    """
    token = _get_token(ctx)
    return await backend_client.get_project_performance(token=token, project_id=project_id, hours=hours)


@mcp.tool()
async def create_project(
    ctx: Context,
    name: str,
    total_budget: float = 0,
    product: str = "",
    target_market: str = "",
    status: str = "active",
    start_date: str = "",
    end_date: str = "",
    manager: str = "",
    game_type: str = "",
    tags: Optional[list[str]] = None,
    description: str = "",
) -> dict:
    """创建新的广告投放项目，字段对齐 backend CreateProjectRequest。

    Args:
        name: 项目名称
        total_budget: 总预算
        product: 产品/应用名称
        target_market: 目标市场
        status: 项目状态，默认 active
        start_date: 开始日期
        end_date: 结束日期
        manager: 负责人
        game_type: 游戏类型（如 RPG、SLG）
        tags: 标签列表
        description: 项目描述

    Returns:
        创建后的项目信息
    """
    token = _get_token(ctx)
    data = _compact_payload({
        "name": name,
        "product": product or None,
        "target_market": target_market or None,
        "status": status or None,
        "start_date": start_date or None,
        "end_date": end_date or None,
        "total_budget": total_budget,
        "manager": manager or None,
        "game_type": game_type or None,
        "tags": tags,
        "description": description or None,
    })
    # Workspace 可编辑 HITL：用用户确认后的参数覆盖原始 arguments
    approved = await _get_approved_arguments(ctx, "create_project")
    if approved:
        logger.bind(event="agent.tool.arguments_edited", tool_name="create_project").info(
            "Using user-edited tool arguments: fields={}", sorted(approved)
        )
        data.update(_compact_payload(approved))
    result = await backend_client.create_project(
        token=token,
        data=data,
        extra_headers=_get_backend_headers(ctx, "create_project", data),
    )
    project_id = str(result.get("id") or "")
    return await verify_fields(
        result,
        lambda: backend_client.get_project(token, project_id),
        data,
        entity_id=project_id,
    )


@mcp.tool()
async def update_project(
    ctx: Context,
    project_id: str,
    name: str = "",
    product: str = "",
    target_market: str = "",
    status: str = "",
    start_date: str = "",
    end_date: str = "",
    total_budget: Optional[float] = None,
    description: str = "",
) -> dict:
    """更新项目字段，字段对齐 backend UpdateProjectRequest。

    Args:
        project_id: 项目 ID
        name: 项目名称
        product: 产品/应用名称
        target_market: 目标市场
        status: 项目状态
        start_date: 开始日期
        end_date: 结束日期
        total_budget: 总预算
        description: 项目描述

    Returns:
        更新后的项目信息
    """
    token = _get_token(ctx)
    data = _compact_payload({
        "name": name or None,
        "product": product or None,
        "target_market": target_market or None,
        "status": status or None,
        "start_date": start_date or None,
        "end_date": end_date or None,
        "total_budget": total_budget,
        "description": description or None,
    })
    approved = await _get_approved_arguments(ctx, "update_project")
    if approved:
        logger.bind(event="agent.tool.arguments_edited", tool_name="update_project").info(
            "Using user-edited tool arguments: fields={}", sorted(approved)
        )
        data.update(_compact_payload(approved))
    result = await backend_client.update_project(
        token=token,
        project_id=project_id,
        data=data,
        extra_headers=_get_backend_headers(ctx, "update_project", {"project_id": project_id, **data}),
    )
    return await verify_fields(
        result,
        lambda: backend_client.get_project(token, project_id),
        data,
        entity_id=project_id,
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
    result = await backend_client.delete_project(
        token=token,
        project_id=project_id,
        extra_headers=_get_backend_headers(ctx, "delete_project", {"project_id": project_id}),
    )
    return await verify_absent(
        result,
        lambda: backend_client.get_project(token, project_id),
        entity_id=project_id,
    )


