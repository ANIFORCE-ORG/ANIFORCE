"""Block 10 E2E: business_context_summary injection via backend gateway."""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from jose import jwt

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
os.chdir(ROOT)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8010")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
LOG_PATH = ROOT / "logs" / "e2e_block10_context_injection.log"
EXPECTED_MARKER = "MVPContextProject-260619"


class CheckRunner:
    def __init__(self) -> None:
        self.expected = 5
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
        self.log(f"input=backend={BACKEND_URL}, marker={EXPECTED_MARKER}")
        self.log("output=Block 3 business_context_summary injection verification")
        self.log(f"errors={self.failed}")
        self.log(f"elapsed={elapsed:.2f}s")
        self.log(f"summary=passed {self.passed}/{self.expected}, failed {self.failed}")
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def make_token(user_id: str = "user_test_001") -> str:
    return jwt.encode(
        {"sub": user_id, "email": "test@animagus.com", "name": "测试用户"},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


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


async def collect_events(response: httpx.Response, timeout_seconds: float = 90.0) -> list[dict[str, Any]]:
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
                if event["event"] in {"runtime.completed", "runtime.error", "runtime.aborted"}:
                    return events
        if time.time() - started > timeout_seconds:
            return events
    return events


async def main() -> None:
    runner = CheckRunner()
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=120.0) as client:
        health = await client.get(f"{BACKEND_URL}/api/v1/agent/health", headers=headers)
        runner.check(health.status_code == 200, "backend gateway health 正常")

        created = await client.post(f"{BACKEND_URL}/api/v1/agent/sessions", headers=headers)
        runner.check(created.status_code == 200 and created.json().get("session_id"), "创建 session 正常")
        session_id = created.json()["session_id"]

        payload = {
            "session_id": session_id,
            "task_type": "conversation",
            "prompt": "请只根据系统上下文回答：当前用户页面路径里包含的项目名标记是什么？只输出该标记。",
            "context_snapshot": {"route": f"/projects/{EXPECTED_MARKER}", "activePanel": "context"},
        }

        async with client.stream(
            "POST",
            f"{BACKEND_URL}/api/v1/agent/runs",
            headers={**headers, "Accept": "text/event-stream"},
            json=payload,
        ) as response:
            runner.check(response.status_code == 200, "runs SSE 正常")
            events = await collect_events(response)

    event_types = [event["event"] for event in events]
    runner.check(any(event in event_types for event in ("message.updated", "message.completed")), "收到真实 message 事件")
    all_text = json.dumps(events, ensure_ascii=False)
    runner.check(EXPECTED_MARKER in all_text, "Agent 输出引用 business_context_summary marker")
    runner.finish()


if __name__ == "__main__":
    asyncio.run(main())
