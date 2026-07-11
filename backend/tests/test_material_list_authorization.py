from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.api.v1.materials import list_materials


class FakeMaterialRepo:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    async def list_by_project(self, project_id: str, limit: int = 50) -> list[dict]:
        self.calls.append(("project", project_id, limit))
        return [{"id": "material-1"}]

    async def list_by_campaign(self, campaign_id: str, limit: int = 50) -> list[dict]:
        self.calls.append(("campaign", campaign_id, limit))
        return [{"id": "material-1"}]

    async def list_by_user(self, user_id: str, type: str | None = None, limit: int = 50) -> list[dict]:
        self.calls.append(("user", user_id, limit))
        return []


class FakeProjectRepo:
    def __init__(self, projects: dict[str, dict]) -> None:
        self.projects = projects

    async def get_by_id(self, project_id: str) -> dict | None:
        return self.projects.get(project_id)


class FakeCampaignRepo:
    def __init__(self, campaigns: dict[str, dict]) -> None:
        self.campaigns = campaigns

    async def get_by_id(self, campaign_id: str) -> dict | None:
        return self.campaigns.get(campaign_id)


def test_project_material_list_rejects_non_owner_before_query() -> None:
    async def scenario() -> None:
        materials = FakeMaterialRepo()

        with pytest.raises(HTTPException) as exc_info:
            await list_materials(
                project_id="project-owner",
                campaign_id=None,
                type=None,
                limit=50,
                current_user={"id": "other-user"},
                material_repo=materials,
                project_repo=FakeProjectRepo({"project-owner": {"id": "project-owner", "user_id": "owner"}}),
                campaign_repo=FakeCampaignRepo({}),
            )

        assert exc_info.value.status_code == 403
        assert materials.calls == []

    asyncio.run(scenario())


def test_campaign_material_list_rejects_non_owner_before_query() -> None:
    async def scenario() -> None:
        materials = FakeMaterialRepo()

        with pytest.raises(HTTPException) as exc_info:
            await list_materials(
                project_id=None,
                campaign_id="campaign-owner",
                type=None,
                limit=50,
                current_user={"id": "other-user"},
                material_repo=materials,
                project_repo=FakeProjectRepo({"project-owner": {"id": "project-owner", "user_id": "owner"}}),
                campaign_repo=FakeCampaignRepo({"campaign-owner": {"id": "campaign-owner", "project_id": "project-owner"}}),
            )

        assert exc_info.value.status_code == 403
        assert materials.calls == []

    asyncio.run(scenario())


def test_project_material_list_allows_owner() -> None:
    async def scenario() -> None:
        materials = FakeMaterialRepo()

        result = await list_materials(
            project_id="project-owner",
            campaign_id=None,
            type=None,
            limit=25,
            current_user={"id": "owner"},
            material_repo=materials,
            project_repo=FakeProjectRepo({"project-owner": {"id": "project-owner", "user_id": "owner"}}),
            campaign_repo=FakeCampaignRepo({}),
        )

        assert result == {"materials": [{"id": "material-1"}]}
        assert materials.calls == [("project", "project-owner", 25)]

    asyncio.run(scenario())
