"""SQLite repository for standalone GEO diagnosis demos."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .repository import GeoAuditRepository


class SqliteGeoAuditRepository(GeoAuditRepository):
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "database" / "001_create_geo_audits.sql"
        with self._connect() as conn:
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            conn.commit()

    async def create(self, report: dict) -> dict:
        input_data = report["input"]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO geo_audits (
                    id, project_id, brand, domain, category, market,
                    report_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report["id"],
                    report.get("project_id"),
                    input_data["brand"],
                    report["domain"],
                    input_data["category"],
                    input_data.get("market"),
                    json.dumps(report, ensure_ascii=False),
                    report["created_at"],
                    report["created_at"],
                ),
            )
            conn.commit()
        return report

    async def list_by_project(self, project_id: str, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT report_json
                FROM geo_audits
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        return [json.loads(row["report_json"]) for row in rows]

    async def get_by_id(self, audit_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT report_json FROM geo_audits WHERE id = ?",
                (audit_id,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["report_json"])
