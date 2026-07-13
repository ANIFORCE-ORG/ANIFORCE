"""Stable local tool used to progressively load business decision contracts."""

import json
from typing import Annotated

from agents import RunContextWrapper, function_tool
from loguru import logger

from app.agent.business_skills.registry import business_skill_registry
from app.agent.workspace_context import WorkspaceRunContext


MAX_SELECTED_SKILLS = 2


def load_skill_into_context(context: WorkspaceRunContext, skill_name: str, reason: str) -> dict:
    skill = business_skill_registry.get(skill_name)
    if skill is None:
        return {
            "loaded": False,
            "code": "UNKNOWN_BUSINESS_SKILL",
            "message": "Unknown business skill; continue with base behavior or clarify the task.",
        }
    if skill_name in context.selected_skill_ids:
        return {
            "loaded": True,
            "already_loaded": True,
            "skill_name": skill.name,
            "version": skill.version,
        }
    if len(context.selected_skill_ids) >= MAX_SELECTED_SKILLS:
        return {
            "loaded": False,
            "code": "BUSINESS_SKILL_LIMIT",
            "message": f"At most {MAX_SELECTED_SKILLS} business skills may be loaded for one run.",
        }
    context.selected_skill_ids.append(skill.name)
    context.selected_skill_versions[skill.name] = skill.version
    context.skill_load_reason = reason.strip()[:80] or "matched_user_intent"
    logger.bind(
        event="agent.skill.loaded",
        skill_name=skill.name,
        skill_version=skill.version,
        run_id=context.run_id,
        session_id=context.session_id,
    ).info("Business skill loaded")
    return {
        "loaded": True,
        "already_loaded": False,
        "skill_name": skill.name,
        "version": skill.version,
        "required_slots": list(skill.required_slots),
    }


@function_tool(timeout=3.0, timeout_behavior="error_as_result")
async def load_business_skill(
    ctx: RunContextWrapper[WorkspaceRunContext],
    skill_name: Annotated[str, "要加载的业务 Skill 名称，必须来自 System Prompt 的 Business Skill Index"],
    reason: Annotated[str, "简短选择原因，例如 matched_user_intent、continued_session_task"],
) -> str:
    """按当前任务加载一个 Business Skill 决策合同。

    当用户任务明确匹配 Business Skill Index 时先调用本工具。加载后下一轮会注入完整合同并裁剪可见 MCP 工具。
    普通闲聊或简单展示查询不需要加载 Skill。
    """
    result = load_skill_into_context(ctx.context, skill_name, reason)
    return json.dumps(result, ensure_ascii=False)
