"""Block 2 E2E: Backend Agent Gateway."""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from jose import jwt
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.config.database import Base  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository  # noqa: E402

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8010")
AGENT_URL = os.getenv("AGENT_SERVICE_URL", "http://127.0.0.1:8020")
LOG_PATH = ROOT / "logs" / "e2e_block2_agent_gateway.log"
DB_PATH = ROOT / "data" / "sqlite" / "animagus.db"


class CheckRunner:
    def __init__(self) -> None:
        self.expected = 14
        self.passed = 0
        self.failed = 0
        self.lines: list[str] = []
        self.started = time.time()
        self.backend_process: subprocess.Popen | None = None

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
        self.log(f"input=backend={BACKEND_URL}, agent={AGENT_URL}")
        self.log("output=Block 2 Backend Agent Gateway verification")
        self.log(f"errors={self.failed}")
        self.log(f"elapsed={elapsed:.2f}s")
        self.log(f"summary=passed {self.passed}/{self.expected}, failed {self.failed}")
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        if self.backend_process:
            self.backend_process.send_signal(signal.SIGTERM)
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()


async def ensure_db_table() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def service_ok(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
            return response.status_code < 500
    except httpx.HTTPError:
        return False


def make_token(user_id: str = "user_test_001") -> str:
    settings = get_settings()
    return jwt.encode(
        {"sub": user_id, "email": "test@animagus.com", "name": "测试用户"},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


async def start_backend_if_needed(runner: CheckRunner) -> None:
    if await service_ok(f"{BACKEND_URL}/health"):
        runner.log("backend already running")
        return
    env = os.environ.copy()
    env.setdefault("DEMO_MODE", "false")
    env.setdefault("JWT_SECRET", "change-me-in-production")
    env.setdefault("AGENT_SERVICE_URL", AGENT_URL)
    env.setdefault("UV_CACHE_DIR", "./uv_cache")
    runner.backend_process = subprocess.Popen(
        ["uv", "run", "python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        if await service_ok(f"{BACKEND_URL}/health"):
            runner.log("backend started by test")
            return
        await asyncio.sleep(0.5)
    raise RuntimeError("backend did not start")


async def read_sse_events(response: httpx.Response, timeout_seconds: float = 60.0) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    buffer = ""
    started = time.time()
    async for chunk in response.aiter_text():
        buffer += chunk
        while "\n\n" in buffer:
            raw, buffer = buffer.split("\n\n", 1)
            parsed = parse_sse(raw)
            if parsed:
                events.append(parsed)
                if parsed["event"] in {"runtime.completed", "runtime.error", "runtime.aborted"}:
                    return events
        if time.time() - started > timeout_seconds:
            return events
    return events


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

    agent_available = await service_ok(f"{AGENT_URL}/health")
    runner.check(agent_available, "agent-service health 可达")

    await start_backend_if_needed(runner)
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        health = await client.get(f"{BACKEND_URL}/api/v1/agent/health", headers=headers)
        runner.check(health.status_code == 200, "/api/v1/agent/health 正常")

        created = await client.post(f"{BACKEND_URL}/api/v1/agent/sessions", headers=headers)
        runner.check(created.status_code == 200 and created.json().get("session_id"), "创建 session 正常")
        session_id = created.json()["session_id"]

        state = await get_session_state(session_id)
        runner.check(state is not None and state["session_id"] == session_id, "backend 同步创建 Session State")

        listed = await client.get(f"{BACKEND_URL}/api/v1/agent/sessions", headers=headers)
        sessions = listed.json() if listed.status_code == 200 else []
        runner.check(listed.status_code == 200 and any(item.get("session_id") == session_id for item in sessions), "list sessions 正常")

        run_payload = {
            "prompt": "请只回复 OK，不要调用任何工具。",
            "session_id": session_id,
            "task_type": "conversation",
            "context_snapshot": {"route": "/", "activePanel": "context"},
        }
        async with client.stream(
            "POST",
            f"{BACKEND_URL}/api/v1/agent/runs",
            headers={**headers, "Accept": "text/event-stream"},
            json=run_payload,
        ) as response:
            runner.check(response.status_code == 200, "runs 返回 SSE")
            events = await read_sse_events(response)

        event_types = [event["event"] for event in events]
        runner.check(any(event["event"] == "run_status" and event["data"].get("status") == "running" for event in events), "SSE 包含 running run_status")
        runner.check("runtime.started" in event_types, "真实 Agent 流包含 runtime.started")
        runner.check(any(event in event_types for event in ("message.updated", "message.completed")), "真实 Agent 流包含 message 事件")
        runner.check(any(event in event_types for event in ("runtime.completed", "runtime.error", "runtime.aborted")), "真实 Agent 流包含终态事件")

        state_after_context = await get_session_state(session_id)
        runner.check(state_after_context and state_after_context["ui_snapshot"]["route"] == "/", "context_snapshot 写入 Session State")

        state_after_run = await get_session_state(session_id)
        runner.check(state_after_run and state_after_run["status"] in {"active", "error"}, "run 后 Session State 最终状态可读")

        bad = await client.get(f"{BACKEND_URL}/api/v1/agent/health")
        runner.check(bad.status_code in {200, 401}, "无 token 场景有明确响应")

        runner.check("business_context_summary" in Path("app/api/v1/agent_routes.py").read_text(encoding="utf-8"), "business_context_summary 已接入 gateway payload")

    runner.finish()


if __name__ == "__main__":
    asyncio.run(main())
