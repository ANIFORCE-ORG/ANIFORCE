"""Repository contracts and demo repository for GEO diagnosis."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class GeoAuditRepository(Protocol):
    async def create(self, report: dict) -> dict: ...
    async def list_by_project(self, project_id: str, limit: int = 50) -> list[dict]: ...
    async def get_by_id(self, audit_id: str) -> dict | None: ...


class MemoryGeoAuditRepository:
    def __init__(self):
        self._audits: dict[str, dict] = {}

    async def create(self, report: dict) -> dict:
        self._audits[report["id"]] = report
        return report

    async def list_by_project(self, project_id: str, limit: int = 50) -> list[dict]:
        audits = [
            audit
            for audit in self._audits.values()
            if audit.get("project_id") == project_id
        ]
        return sorted(audits, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]

    async def get_by_id(self, audit_id: str) -> dict | None:
        return self._audits.get(audit_id)
