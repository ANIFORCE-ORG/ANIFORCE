"""Build simplified side_effect events from Session State changelog."""

from app.models.side_effect import SideEffect


class SideEffectService:
    """Converts changelog entries into frontend projection events."""

    def from_changelog_entries(self, entries: list[dict]) -> list[SideEffect]:
        events: list[SideEffect] = []
        for entry in entries:
            event = self.from_changelog_entry(entry)
            if event:
                events.append(event)
        return events

    def from_changelog_entry(self, entry: dict) -> SideEffect | None:
        entity_type = entry.get("entity_type")
        action = entry.get("action") or "changed"
        entity_id = entry.get("entity_id")
        new_value = entry.get("new_value") or {}
        name = new_value.get("name") if isinstance(new_value, dict) else None

        if entity_type == "project":
            return SideEffect(
                type="entity_changed",
                domain="project",
                action=action,
                message=self._message("项目", name, action),
                affected_entities=[{"type": "project", "id": entity_id, "name": name}],
                refresh_panels=["context"],
            )

        if entity_type == "campaign":
            return SideEffect(
                type="entity_changed",
                domain="campaign",
                action=action,
                message=self._message("广告计划", name, action),
                affected_entities=[{"type": "campaign", "id": entity_id, "name": name}],
                refresh_panels=["context", "budget"] if entry.get("field") == "budget" else ["context"],
            )

        if entity_type == "material":
            return SideEffect(
                type="content_ready" if action in {"created", "generated"} else "entity_changed",
                domain="material",
                action=action,
                message=self._message("素材", name, action),
                affected_entities=[{"type": "material", "id": entity_id, "name": name}],
                refresh_panels=["creative"],
            )

        return None

    def _message(self, label: str, name: str | None, action: str) -> str:
        action_text = {
            "created": "已创建",
            "updated": "已更新",
            "deleted": "已删除",
            "changed": "已变更",
        }.get(action, "已变更")
        if name:
            return f"{action_text}{label}「{name}」"
        return f"{action_text}{label}"
