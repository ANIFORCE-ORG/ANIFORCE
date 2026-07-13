import asyncio

from app.agent.sessions.business_context import BusinessContextBuilder


class ProjectRepo:
    def __init__(self):
        self.items = {
            "p-history": {"id": "p-history", "user_id": "u1", "name": "历史项目", "total_budget": 1, "status": "active"},
            "p-current": {"id": "p-current", "user_id": "u1", "name": "当前项目", "total_budget": 2, "status": "active"},
            "p-other": {"id": "p-other", "user_id": "u2", "name": "他人项目", "total_budget": 3, "status": "active"},
        }

    async def get_by_id(self, item_id):
        return self.items.get(item_id)


class CampaignRepo:
    def __init__(self):
        self.items = {
            "c-current": {"id": "c-current", "project_id": "p-current", "name": "当前计划", "platform": "Meta", "budget": 10, "status": "running"},
            "c-other": {"id": "c-other", "project_id": "p-other", "name": "他人计划", "platform": "Meta", "budget": 10, "status": "running"},
        }

    async def get_by_id(self, item_id):
        return self.items.get(item_id)


class MaterialRepo:
    def __init__(self):
        self.items = {
            "m-current": {"id": "m-current", "user_id": "u1", "name": "当前素材"},
            "m-other": {"id": "m-other", "user_id": "u2", "name": "他人素材"},
        }

    async def get_by_id(self, item_id):
        return self.items.get(item_id)


def builder():
    return BusinessContextBuilder(ProjectRepo(), CampaignRepo(), MaterialRepo())


def test_current_workspace_selection_precedes_historical_links():
    summary = asyncio.run(builder().build(
        {
            "mode": "general",
            "linked_entities": {"project_id": "p-history"},
            "ui_snapshot": {
                "selectedEntities": [
                    {"type": "project", "id": "p-current"},
                    {"type": "campaign", "id": "c-current"},
                    {"type": "material", "id": "m-current"},
                ]
            },
        },
        "u1",
    ))

    assert "当前项目" in summary
    assert "历史项目" not in summary
    assert "当前计划" in summary
    assert "当前素材" in summary
    assert "显式选中" in summary


def test_multiple_selected_projects_do_not_pick_an_arbitrary_project():
    summary = asyncio.run(builder().build(
        {
            "linked_entities": {},
            "ui_snapshot": {
                "selectedEntities": [
                    {"type": "project", "id": "p-history"},
                    {"type": "project", "id": "p-current"},
                ]
            },
        },
        "u1",
    ))

    assert "当前未绑定具体项目" in summary
    assert "历史项目" not in summary
    assert "当前项目" not in summary


def test_unauthorized_selected_entities_are_not_injected():
    summary = asyncio.run(builder().build(
        {
            "linked_entities": {},
            "ui_snapshot": {
                "activeProjectId": "p-other",
                "selectedEntities": [
                    {"type": "campaign", "id": "c-other"},
                    {"type": "material", "id": "m-other"},
                ],
            },
        },
        "u1",
    ))

    assert "未找到或无权限" in summary
    assert "他人计划" not in summary
    assert "他人素材" not in summary
