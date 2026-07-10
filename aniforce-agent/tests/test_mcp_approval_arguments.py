from __future__ import annotations

import asyncio
import importlib
import json
import sys
from pathlib import Path

import aiosqlite

agent_root = Path(__file__).parent.parent
project_root = agent_root.parent
sys.path.insert(0, str(agent_root))

from app import mcp_server


class FakeContext:
    def __init__(self, *, run_id: str, user_id: str, checkpoint_id: str = "current") -> None:
        self.request_context = type(
            "RequestContext",
            (),
            {"meta": {"run_id": run_id, "user_id": user_id, "checkpoint_id": checkpoint_id}},
        )()


async def create_checkpoint_db(db_path: Path) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE runtime_checkpoints (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                approved_arguments_json TEXT,
                interruptions_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        rows = [
            (
                "current",
                "run_1",
                "user_1",
                "resuming",
                json.dumps({"budget": 100}),
                json.dumps([{"tool_name": "create_project"}]),
                "2026-07-10T10:00:00",
            ),
            (
                "same_tool_other_checkpoint",
                "run_1",
                "user_1",
                "resuming",
                json.dumps({"budget": 777}),
                json.dumps([{"tool_name": "create_project"}]),
                "2026-07-10T10:30:00",
            ),
            (
                "other_user",
                "run_1",
                "user_2",
                "resuming",
                json.dumps({"budget": 999}),
                json.dumps([{"tool_name": "create_project"}]),
                "2026-07-10T11:00:00",
            ),
            (
                "completed",
                "run_1",
                "user_1",
                "completed",
                json.dumps({"budget": 888}),
                json.dumps([{"tool_name": "create_project"}]),
                "2026-07-10T12:00:00",
            ),
        ]
        await db.executemany(
            "INSERT INTO runtime_checkpoints VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        await db.commit()


def test_approved_arguments_are_isolated_by_user_status_and_tool(monkeypatch) -> None:
    async def scenario() -> None:
        db_path = project_root / "drafts" / "260710" / "260710_02_mcp_approval_test.db"
        db_path.unlink(missing_ok=True)
        await create_checkpoint_db(db_path)

        class Settings:
            AGENT_RUNTIME_DB_URL = f"sqlite+aiosqlite:///{db_path}"

        settings_module = importlib.import_module("app.config.settings")
        monkeypatch.setattr(settings_module, "get_settings", lambda: Settings())
        try:
            approved = await mcp_server._get_approved_arguments(
                FakeContext(run_id="run_1", user_id="user_1"),
                "create_project",
            )
            wrong_user = await mcp_server._get_approved_arguments(
                FakeContext(run_id="run_1", user_id="user_3"),
                "create_project",
            )
            wrong_tool = await mcp_server._get_approved_arguments(
                FakeContext(run_id="run_1", user_id="user_1"),
                "update_project",
            )
            missing_checkpoint = await mcp_server._get_approved_arguments(
                FakeContext(run_id="run_1", user_id="user_1", checkpoint_id=""),
                "create_project",
            )

            assert approved == {"budget": 100}
            assert wrong_user is None
            assert wrong_tool is None
            assert missing_checkpoint is None
        finally:
            db_path.unlink(missing_ok=True)

    asyncio.run(scenario())
