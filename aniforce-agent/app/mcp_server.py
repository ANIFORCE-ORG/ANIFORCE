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


def _compact_payload(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


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
        logger.info(f"[MCP] create_project 使用用户编辑后的参数: {approved}")
        data.update(_compact_payload(approved))
    return await backend_client.create_project(
        token=token,
        data=data,
        extra_headers=_get_backend_headers(ctx, "create_project", data),
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
        logger.info(f"[MCP] update_project 使用用户编辑后的参数: {approved}")
        data.update(_compact_payload(approved))
    return await backend_client.update_project(
        token=token,
        project_id=project_id,
        data=data,
        extra_headers=_get_backend_headers(ctx, "update_project", {"project_id": project_id, **data}),
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
        logger.info(f"[MCP] create_campaign 使用用户编辑后的参数: {approved}")
        data.update(_compact_payload(approved))
    return await backend_client.create_campaign(
        token=token,
        data=data,
        extra_headers=_get_backend_headers(ctx, "create_campaign", data),
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
        logger.info(f"[MCP] update_campaign 使用用户编辑后的参数: {approved}")
        data.update(_compact_payload(approved))
    return await backend_client.update_campaign(
        token=token,
        campaign_id=campaign_id,
        data=data,
        extra_headers=_get_backend_headers(ctx, "update_campaign", {"campaign_id": campaign_id, **data}),
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
    return await backend_client.add_material_to_campaign(
        token=token,
        campaign_id=campaign_id,
        material_id=material_id,
        extra_headers=_get_backend_headers(ctx, "add_material_to_campaign", args),
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
    return await backend_client.remove_material_from_campaign(
        token=token,
        campaign_id=campaign_id,
        material_id=material_id,
        extra_headers=_get_backend_headers(ctx, "remove_material_from_campaign", args),
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
async def list_materials(ctx: Context, project_id: str = "", campaign_id: str = "", type: str = "", limit: int = 20) -> dict:
    """列出广告素材（可按项目、广告计划、类型过滤）。

    Args:
        project_id: 可选，按项目 ID 过滤
        campaign_id: 可选，按广告计划 ID 过滤
        type: 可选，按素材类型过滤
        limit: 返回数量上限

    Returns:
        素材列表
    """
    token = _get_token(ctx)
    return await backend_client.list_materials(
        token=token,
        project_id=project_id or None,
        campaign_id=campaign_id or None,
        type=type or None,
        limit=limit,
    )


@mcp.tool()
async def create_material(
    ctx: Context,
    name: str,
    type: str,
    url: str,
    thumbnail_url: str = "",
    project_ids: Optional[list[str]] = None,
    campaign_ids: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    ctr_estimate: Optional[float] = None,
) -> dict:
    """创建素材记录，不处理文件上传，字段对齐 backend CreateMaterialRequest。

    Args:
        name: 素材名称
        type: 素材类型
        url: 素材 URL
        thumbnail_url: 缩略图 URL
        project_ids: 关联项目 ID 列表
        campaign_ids: 关联广告计划 ID 列表
        tags: 标签列表
        ctr_estimate: CTR 预估

    Returns:
        创建后的素材信息
    """
    token = _get_token(ctx)
    data = _compact_payload({
        "name": name,
        "type": type,
        "url": url,
        "thumbnail_url": thumbnail_url or None,
        "project_ids": project_ids,
        "campaign_ids": campaign_ids,
        "tags": tags,
        "ctr_estimate": ctr_estimate,
    })
    approved = await _get_approved_arguments(ctx, "create_material")
    if approved:
        logger.info(f"[MCP] create_material 使用用户编辑后的参数: {approved}")
        data.update(_compact_payload(approved))
    return await backend_client.create_material(
        token=token,
        data=data,
        extra_headers=_get_backend_headers(ctx, "create_material", data),
    )


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


@mcp.tool()
async def get_material_image(ctx: Context, material_id: str, thumbnail: bool = False) -> dict:
    """获取素材预览资源元信息。若 backend 返回 base64，本工具会截断 data 字段避免大 payload。

    Args:
        material_id: 素材 ID
        thumbnail: 是否请求缩略图

    Returns:
        素材图片/视频预览元信息，优先包含 url/mime_type/size
    """
    token = _get_token(ctx)
    result = await backend_client.get_material_image(token=token, material_id=material_id, thumbnail=thumbnail)
    if isinstance(result, dict) and isinstance(result.get("data"), str) and len(result["data"]) > 200:
        result = {**result, "data": "[base64_data_omitted]"}
    return result


@mcp.tool()
async def list_available_images(ctx: Context) -> dict:
    """列出 backend 本地可用图像文件。"""
    token = _get_token(ctx)
    return await backend_client.list_available_images(token=token)


@mcp.tool()
async def update_material(
    ctx: Context,
    material_id: str,
    name: str = "",
    status: str = "",
    thumbnail_url: str = "",
    poster_url: str = "",
    preview_url: str = "",
    ctr_estimate: Optional[float] = None,
    tags: Optional[list[str]] = None,
    media_kind: str = "",
    format: str = "",
    width: Optional[int] = None,
    height: Optional[int] = None,
    ratio: str = "",
    source: str = "",
    creator: str = "",
    rights: str = "",
    platforms: Optional[list[str]] = None,
    review_status: str = "",
    source_account: str = "",
    placements: Optional[list[str]] = None,
    score: Optional[int] = None,
    fatigue: Optional[int] = None,
    duration: Optional[int] = None,
    file_size: Optional[int] = None,
) -> dict:
    """更新素材基础信息，字段对齐 backend UpdateMaterialRequest。

    Args:
        material_id: 素材 ID
        name: 素材名称
        status: 素材状态
        thumbnail_url: 缩略图 URL
        poster_url: 视频封面 URL
        preview_url: 预览 URL
        ctr_estimate: CTR 预估
        tags: 标签列表
        media_kind: 媒体类型
        format: 文件格式
        width: 宽度
        height: 高度
        ratio: 宽高比
        source: 来源
        creator: 创作者
        rights: 版权信息
        platforms: 适用平台
        review_status: 审核状态
        source_account: 来源账号
        placements: 版位
        score: 素材评分
        fatigue: 疲劳度
        duration: 时长
        file_size: 文件大小

    Returns:
        更新后的素材信息
    """
    token = _get_token(ctx)
    data = _compact_payload({
        "name": name or None,
        "status": status or None,
        "thumbnail_url": thumbnail_url or None,
        "poster_url": poster_url or None,
        "preview_url": preview_url or None,
        "ctr_estimate": ctr_estimate,
        "tags": tags,
        "media_kind": media_kind or None,
        "format": format or None,
        "width": width,
        "height": height,
        "ratio": ratio or None,
        "source": source or None,
        "creator": creator or None,
        "rights": rights or None,
        "platforms": platforms,
        "review_status": review_status or None,
        "source_account": source_account or None,
        "placements": placements,
        "score": score,
        "fatigue": fatigue,
        "duration": duration,
        "file_size": file_size,
    })
    approved = await _get_approved_arguments(ctx, "update_material")
    if approved:
        logger.info(f"[MCP] update_material 使用用户编辑后的参数: {approved}")
        data.update(_compact_payload(approved))
    return await backend_client.update_material(
        token=token,
        material_id=material_id,
        data=data,
        extra_headers=_get_backend_headers(ctx, "update_material", {"material_id": material_id, **data}),
    )


@mcp.tool()
async def add_material_to_project(ctx: Context, material_id: str, project_id: str) -> dict:
    """把素材添加到项目。"""
    token = _get_token(ctx)
    args = {"material_id": material_id, "project_id": project_id}
    return await backend_client.add_material_to_project(
        token=token,
        material_id=material_id,
        project_id=project_id,
        extra_headers=_get_backend_headers(ctx, "add_material_to_project", args),
    )


@mcp.tool()
async def remove_material_from_project(ctx: Context, material_id: str, project_id: str) -> dict:
    """从项目移除素材。"""
    token = _get_token(ctx)
    args = {"material_id": material_id, "project_id": project_id}
    return await backend_client.remove_material_from_project(
        token=token,
        material_id=material_id,
        project_id=project_id,
        extra_headers=_get_backend_headers(ctx, "remove_material_from_project", args),
    )


@mcp.tool()
async def delete_material(ctx: Context, material_id: str) -> dict:
    """删除指定素材。"""
    token = _get_token(ctx)
    return await backend_client.delete_material(
        token=token,
        material_id=material_id,
        extra_headers=_get_backend_headers(ctx, "delete_material", {"material_id": material_id}),
    )


def get_mcp_starlette_app():
    """获取 FastMCP 的 streamable_http Starlette app，用于挂载到 FastAPI"""
    return mcp.streamable_http_app()
