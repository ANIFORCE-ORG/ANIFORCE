"""Conservative deterministic preselection for obvious business intents.

This avoids changing the provider-visible MCP tool set mid-Responses run for
clear tasks. Ambiguous tasks still use the progressive loader tool.
"""

import re

from app.agent.business_skills.loader_tool import load_skill_into_context
from app.agent.workspace_context import WorkspaceRunContext


MUTATION_RE = re.compile(
    r"(创建|新建|删除|暂停|恢复投放|上线|下线|关联|解绑|移除|"
    r"(?:把|将).{0,30}(?:改成|修改为|调整为|换到|放到))"
)
def preselect_business_skill(context: WorkspaceRunContext, user_input: str) -> str | None:
    normalized = " ".join(str(user_input or "").split())
    skill_name = None
    if MUTATION_RE.search(normalized):
        skill_name = "safe_business_mutation"
    current = context.selected_skill_ids[0] if context.selected_skill_ids else None
    if not skill_name:
        return current
    if current and current != skill_name:
        context.selected_skill_ids.clear()
        context.selected_skill_versions.clear()
        context.skill_slots.clear()
        context.skill_missing_slots.clear()
        context.skill_pending_question = None
        context.skill_status = None
    if not context.selected_skill_ids:
        load_skill_into_context(context, skill_name, "deterministic_intent_match")
    return skill_name
