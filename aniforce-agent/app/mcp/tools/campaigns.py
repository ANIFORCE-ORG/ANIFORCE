"""Campaign MCP tools."""

from typing import Literal, Optional

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
from app.mcp.verification import verify_absent, verify_collection_membership, verify_fields

@mcp.tool()
async def list_campaigns(ctx: Context, project_id: str = "", status: str = "", limit: int = 20) -> dict:
    """列出广告计划（可按项目和状态过滤）。

    Args:
        project_id: 可选，按项目 ID 过滤
        status: 可选，按广告计划状态过滤
        limit: 返回数量上限

    Returns:
        计划列表
    """
    token = _get_token(ctx)
    return await backend_client.list_campaigns(
        token=token,
        project_id=project_id or None,
        status=status or None,
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
async def get_campaign_performance(ctx: Context, campaign_id: str, hours: int = 168) -> dict:
    """获取广告计划的最新指标和时间序列证据，供效果诊断使用。

    Args:
        campaign_id: 广告计划 ID
        hours: 查询时间窗口小时数，默认 168（最近 7 天），范围 1 至 2160

    Returns:
        最新指标、窗口内变化、时间序列和数据新鲜度。data_available=false 表示没有指标，不能据此判断效果。
    """
    token = _get_token(ctx)
    return await backend_client.get_campaign_performance(token=token, campaign_id=campaign_id, hours=hours)


@mcp.tool()
async def create_campaign(
    ctx: Context,
    project_id: str,
    name: str,
    budget: float,
    platform: str,
    status: str = "draft",
    material_ids: Optional[list[str]] = None,
    account_id: str = "",
    objective: str = "",
    buying_type: str = "",
    special_ad_categories: str = "",
    special_ad_category_country: str = "",
    promoted_object: str = "",
    ab_test: str = "",
    campaign_budget_optimization: str = "",
    budget_type: str = "",
    budget_schedule_specs: str = "",
    pacing_type: str = "",
    bid_strategy: str = "",
    spend_limit: Optional[float] = None,
    start_date: str = "",
    end_date: str = "",
) -> dict:
    """在指定项目下创建新的广告计划，字段对齐 backend CreateCampaignRequest。

    Args:
        project_id: 所属项目 ID
        name: 计划名称
        budget: 计划预算
        platform: 投放平台（Meta / Google / TikTok）
        status: 计划状态，默认 draft
        material_ids: 关联素材 ID 列表
        account_id: 平台广告账户 ID
        objective: 广告目标
        buying_type: 购买类型
        special_ad_categories: 特殊广告类别
        special_ad_category_country: 特殊广告类别国家
        promoted_object: 推广对象
        ab_test: A/B 测试配置
        campaign_budget_optimization: 预算优化配置
        budget_type: 预算类型
        budget_schedule_specs: 预算排期规格
        pacing_type: 花费节奏
        bid_strategy: 出价策略
        spend_limit: 花费上限
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        创建后的计划信息
    """
    token = _get_token(ctx)
    data = _compact_payload({
        "project_id": project_id,
        "name": name,
        "platform": platform,
        "budget": budget,
        "status": status or None,
        "material_ids": material_ids,
        "account_id": account_id or None,
        "objective": objective or None,
        "buying_type": buying_type or None,
        "special_ad_categories": special_ad_categories or None,
        "special_ad_category_country": special_ad_category_country or None,
        "promoted_object": promoted_object or None,
        "ab_test": ab_test or None,
        "campaign_budget_optimization": campaign_budget_optimization or None,
        "budget_type": budget_type or None,
        "budget_schedule_specs": budget_schedule_specs or None,
        "pacing_type": pacing_type or None,
        "bid_strategy": bid_strategy or None,
        "spend_limit": spend_limit,
        "start_date": start_date or None,
        "end_date": end_date or None,
    })
    approved = await _get_approved_arguments(ctx, "create_campaign")
    if approved:
        logger.bind(event="agent.tool.arguments_edited", tool_name="create_campaign").info(
            "Using user-edited tool arguments: fields={}", sorted(approved)
        )
        data.update(_compact_payload(approved))
    result = await backend_client.create_campaign(
        token=token,
        data=data,
        extra_headers=_get_backend_headers(ctx, "create_campaign", data),
    )
    campaign_id = str(result.get("id") or "")
    return await verify_fields(
        result,
        lambda: backend_client.get_campaign(token, campaign_id),
        data,
        entity_id=campaign_id,
    )


@mcp.tool()
async def update_campaign(
    ctx: Context,
    campaign_id: str,
    name: str = "",
    platform: str = "",
    budget: Optional[float] = None,
    status: str = "",
    material_ids: Optional[list[str]] = None,
    account_id: str = "",
    objective: str = "",
    buying_type: str = "",
    special_ad_categories: str = "",
    special_ad_category_country: str = "",
    promoted_object: str = "",
    ab_test: str = "",
    campaign_budget_optimization: str = "",
    budget_type: str = "",
    budget_schedule_specs: str = "",
    pacing_type: str = "",
    bid_strategy: str = "",
    spend_limit: Optional[float] = None,
    start_date: str = "",
    end_date: str = "",
) -> dict:
    """更新广告计划字段，字段对齐 backend UpdateCampaignRequest。

    Args:
        campaign_id: 计划 ID
        name: 计划名称
        platform: 投放平台
        budget: 计划预算
        status: 计划状态
        material_ids: 关联素材 ID 列表
        account_id: 平台广告账户 ID
        objective: 广告目标
        buying_type: 购买类型
        special_ad_categories: 特殊广告类别
        special_ad_category_country: 特殊广告类别国家
        promoted_object: 推广对象
        ab_test: A/B 测试配置
        campaign_budget_optimization: 预算优化配置
        budget_type: 预算类型
        budget_schedule_specs: 预算排期规格
        pacing_type: 花费节奏
        bid_strategy: 出价策略
        spend_limit: 花费上限
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        更新后的计划信息
    """
    token = _get_token(ctx)
    data = _compact_payload({
        "name": name or None,
        "platform": platform or None,
        "budget": budget,
        "status": status or None,
        "material_ids": material_ids,
        "account_id": account_id or None,
        "objective": objective or None,
        "buying_type": buying_type or None,
        "special_ad_categories": special_ad_categories or None,
        "special_ad_category_country": special_ad_category_country or None,
        "promoted_object": promoted_object or None,
        "ab_test": ab_test or None,
        "campaign_budget_optimization": campaign_budget_optimization or None,
        "budget_type": budget_type or None,
        "budget_schedule_specs": budget_schedule_specs or None,
        "pacing_type": pacing_type or None,
        "bid_strategy": bid_strategy or None,
        "spend_limit": spend_limit,
        "start_date": start_date or None,
        "end_date": end_date or None,
    })
    approved = await _get_approved_arguments(ctx, "update_campaign")
    if approved:
        logger.bind(event="agent.tool.arguments_edited", tool_name="update_campaign").info(
            "Using user-edited tool arguments: fields={}", sorted(approved)
        )
        data.update(_compact_payload(approved))
    result = await backend_client.update_campaign(
        token=token,
        campaign_id=campaign_id,
        data=data,
        extra_headers=_get_backend_headers(ctx, "update_campaign", {"campaign_id": campaign_id, **data}),
    )
    return await verify_fields(
        result,
        lambda: backend_client.get_campaign(token, campaign_id),
        data,
        entity_id=campaign_id,
    )


@mcp.tool()
async def update_campaign_status(
    ctx: Context,
    campaign_id: str,
    status: Literal["draft", "running", "review", "paused", "completed"],
) -> dict:
    """更新广告计划状态。

    Args:
        campaign_id: 计划 ID
        status: 新状态，只能是 draft、running、review、paused 或 completed

    Returns:
        更新后的计划信息
    """
    token = _get_token(ctx)
    result = await backend_client.update_campaign_status(
        token=token,
        campaign_id=campaign_id,
        status=status,
        extra_headers=_get_backend_headers(ctx, "update_campaign_status", {"campaign_id": campaign_id, "status": status}),
    )
    return await verify_fields(
        result,
        lambda: backend_client.get_campaign(token, campaign_id),
        {"status": status},
        entity_id=campaign_id,
    )


@mcp.tool()
async def get_campaign_materials(ctx: Context, campaign_id: str) -> dict:
    """获取广告计划关联的素材列表。

    Args:
        campaign_id: 计划 ID

    Returns:
        素材列表
    """
    token = _get_token(ctx)
    return await backend_client.get_campaign_materials(token=token, campaign_id=campaign_id)


@mcp.tool()
async def add_material_to_campaign(ctx: Context, campaign_id: str, material_id: str) -> dict:
    """把素材添加到广告计划。

    Args:
        campaign_id: 计划 ID
        material_id: 素材 ID

    Returns:
        绑定结果
    """
    token = _get_token(ctx)
    args = {"campaign_id": campaign_id, "material_id": material_id}
    result = await backend_client.add_material_to_campaign(
        token=token,
        campaign_id=campaign_id,
        material_id=material_id,
        extra_headers=_get_backend_headers(ctx, "add_material_to_campaign", args),
    )
    return await verify_collection_membership(
        result,
        lambda: backend_client.get_campaign_materials(token, campaign_id),
        collection_key="materials",
        entity_id=material_id,
        should_exist=True,
    )


@mcp.tool()
async def remove_material_from_campaign(ctx: Context, campaign_id: str, material_id: str) -> dict:
    """从广告计划移除素材。

    Args:
        campaign_id: 计划 ID
        material_id: 素材 ID

    Returns:
        解绑结果
    """
    token = _get_token(ctx)
    args = {"campaign_id": campaign_id, "material_id": material_id}
    result = await backend_client.remove_material_from_campaign(
        token=token,
        campaign_id=campaign_id,
        material_id=material_id,
        extra_headers=_get_backend_headers(ctx, "remove_material_from_campaign", args),
    )
    return await verify_collection_membership(
        result,
        lambda: backend_client.get_campaign_materials(token, campaign_id),
        collection_key="materials",
        entity_id=material_id,
        should_exist=False,
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
    result = await backend_client.delete_campaign(
        token=token,
        campaign_id=campaign_id,
        extra_headers=_get_backend_headers(ctx, "delete_campaign", {"campaign_id": campaign_id}),
    )
    return await verify_absent(
        result,
        lambda: backend_client.get_campaign(token, campaign_id),
        entity_id=campaign_id,
    )


