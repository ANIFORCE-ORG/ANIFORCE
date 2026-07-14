import json

import pytest

from app.agent.projections.workspace_artifact import WorkspaceArtifactProjection


class ArtifactRepositorySpy:
    def __init__(self) -> None:
        self.created: list[dict] = []

    async def create_projection(self, **kwargs) -> dict:
        self.created.append(kwargs)
        return kwargs


def tool_called(call_id: str, tool_name: str) -> tuple[str, dict]:
    return (
        "run_item_stream_event",
        {
            "type": "run_item_stream_event",
            "name": "tool_called",
            "item": {"call_id": call_id, "tool_name": tool_name, "raw_item": {}},
        },
    )


def tool_output(call_id: str, output: object) -> tuple[str, dict]:
    return (
        "run_item_stream_event",
        {
            "type": "run_item_stream_event",
            "name": "tool_output",
            "item": {"call_id": call_id, "output": output, "raw_item": {}},
        },
    )


@pytest.mark.anyio
async def test_projection_request_persists_preceding_campaign_result() -> None:
    repository = ArtifactRepositorySpy()
    events = [
        tool_called("call_query", "list_campaigns"),
        tool_output("call_query", json.dumps({"campaigns": [{"id": "c1", "name": "Android test"}]})),
        tool_called("call_projection", "request_workspace_projection"),
        tool_output(
            "call_projection",
            json.dumps({"accepted": True, "surface": "campaign.list", "reason": "show campaigns"}),
        ),
    ]

    await WorkspaceArtifactProjection(repository).project(
        run_id="run_1",
        session_id="session_1",
        events=events,
    )

    assert repository.created == [
        {
            "session_id": "session_1",
            "run_id": "run_1",
            "source_tool_call_id": "call_query",
            "surface": "campaign.list",
            "payload": {"campaigns": [{"id": "c1", "name": "Android test"}]},
        }
    ]


@pytest.mark.anyio
async def test_projection_request_without_matching_query_is_not_persisted() -> None:
    repository = ArtifactRepositorySpy()
    events = [
        tool_called("call_projection", "request_workspace_projection"),
        tool_output(
            "call_projection",
            json.dumps({"accepted": True, "surface": "campaign.list"}),
        ),
    ]

    await WorkspaceArtifactProjection(repository).project(
        run_id="run_1",
        session_id="session_1",
        events=events,
    )

    assert repository.created == []


@pytest.mark.anyio
async def test_explicit_projection_event_remains_supported() -> None:
    repository = ArtifactRepositorySpy()

    await WorkspaceArtifactProjection(repository).project(
        run_id="run_1",
        session_id="session_1",
        events=[("workspace.projection", {"surface": "project.list", "projects": []})],
    )

    assert repository.created[0]["surface"] == "project.list"
