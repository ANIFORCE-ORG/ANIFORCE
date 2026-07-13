"""Build minimal business context summary for Agent runs."""

from typing import Any

from app.repositories.protocols import CampaignRepository, MaterialRepository, ProjectRepository


class BusinessContextBuilder:
    """Builds a compact, text-first business context for agent-service."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        campaign_repo: CampaignRepository,
        material_repo: MaterialRepository,
    ) -> None:
        self.project_repo = project_repo
        self.campaign_repo = campaign_repo
        self.material_repo = material_repo

    async def build(self, session_state: dict, user_id: str) -> str:
        linked_entities = session_state.get("linked_entities") or {}
        ui_snapshot = session_state.get("ui_snapshot") or {}
        selected_entities = ui_snapshot.get("selectedEntities") or []
        lines = ["当前业务现场："]
        lines.append(f"- 当前会话模式：{session_state.get('mode', 'general')}")

        selected_project_ids = self._selected_ids(selected_entities, "project")
        selected_campaign_ids = self._selected_ids(selected_entities, "campaign")
        selected_material_ids = self._selected_ids(selected_entities, "material")
        project_id = ui_snapshot.get("activeProjectId") or (selected_project_ids[0] if len(selected_project_ids) == 1 else None) or linked_entities.get("project_id")
        if project_id:
            project = await self.project_repo.get_by_id(project_id)
            if project and project.get("user_id") == user_id:
                lines.append(
                    "- 当前项目："
                    f"{project.get('name')}，类型 {project.get('game_type') or '未知'}，"
                    f"总预算 ¥{project.get('total_budget', 0):,.0f}，状态 {project.get('status')}"
                )
            else:
                lines.append(f"- 当前项目引用：{project_id}（未找到或无权限）")
        else:
            lines.append("- 当前未绑定具体项目")

        active_campaign_id = ui_snapshot.get("activeCampaignId")
        campaign_ids = self._ordered_unique([
            *([active_campaign_id] if active_campaign_id else []),
            *selected_campaign_ids,
            *(linked_entities.get("campaign_ids") or []),
        ])
        campaigns = []
        for campaign_id in campaign_ids[:10]:
            campaign = await self.campaign_repo.get_by_id(campaign_id)
            if campaign and await self._campaign_belongs_to_user(campaign, user_id):
                campaigns.append(campaign)
        if campaigns:
            lines.append(f"- 关联广告计划：{len(campaigns)} 个")
            for campaign in campaigns:
                lines.append(
                    "  · "
                    f"{campaign.get('name')}：{campaign.get('platform')}，"
                    f"预算 ¥{campaign.get('budget', 0):,.0f}，状态 {campaign.get('status')}"
                )

        material_ids = self._ordered_unique([
            *selected_material_ids,
            *(linked_entities.get("material_ids") or []),
        ])
        visible_materials = []
        for material_id in material_ids[:10]:
            material = await self.material_repo.get_by_id(material_id)
            if material and material.get("user_id") == user_id:
                visible_materials.append(material)
        if visible_materials:
            lines.append(f"- 关联素材：{len(visible_materials)} 个")
            for material in visible_materials:
                lines.append(f"  · {material.get('name')}（ID: {material.get('id')}）")

        if selected_entities:
            lines.append("- 本轮用户在 Workspace 显式选中了业务对象；以上经过权限校验的选中对象优先于历史会话引用")

        summary = session_state.get("summary") or ""
        if summary:
            lines.append(f"- 会话摘要：{summary}")

        changelog = session_state.get("changelog") or []
        if changelog:
            lines.append("- 最近变更：")
            for item in changelog[-5:]:
                entity_type = item.get("entity_type") or "entity"
                action = item.get("action") or "changed"
                entity_id = item.get("entity_id") or "unknown"
                lines.append(f"  · {entity_type} {entity_id} {action}")

        pending_actions = session_state.get("pending_actions") or []
        if pending_actions:
            lines.append(f"- 待确认动作：{len(pending_actions)} 项")

        if ui_snapshot:
            route = ui_snapshot.get("route")
            active_panel = ui_snapshot.get("activePanel") or ui_snapshot.get("active_panel")
            if route:
                lines.append(f"- 用户当前页面：{route}")
            if active_panel:
                lines.append(f"- 当前面板：{active_panel}")

        lines.extend(
            [
                "",
                "约束：",
                "- backend DB 是业务事实源，不要把聊天历史当作业务事实。",
                "- 写操作必须通过 MCP 工具调用 backend REST 完成。",
                "- 预算、上线、删除等高风险操作需要用户确认。",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _selected_ids(selected_entities: list[Any], entity_type: str) -> list[str]:
        return [
            str(item["id"])
            for item in selected_entities
            if isinstance(item, dict) and item.get("type") == entity_type and item.get("id")
        ]

    @staticmethod
    def _ordered_unique(values: list[Any]) -> list[str]:
        return list(dict.fromkeys(str(value) for value in values if value))

    async def _campaign_belongs_to_user(self, campaign: dict, user_id: str) -> bool:
        project_id = campaign.get("project_id")
        if not project_id:
            return False
        project = await self.project_repo.get_by_id(str(project_id))
        return bool(project and project.get("user_id") == user_id)

    def build_general_context(self, ui_snapshot: dict[str, Any] | None = None) -> str:
        lines = ["当前业务现场：", "- 当前未绑定具体项目", "- 用户可能是在闲聊、查询、体验或准备开始任务"]
        if ui_snapshot:
            route = ui_snapshot.get("route")
            active_panel = ui_snapshot.get("activePanel") or ui_snapshot.get("active_panel")
            if route:
                lines.append(f"- 用户当前页面：{route}")
            if active_panel:
                lines.append(f"- 当前面板：{active_panel}")
        lines.extend(
            [
                "",
                "约束：",
                "- 可以先回答问题或澄清目标，不要强制进入结构化任务。",
                "- 如需修改业务数据，必须通过 backend 工具并遵守权限和确认规则。",
            ]
        )
        return "\n".join(lines)
