"""Read-only validated registry for ANIFORCE business skills."""

from collections.abc import Iterable

from app.agent.business_skills.definitions import BUSINESS_SKILLS
from app.agent.business_skills.models import BusinessSkill


MCP_TOOL_NAMES = frozenset({
    "list_projects", "get_project_detail", "get_project_performance", "create_project", "update_project", "delete_project",
    "list_campaigns", "get_campaign_detail", "get_campaign_performance", "create_campaign", "update_campaign",
    "update_campaign_status", "get_campaign_materials", "add_material_to_campaign", "remove_material_from_campaign", "delete_campaign",
    "list_materials", "create_material", "get_material_detail", "get_material_image", "list_available_images", "update_material",
    "add_material_to_project", "remove_material_from_project", "delete_material",
})


class BusinessSkillRegistry:
    def __init__(self, skills: Iterable[BusinessSkill] = BUSINESS_SKILLS) -> None:
        items = tuple(skills)
        self._validate(items)
        self._skills = {skill.name: skill for skill in items}

    @staticmethod
    def _validate(skills: tuple[BusinessSkill, ...]) -> None:
        names: set[str] = set()
        for skill in skills:
            if not skill.name or skill.name in names:
                raise ValueError(f"Duplicate or empty business skill name: {skill.name}")
            names.add(skill.name)
            if not skill.version or not skill.description or not skill.workflow or not skill.response_contract:
                raise ValueError(f"Incomplete business skill: {skill.name}")
            unknown = skill.allowed_tools - MCP_TOOL_NAMES
            if unknown:
                raise ValueError(f"Business skill {skill.name} references unknown tools: {sorted(unknown)}")

    def get(self, name: str) -> BusinessSkill | None:
        return self._skills.get(name)

    def require(self, name: str) -> BusinessSkill:
        skill = self.get(name)
        if skill is None:
            raise KeyError(name)
        return skill

    def list(self) -> tuple[BusinessSkill, ...]:
        return tuple(self._skills.values())

    def render_index(self) -> str:
        return "\n".join(f"- `{skill.name}` v{skill.version}：{skill.description}" for skill in self.list())


business_skill_registry = BusinessSkillRegistry()
