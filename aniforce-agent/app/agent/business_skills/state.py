"""Run-local and cross-run state helpers for business skills."""

from __future__ import annotations

from typing import Any

from app.agent.business_skills.registry import business_skill_registry
from app.agent.workspace_context import WorkspaceRunContext


RESTORABLE_STATUSES = frozenset({"selected", "collecting_inputs", "ready", "executing"})


def restore_business_skill_state(context: WorkspaceRunContext) -> None:
    task_state = context.session_state.get("task_state") or {}
    active = task_state.get("active_skill") if isinstance(task_state, dict) else None
    if not isinstance(active, dict) or active.get("status") not in RESTORABLE_STATUSES:
        return
    skill = business_skill_registry.get(str(active.get("name") or ""))
    version = str(active.get("version") or "")
    if not skill or skill.version != version:
        return
    context.selected_skill_ids = [skill.name]
    context.selected_skill_versions = {skill.name: skill.version}
    context.skill_slots = dict(active.get("slots") or {})
    context.skill_load_reason = str(active.get("load_reason") or "continued_session_task")[:80]
    context.skill_status = str(active.get("status") or "selected")
    context.skill_missing_slots = [str(item) for item in (active.get("missing_slots") or [])]
    context.skill_pending_question = str(active.get("pending_question") or "")[:500] or None
    seed_skill_slots_from_workspace(context, skill.name)


def seed_skill_slots_from_workspace(context: WorkspaceRunContext, skill_name: str) -> None:
    snapshot = context.ui_snapshot or {}
    selected = snapshot.get("selectedEntities") or []
    selected_by_type: dict[str, list[str]] = {}
    for item in selected:
        if isinstance(item, dict) and item.get("type") and item.get("id"):
            selected_by_type.setdefault(str(item["type"]), []).append(str(item["id"]))
    project_id = snapshot.get("activeProjectId")
    campaign_id = snapshot.get("activeCampaignId")
    if not project_id and len(selected_by_type.get("project", [])) == 1:
        project_id = selected_by_type["project"][0]
    if not campaign_id and len(selected_by_type.get("campaign", [])) == 1:
        campaign_id = selected_by_type["campaign"][0]
    if project_id:
        context.skill_slots.setdefault("project_id", str(project_id))
    if campaign_id:
        context.skill_slots.setdefault("campaign_id", str(campaign_id))
    if len(selected_by_type.get("material", [])) == 1:
        context.skill_slots.setdefault("material_id", selected_by_type["material"][0])
    if skill_name in {"campaign_diagnosis", "project_review"}:
        context.skill_slots.setdefault("time_range_hours", 168)


def skill_trace_metadata(context: WorkspaceRunContext) -> dict[str, Any]:
    return {
        "skill_names": list(context.selected_skill_ids),
        "skill_versions": dict(context.selected_skill_versions),
        "skill_load_reason": context.skill_load_reason,
        "skill_status": context.skill_status,
    }


def build_task_state(
    context: WorkspaceRunContext,
    *,
    terminal_status: str | None = None,
) -> dict[str, Any]:
    previous = context.session_state.get("task_state") or {}
    result: dict[str, Any] = {
        key: value for key, value in previous.items()
        if key in {"confirmed_entities", "constraints", "last_conclusion"}
    }
    if not context.selected_skill_ids:
        return result
    skill_name = context.selected_skill_ids[0]
    skill = business_skill_registry.get(skill_name)
    version = context.selected_skill_versions.get(skill_name)
    if not skill or version != skill.version:
        result["active_skill"] = {
            "name": skill_name,
            "version": version or "unknown",
            "status": "failed",
            "slots": dict(context.skill_slots),
            "missing_slots": [],
            "load_reason": context.skill_load_reason,
            "pending_question": None,
        }
        return result
    missing = context.skill_missing_slots or [
        slot for slot in skill.required_slots if not context.skill_slots.get(slot)
    ]
    status = terminal_status or context.skill_status or ("collecting_inputs" if missing else "ready")
    result["active_skill"] = {
        "name": skill.name,
        "version": skill.version,
        "status": status,
        "slots": dict(context.skill_slots),
        "missing_slots": missing,
        "load_reason": context.skill_load_reason,
        "pending_question": context.skill_pending_question,
    }
    confirmed = dict(result.get("confirmed_entities") or {})
    for key in ("project_id", "campaign_id", "material_id"):
        if context.skill_slots.get(key):
            confirmed[key.removesuffix("_id")] = context.skill_slots[key]
    if confirmed:
        result["confirmed_entities"] = confirmed
    return result
