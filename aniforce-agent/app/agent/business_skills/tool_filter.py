"""Per-run MCP tool visibility for business skills."""

from app.agent.business_skills.registry import business_skill_registry
from app.config.settings import get_settings


BASE_READ_TOOLS = frozenset({
    "list_projects",
    "get_project_detail",
    "get_project_performance",
    "list_campaigns",
    "get_campaign_detail",
    "get_campaign_performance",
    "get_campaign_materials",
    "list_materials",
    "get_material_detail",
    "get_material_image",
    "list_available_images",
})


def allowed_mcp_tools(context) -> frozenset[str] | None:
    """Return None for legacy all-tools mode, otherwise a per-run allowlist."""
    if not get_settings().ENABLE_BUSINESS_SKILLS:
        return None
    selected = list(getattr(context, "selected_skill_ids", []) or [])
    if not selected:
        return BASE_READ_TOOLS
    allowed = set(BASE_READ_TOOLS)
    for skill_name in selected:
        skill = business_skill_registry.get(skill_name)
        selected_version = (getattr(context, "selected_skill_versions", {}) or {}).get(skill_name)
        if skill and selected_version == skill.version:
            allowed.update(skill.allowed_tools)
    return frozenset(allowed)


def business_skill_tool_filter(filter_context, tool) -> bool:
    """Stable Agents SDK MCP filter; state comes only from this RunContext."""
    run_context = filter_context.run_context.context
    allowed = allowed_mcp_tools(run_context)
    return True if allowed is None else tool.name in allowed
