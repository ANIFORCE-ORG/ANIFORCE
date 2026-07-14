"""Material MCP tools."""

from typing import Literal, Optional

from loguru import logger
from mcp.server.fastmcp import Context

from app.backend_client import backend_client
from app.mcp.approval import get_approved_arguments as _get_approved_arguments
from app.mcp.context import (
    backend_headers as _get_backend_headers,
    compact_payload as _compact_payload,
    compact_update_payload as _compact_update_payload,
    get_token as _get_token,
)
from app.mcp.server import mcp
from app.mcp.verification import verify_absent, verify_collection_membership, verify_fields

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
    type: Literal["a_segment", "b_segment", "c_segment", "full_video"],
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
        type: 素材类型，只能是 a_segment、b_segment、c_segment 或 full_video；完整视频使用 full_video
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
        logger.bind(event="agent.tool.arguments_edited", tool_name="create_material").info(
            "Using user-edited tool arguments: fields={}", sorted(approved)
        )
        data.update(_compact_payload(approved))
    result = await backend_client.create_material(
        token=token,
        data=data,
        extra_headers=_get_backend_headers(ctx, "create_material", data),
    )
    material_id = str(result.get("id") or "")
    return await verify_fields(
        result,
        lambda: backend_client.get_material(token, material_id),
        data,
        entity_id=material_id,
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
        logger.bind(event="agent.tool.arguments_edited", tool_name="update_material").info(
            "Using user-edited tool arguments: fields={}", sorted(approved)
        )
        data.update(_compact_update_payload(approved, "material_id"))
    data = _compact_update_payload(data, "material_id")
    result = await backend_client.update_material(
        token=token,
        material_id=material_id,
        data=data,
        extra_headers=_get_backend_headers(ctx, "update_material", {"material_id": material_id, **data}),
    )
    return await verify_fields(
        result,
        lambda: backend_client.get_material(token, material_id),
        data,
        entity_id=material_id,
    )


@mcp.tool()
async def add_material_to_project(ctx: Context, material_id: str, project_id: str) -> dict:
    """把素材添加到项目。"""
    token = _get_token(ctx)
    args = {"material_id": material_id, "project_id": project_id}
    result = await backend_client.add_material_to_project(
        token=token,
        material_id=material_id,
        project_id=project_id,
        extra_headers=_get_backend_headers(ctx, "add_material_to_project", args),
    )
    return await verify_collection_membership(
        result,
        lambda: backend_client.get_material(token, material_id),
        collection_key="project_ids",
        entity_id=project_id,
        should_exist=True,
    )


@mcp.tool()
async def remove_material_from_project(ctx: Context, material_id: str, project_id: str) -> dict:
    """从项目移除素材。"""
    token = _get_token(ctx)
    args = {"material_id": material_id, "project_id": project_id}
    result = await backend_client.remove_material_from_project(
        token=token,
        material_id=material_id,
        project_id=project_id,
        extra_headers=_get_backend_headers(ctx, "remove_material_from_project", args),
    )
    return await verify_collection_membership(
        result,
        lambda: backend_client.get_material(token, material_id),
        collection_key="project_ids",
        entity_id=project_id,
        should_exist=False,
    )


@mcp.tool()
async def delete_material(ctx: Context, material_id: str) -> dict:
    """删除指定素材。"""
    token = _get_token(ctx)
    result = await backend_client.delete_material(
        token=token,
        material_id=material_id,
        extra_headers=_get_backend_headers(ctx, "delete_material", {"material_id": material_id}),
    )
    return await verify_absent(
        result,
        lambda: backend_client.get_material(token, material_id),
        entity_id=material_id,
    )


