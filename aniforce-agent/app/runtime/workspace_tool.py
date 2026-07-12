"""Runtime-local tool for requesting a durable Workspace projection."""

import json
from typing import Annotated

from agents import RunContextWrapper, function_tool

from app.agent.workspace_context import WorkspaceRunContext


@function_tool
async def request_workspace_projection(
    ctx: RunContextWrapper[WorkspaceRunContext],
    surface: Annotated[str, "必须匹配刚刚查询结果的 Workspace surface：project.list、project.detail、campaign.list、campaign.detail、campaign.materials、material.list、material.detail、material.image"],
    reason: Annotated[str, "为什么用户需要在右侧 Workspace 查看这个结果"],
) -> str:
    """请求把刚刚查询到的业务结果展示到右侧 Workspace。

    浏览、查看、列出、打开业务对象时，在完成对应查询工具后必须调用本工具。
    surface 映射：
    - 项目：list_projects -> project.list, get_project_detail -> project.detail
    - 广告计划：list_campaigns -> campaign.list, get_campaign_detail -> campaign.detail, get_campaign_materials -> campaign.materials
    - 素材：list_materials -> material.list, get_material_detail -> material.detail, get_material_image -> material.image, list_available_images -> material.list

    当前没有 task 专用 surface；任务/执行状态类问题不要调用本工具。
    分析、诊断、对比、多上下文任务不要调用本工具，除非用户明确要求把某个结果放到右侧查看。
    审批类操作（包括关联/解绑）会自动投影，不需要调用本工具。
    """
    allowed_surfaces = {"project.list", "project.detail", "campaign.list", "campaign.detail", "campaign.materials", "material.list", "material.detail", "material.image"}
    if surface not in allowed_surfaces:
        return json.dumps(
            {"accepted": False, "surface": surface, "reason": "unsupported_surface", "message": "当前 Workspace 不支持该投影类型。"},
            ensure_ascii=False,
        )
    request = {"surface": surface, "reason": reason, "run_id": ctx.context.run_id, "session_id": ctx.context.session_id}
    ctx.context.workspace_projection_requests.append(request)
    return json.dumps({"accepted": True, **request}, ensure_ascii=False)
