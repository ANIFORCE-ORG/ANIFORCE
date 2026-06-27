"""Block 6 E2E: Safety MVP for lock, idempotency, and error shape."""

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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
AGENT_ROOT = PROJECT_ROOT / "aniforce-agent"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.config.database import Base  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository  # noqa: E402

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8010")
AGENT_URL = os.getenv("AGENT_SERVICE_URL", "http://127.0.0.1:8020")
LOG_PATH = ROOT / "logs" / "e2e_block6_safety.log"
DB_PATH = ROOT / "data" / "sqlite" / "animagus.db"
USER_ID = "user_test_001"
PROJECT_NAME = f"Block6-Idem-{int(time.time())}"


class CheckRunner:
    def __init__(self) -> None:
        self.expected = 9
        self.passed = 0
        self.failed = 0
        self.lines: list[str] = []
        self.started = time.time()
        self.backend_process: subprocess.Popen | None = None
        self.agent_process: subprocess.Popen | None = None

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
        self.log(f"input=backend={BACKEND_URL}, project={PROJECT_NAME}")
        self.log("output=Block 6 Safety MVP verification")
        self.log(f"errors={self.failed}")
        self.log(f"elapsed={elapsed:.2f}s")
        self.log(f"summary=passed {self.passed}/{self.expected}, failed {self.failed}")
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        for process in (self.backend_process, self.agent_process):
            if process:
                process.send_signal(signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()


def make_token(user_id: str = USER_ID) -> str:
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


async def service_ok(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
            return response.status_code < 500
    except httpx.HTTPError:
        return False


async def start_agent_if_needed(runner: CheckRunner) -> None:
    if await service_ok(f"{AGENT_URL}/health"):
        runner.log("agent already running")
        return
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.setdefault("JWT_SECRET", "change-me-in-production")
    env.setdefault("BACKEND_BASE_URL", BACKEND_URL)
    env.setdefault("UV_CACHE_DIR", "./uv_cache")
    agent_log = ROOT / "logs" / "e2e_block6_agent_start.log"
    agent_log.parent.mkdir(parents=True, exist_ok=True)
    agent_output = agent_log.open("w", encoding="utf-8")
    runner.agent_process = subprocess.Popen(
        ["uv", "run", "python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8020"],
        cwd=AGENT_ROOT,
        env=env,
        stdout=agent_output,
        stderr=subprocess.STDOUT,
    )
    for _ in range(60):
        if await service_ok(f"{AGENT_URL}/health"):
            runner.log("agent started by test")
            return
        await asyncio.sleep(0.5)
    raise RuntimeError("agent did not start")


async def start_backend_if_needed(runner: CheckRunner) -> None:
    if await service_ok(f"{BACKEND_URL}/health"):
        runner.log("backend already running")
        return
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.setdefault("DEMO_MODE", "false")
    env.setdefault("JWT_SECRET", "change-me-in-production")
    env.setdefault("AGENT_SERVICE_URL", AGENT_URL)
    env.setdefault("UV_CACHE_DIR", "./uv_cache")
    backend_log = ROOT / "logs" / "e2e_block6_backend_start.log"
    backend_log.parent.mkdir(parents=True, exist_ok=True)
    backend_output = backend_log.open("w", encoding="utf-8")
    runner.backend_process = subprocess.Popen(
        ["uv", "run", "python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010"],
        cwd=ROOT,
        env=env,
        stdout=backend_output,
        stderr=subprocess.STDOUT,
    )
    for _ in range(30):
        if await service_ok(f"{BACKEND_URL}/health"):
            runner.log("backend started by test")
            return
        await asyncio.sleep(0.5)
    raise RuntimeError("backend did not start")


async def count_projects_by_name(name: str) -> int:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        result = await session.execute(select(Project).where(Project.name == name))
        count = len(result.scalars().all())
    await engine.dispose()
    return count


async def ensure_session_state(session_id: str) -> None:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        repo = SqliteSessionStateRepository(session)
        existing = await repo.get(session_id, USER_ID)
        if existing is None:
            await repo.create(session_id, USER_ID)
        await session.commit()
    await engine.dispose()


async def get_session_state(session_id: str) -> dict | None:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        repo = SqliteSessionStateRepository(session)
        state = await repo.get(session_id, USER_ID)
    await engine.dispose()
    return state


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
    try:
        data = json.loads("\n".join(data_lines))
    except json.JSONDecodeError:
        data = {"text": "\n".join(data_lines)}
    return {"event": event, "data": data}


async def first_sse_event(response: httpx.Response, event_name: str, timeout_seconds: float = 10.0) -> dict | None:
    buffer = ""
    started = time.time()
    async for chunk in response.aiter_text():
        buffer += chunk
        while "\n\n" in buffer:
            raw, buffer = buffer.split("\n\n", 1)
            event = parse_sse(raw)
            if event and event["event"] == event_name:
                return event
        if time.time() - started > timeout_seconds:
            return None
    return None


async def main() -> None:
    runner = CheckRunner()
    try:
        await ensure_db_table()
        await start_agent_if_needed(runner)
        await start_backend_if_needed(runner)
        token = make_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            health = await client.get(f"{BACKEND_URL}/health")
            runner.check(health.status_code == 200, "backend health 正常")

            session_id = f"sess_block6_{int(time.time())}"
            await ensure_session_state(session_id)
            project_payload = {
                "name": PROJECT_NAME,
                "total_budget": 6000,
                "description": "Block 6 idempotency verification",
                "game_type": "RPG",
                "target_market": "US",
            }
            write_headers = {
                **headers,
                "Idempotency-Key": f"{session_id}:run_block6:create_project:fixed",
                "X-Agent-Session-Id": session_id,
                "X-Agent-Run-Id": "run_block6",
                "X-Agent-Tool-Call-Id": "tool_block6_create_project",
            }
            first = await client.post(f"{BACKEND_URL}/api/v1/projects", headers=write_headers, json=project_payload)
            runner.check(first.status_code == 200 and first.json().get("id"), "首次幂等写创建项目成功")

            second = await client.post(f"{BACKEND_URL}/api/v1/projects", headers=write_headers, json=project_payload)
            runner.check(second.status_code == 200 and second.json().get("id") == first.json().get("id"), "同 Idempotency-Key 返回同一结果")

            runner.check(await count_projects_by_name(PROJECT_NAME) == 1, "同 Idempotency-Key 不重复创建项目")

            state = await get_session_state(session_id)
            runner.check(state is not None and len(state.get("changelog") or []) == 1, "重复幂等写不重复追加 changelog")

            session_created = await client.post(f"{BACKEND_URL}/api/v1/agent/sessions", headers=headers)
            runner.check(session_created.status_code == 200 and session_created.json().get("session_id"), "创建 agent session 正常")
            busy_session = session_created.json()["session_id"]

            run_payload = {"prompt": "请只回复 OK", "session_id": busy_session, "context_snapshot": {"route": "/", "activePanel": "context"}}
            stream_one = client.stream("POST", f"{BACKEND_URL}/api/v1/agent/runs", headers={**headers, "Accept": "text/event-stream"}, json=run_payload)
            response_one = await stream_one.__aenter__()
            try:
                running = await first_sse_event(response_one, "run_status")
                runner.check(running is not None and running["data"].get("status") == "running", "首个 run 进入 running")

                async with httpx.AsyncClient(timeout=30.0) as second_client:
                    async with second_client.stream(
                        "POST",
                        f"{BACKEND_URL}/api/v1/agent/runs",
                        headers={**headers, "Accept": "text/event-stream"},
                        json=run_payload,
                    ) as response_two:
                        busy_error = await first_sse_event(response_two, "error")
                runner.check(
                    busy_error is not None
                    and busy_error["data"].get("error", {}).get("code") == "SESSION_BUSY"
                    and busy_error["data"].get("error", {}).get("retryable") is True,
                    "同 session 并发 run 返回统一 SESSION_BUSY 错误",
                )
            finally:
                await stream_one.__aexit__(None, None, None)

            unavailable = await client.get(f"{BACKEND_URL}/api/v1/agent/health", headers=headers)
            runner.check(unavailable.status_code in {200, 503}, "agent health 失败/成功都有明确状态")
    finally:
        runner.finish()


if __name__ == "__main__":
    asyncio.run(main())
