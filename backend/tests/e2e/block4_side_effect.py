"""Block 4 E2E: Tool call -> backend write -> changelog -> side_effect."""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from jose import jwt
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.config.database import Base  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository  # noqa: E402

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8010")
AGENT_URL = os.getenv("AGENT_SERVICE_URL", "http://127.0.0.1:8020")
LOG_PATH = ROOT / "logs" / "e2e_block4_side_effect.log"
DB_PATH = ROOT / "data" / "sqlite" / "animagus.db"
PROJECT_NAME = f"MVP-SideEffect-{int(time.time())}"


class CheckRunner:
    def __init__(self) -> None:
        self.expected = 8
        self.passed = 0
        self.failed = 0
        self.lines: list[str] = []
        self.started = time.time()

    def log(self, message: str) -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        print(line)
        self.lines.append(line)

    def check(self, condition: bool, label: str) -> None:
        if condition:
            self.passed += 1
            self.log(f"✓ {self.passed}/{self.expected} {label}")
            return
        self.failed += 1
        self.log(f"✗ {label}")
        raise AssertionError(label)

    def finish(self) -> None:
        elapsed = time.time() - self.started
        self.log(f"input=backend={BACKEND_URL}, agent={AGENT_URL}, project={PROJECT_NAME}")
        self.log("output=Block 4 side_effect verification")
        self.log(f"errors={self.failed}")
        self.log(f"elapsed={elapsed:.2f}s")
        self.log(f"summary=passed {self.passed}/{self.expected}, failed {self.failed}")
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def make_token(user_id: str = "user_test_001") -> str:
    settings = get_settings()
    return jwt.encode(
        {"sub": user_id, "email": "test@animagus.com", "name": "测试用户"},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


async def ensure_db_table() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def parse_sse(raw: str) -> dict[str, Any] | None:
    event = "message"
    data_lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].lstrip())
    if not data_lines:
        return None
    data_text = "\n".join(data_lines)
    try:
        data = json.loads(data_text)
    except json.JSONDecodeError:
        data = {"text": data_text}
    return {"event": event, "data": data}


async def collect_events(response: httpx.Response, timeout_seconds: float = 120.0) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    buffer = ""
    started = time.time()
    async for chunk in response.aiter_text():
        buffer += chunk
        while "\n\n" in buffer:
            raw, buffer = buffer.split("\n\n", 1)
            event = parse_sse(raw)
            if event:
                events.append(event)
                if event["event"] == "run_status" and event["data"].get("status") == "completed":
                    return events
                if event["event"] == "error":
                    return events
        if time.time() - started > timeout_seconds:
            return events
    return events


async def get_session_state(session_id: str, user_id: str = "user_test_001") -> dict | None:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        repo = SqliteSessionStateRepository(session)
        state = await repo.get(session_id, user_id)
    await engine.dispose()
    return state


async def main() -> None:
    runner = CheckRunner()
    await ensure_db_table()
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=150.0) as client:
        health = await client.get(f"{BACKEND_URL}/api/v1/agent/health", headers=headers)
        runner.check(health.status_code == 200, "backend gateway health 正常")

        created = await client.post(f"{BACKEND_URL}/api/v1/agent/sessions", headers=headers)
        runner.check(created.status_code == 200 and created.json().get("session_id"), "创建 session 正常")
        session_id = created.json()["session_id"]

        prompt = (
            f"请调用 create_project 工具创建一个项目，项目名必须是 {PROJECT_NAME}，"
            "总预算 12345，game_type 为 RPG，target_market 为 US。创建后简短说明结果。"
        )
        async with client.stream(
            "POST",
            f"{BACKEND_URL}/api/v1/agent/runs",
            headers={**headers, "Accept": "text/event-stream"},
            json={"prompt": prompt, "session_id": session_id, "context_snapshot": {"route": "/", "activePanel": "context"}},
        ) as response:
            runner.check(response.status_code == 200, "runs SSE 正常")
            events = await collect_events(response)

        event_types = [event["event"] for event in events]
        runner.check("tool_call.completed" in event_types or "tool_call.started" in event_types, "真实 Agent 触发工具调用事件")
        runner.check(any(event["event"] == "side_effect" for event in events), "SSE 包含 side_effect")

        state = await get_session_state(session_id)
        runner.check(state is not None and len(state["changelog"]) >= 1, "Session State changelog 已记录")
        runner.check(state and state["linked_entities"].get("project_id"), "linked_entities 记录 project_id")

        side_effects = [event["data"] for event in events if event["event"] == "side_effect"]
        runner.check(
            any(item.get("type") == "entity_changed" and item.get("domain") == "project" and "context" in item.get("refresh_panels", []) for item in side_effects),
            "side_effect 为 project entity_changed 且刷新 context",
        )

    runner.finish()


if __name__ == "__main__":
    asyncio.run(main())
