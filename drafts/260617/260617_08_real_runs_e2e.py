#!/usr/bin/env python3
"""Real E2E probe for /api/agent/runs business event stream."""

import json
import sqlite3
import uuid
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = PROJECT_ROOT / "aniforce-agent"

import sys
sys.path.insert(0, str(AGENT_ROOT))

from app.core.auth import create_access_token  # noqa: E402


def main() -> int:
    token = create_access_token(
        {
            "sub": "test_user_real_e2e",
            "email": "real-e2e@example.com",
            "name": "Real E2E",
        }
    )
    session_id = str(uuid.uuid4())
    payload = {
        "prompt": "请只回复一句话：收到",
        "session_id": session_id,
        "task_type": "conversation",
        "title": "real e2e",
        "include_raw_events": True,
        "max_turns": 1,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    print(f"session_id={session_id}")
    events: list[tuple[str | None, dict]] = []
    text_delta: list[str] = []
    task_id = None

    with httpx.stream(
        "POST",
        "http://127.0.0.1:8020/api/agent/runs",
        json=payload,
        headers=headers,
        timeout=180,
    ) as response:
        print(f"status={response.status_code}")
        if response.status_code != 200:
            print(response.read().decode())
            return 1

        current_event = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                current_event = line[7:]
                continue
            if not line.startswith("data: "):
                continue

            data = json.loads(line[6:])
            events.append((current_event, data))
            task_id = data.get("taskId") or task_id
            if current_event == "TaskOutputDelta":
                text_delta.append(data.get("delta", ""))
            if current_event in {
                "TaskCreated",
                "TaskProgressUpdated",
                "TaskOutputDelta",
                "TaskOutputProduced",
                "TaskCompleted",
                "sdk_raw_event",
            }:
                print(
                    "EVENT",
                    current_event,
                    json.dumps(data, ensure_ascii=False, default=str)[:800],
                )

    full_text = "".join(text_delta)
    print(f"event_count={len(events)}")
    print(f"text={full_text[:300]}")

    db_path = AGENT_ROOT / "runtime" / "agent" / "tasks.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "SELECT task_id, task_type, status, title, session_id FROM tasks WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
        (session_id,),
    )
    print("db_task=", cur.fetchone())
    if task_id:
        cur.execute(
            "SELECT event_type, COUNT(*) FROM events WHERE task_id = ? GROUP BY event_type ORDER BY event_type",
            (task_id,),
        )
        print("db_events=", cur.fetchall())
        cur.execute(
            "SELECT output_id, output_type, category, status, content FROM task_outputs WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
            (task_id,),
        )
        print("db_output=", cur.fetchone())
    conn.close()

    required_events = {"TaskCreated", "TaskOutputProduced", "TaskCompleted"}
    received_events = {event_type for event_type, _ in events}
    missing = sorted(required_events - received_events)
    if missing:
        print(f"missing_events={missing}")
        return 2
    if not full_text.strip():
        print("missing_text_delta=true")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
