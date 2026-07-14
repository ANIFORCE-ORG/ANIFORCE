"""Project normalized Workspace requests into durable Artifact facts."""

from __future__ import annotations

import json
from typing import Any

from app.agent.messages.assembler import ChatEventAssembler
from app.repositories.impl.sqlite_agent_fact_repo import SqliteAgentArtifactRepository


_TOOL_SURFACES = {
    "list_projects": "project.list",
    "get_project_detail": "project.detail",
    "list_campaigns": "campaign.list",
    "get_campaign_detail": "campaign.detail",
    "get_campaign_materials": "campaign.materials",
    "list_materials": "material.list",
    "get_material_detail": "material.detail",
    "get_material_image": "material.image",
    "list_available_images": "material.list",
}


class WorkspaceArtifactProjection:
    def __init__(self, repository: SqliteAgentArtifactRepository) -> None:
        self._repository = repository
        self._assembler = ChatEventAssembler()

    async def project(
        self,
        *,
        run_id: str,
        session_id: str,
        events: list[tuple[str, dict]],
    ) -> None:
        tool_names: dict[str, str] = {}
        latest_results: dict[str, tuple[str, str, Any]] = {}

        for event_name, data in events:
            if event_name == "workspace.projection" and isinstance(data, dict):
                await self._create(run_id, session_id, data)
                continue
            if event_name != "run_item_stream_event":
                continue

            item = data.get("item") if isinstance(data.get("item"), dict) else {}
            if data.get("name") == "tool_called":
                call_id, tool_name, _ = self._assembler._tool_call_info(item)
                if call_id:
                    tool_names[call_id] = tool_name
                continue
            if data.get("name") != "tool_output":
                continue

            call_id, result = self._assembler._tool_output_info(item)
            tool_name = tool_names.get(call_id, "")
            surface = _TOOL_SURFACES.get(tool_name)
            if surface:
                latest_results[surface] = (call_id, tool_name, result)
                continue
            if tool_name != "request_workspace_projection":
                continue

            request = _json_object(result)
            requested_surface = str(request.get("surface") or "")
            if request.get("accepted") is not True or requested_surface not in latest_results:
                continue
            source_tool_call_id, source_tool_name, query_result = latest_results[requested_surface]
            await self._repository.create_projection(
                session_id=session_id,
                run_id=run_id,
                source_tool_call_id=source_tool_call_id or None,
                surface=requested_surface,
                payload=_workspace_payload(requested_surface, source_tool_name, query_result),
            )

    async def _create(self, run_id: str, session_id: str, request: dict) -> None:
        await self._repository.create_projection(
            session_id=session_id,
            run_id=run_id,
            source_tool_call_id=request.get("tool_call_id"),
            surface=str(request.get("surface") or "unknown"),
            payload=request,
        )


def _json_value(value: Any) -> Any:
    parsed = value
    for _ in range(8):
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
                continue
            except (TypeError, ValueError):
                return parsed
        if isinstance(parsed, list):
            if len(parsed) == 1:
                parsed = parsed[0]
                continue
            text_parts = [
                item.get("text") or item.get("content")
                for item in parsed
                if isinstance(item, dict)
            ]
            if len(text_parts) == len(parsed) and all(isinstance(item, str) for item in text_parts):
                parsed = "\n".join(text_parts)
                continue
            break
        if not isinstance(parsed, dict) or _is_business_record(parsed):
            break
        unwrapped = None
        for key in ("text", "content", "output", "details", "payload", "result"):
            candidate = parsed.get(key)
            if isinstance(candidate, (dict, list, str)):
                unwrapped = candidate
                break
        if unwrapped is None:
            break
        parsed = unwrapped
    return parsed


def _json_object(value: Any) -> dict[str, Any]:
    parsed = _json_value(value)
    return parsed if isinstance(parsed, dict) else {}


def _workspace_payload(surface: str, tool_name: str, result: Any) -> dict[str, Any]:
    parsed = _json_value(result)
    if surface == "project.list":
        return _collection_payload(parsed, "projects")
    if surface == "campaign.list":
        return _collection_payload(parsed, "campaigns")
    if surface in {"material.list", "campaign.materials"}:
        if tool_name == "list_available_images":
            return {"materials": _local_file_materials(_find_collection(parsed, ("files", "images", "items", "list", "data")))}
        return _collection_payload(parsed, "materials")
    if surface == "project.detail":
        return {"project": _first_record(parsed, ("project",))}
    if surface == "campaign.detail":
        return {"campaign": _first_record(parsed, ("campaign",))}
    if surface == "material.detail":
        return {"material": _first_record(parsed, ("material",))}
    if surface == "material.image":
        return {"image": _first_record(parsed, ("image",)) or (parsed if isinstance(parsed, dict) else {"data": parsed})}
    return parsed if isinstance(parsed, dict) else {"data": parsed}


def _collection_payload(value: Any, key: str) -> dict[str, Any]:
    items = _find_collection(value, (key, "items", "list", "data"))
    return {key: [item for item in items if isinstance(item, dict)]}


def _find_collection(value: Any, keys: tuple[str, ...]) -> list[Any]:
    value = _json_value(value)
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        return []
    for key in keys:
        candidate = _json_value(value.get(key))
        if isinstance(candidate, list):
            return candidate
    for key in ("data", "details", "payload", "result"):
        candidate = value.get(key)
        if isinstance(candidate, (dict, list, str)):
            found = _find_collection(candidate, keys)
            if found:
                return found
    return []


def _first_record(value: Any, keys: tuple[str, ...]) -> dict[str, Any] | None:
    value = _json_value(value)
    if not isinstance(value, dict):
        return None
    for key in keys:
        candidate = _json_value(value.get(key))
        if isinstance(candidate, dict):
            nested = _first_record(candidate, keys)
            return nested or candidate
    for key in ("data", "details", "payload", "result", "item"):
        candidate = value.get(key)
        if isinstance(candidate, (dict, str)):
            found = _first_record(candidate, keys)
            if found:
                return found
    return value if _is_business_record(value) else None


def _local_file_materials(files: list[Any]) -> list[dict[str, Any]]:
    materials: list[dict[str, Any]] = []
    for index, item in enumerate(files):
        if isinstance(item, str):
            path = item
            name = path.rsplit("/", 1)[-1]
            record: dict[str, Any] = {}
        elif isinstance(item, dict):
            record = item
            path = str(record.get("url") or record.get("path") or "")
            name = str(record.get("name") or record.get("filename") or path.rsplit("/", 1)[-1] or "未命名")
        else:
            continue
        materials.append({
            **record,
            "id": str(record.get("id") or f"local_file_{index}"),
            "name": name,
            "type": str(record.get("type") or "image"),
            "url": path,
            "thumbnail_url": str(record.get("thumbnail_url") or path),
            "status": str(record.get("status") or "local_available"),
            "source": str(record.get("source") or "local"),
        })
    return materials


def _is_business_record(value: dict[str, Any]) -> bool:
    return isinstance(value.get("id"), str) or isinstance(value.get("name"), str)
