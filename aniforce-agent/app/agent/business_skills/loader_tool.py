"""Stable local tool used to progressively load business decision contracts."""

import json
from typing import Annotated, Literal

from agents import RunContextWrapper, function_tool
from loguru import logger

from app.agent.business_skills.registry import business_skill_registry
from app.agent.business_skills.state import seed_skill_slots_from_workspace
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
    seed_skill_slots_from_workspace(context, skill.name)
    context.skill_missing_slots = [
        slot for slot in skill.required_slots if not context.skill_slots.get(slot)
    ]
    context.skill_status = "collecting_inputs" if context.skill_missing_slots else "ready"
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        span.set_attribute("aniforce.skill.name", skill.name)
        span.set_attribute("aniforce.skill.version", skill.version)
        span.set_attribute("aniforce.skill.status", context.skill_status or "selected")
    except Exception:
        pass
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


def update_skill_state_in_context(
    context: WorkspaceRunContext,
    status: str,
    slots_json: str,
    missing_slots: list[str] | None,
    pending_question: str | None,
) -> dict:
    if not context.selected_skill_ids:
        return {"updated": False, "code": "BUSINESS_SKILL_NOT_LOADED"}
    try:
        slots = json.loads(slots_json or "{}")
    except json.JSONDecodeError:
        return {"updated": False, "code": "INVALID_SKILL_SLOTS_JSON"}
    if not isinstance(slots, dict):
        return {"updated": False, "code": "INVALID_SKILL_SLOTS"}
    context.skill_slots.update({str(key)[:80]: value for key, value in list(slots.items())[:30]})
    context.skill_status = status
    context.skill_missing_slots = [str(item)[:80] for item in (missing_slots or [])[:20]]
    context.skill_pending_question = (pending_question or "").strip()[:500] or None
    return {
        "updated": True,
        "skill_name": context.selected_skill_ids[0],
        "status": status,
        "slots": context.skill_slots,
        "missing_slots": list(missing_slots or []),
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


@function_tool(timeout=3.0, timeout_behavior="error_as_result")
async def update_business_skill_state(
    ctx: RunContextWrapper[WorkspaceRunContext],
    status: Annotated[Literal["collecting_inputs", "ready", "executing"], "当前 Skill 阶段"],
    slots_json: Annotated[str, "已确认槽位的 JSON 对象，例如 {\"campaign_id\":\"c1\",\"time_range_hours\":168}"],
    missing_slots: Annotated[list[str] | None, "仍缺少的必要槽位"] = None,
    pending_question: Annotated[str | None, "准备向用户提出的一个必要问题"] = None,
) -> str:
    """在追问或确认对象后更新当前 Business Skill 的结构化任务状态。

    只保存对象 ID、时间范围和必要约束，不保存用户完整原文、Token、密钥或工具结果。
    """
    result = update_skill_state_in_context(
        ctx.context, status, slots_json, missing_slots, pending_question
    )
    return json.dumps(result, ensure_ascii=False)
