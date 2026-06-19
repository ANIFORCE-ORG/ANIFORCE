#!/usr/bin/env python3
"""
Block 3: 事件系统（AgentTaskEvent 流）

验证：
- /api/agent/runs 返回 SSE 事件流
- 事件 sequence 单调递增
- 事件落盘到 runtime/agent/tasks.db 的 events 表
- after_sequence 查询只返回后续事件
"""

import json
import sqlite3
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.auth import create_access_token


BASE_URL = "http://localhost:8020"
DB_PATH = Path(__file__).parent.parent.parent / "runtime/agent/tasks.db"


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def print_result(passed: bool, message: str) -> bool:
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


def send_agent_run(prompt: str, session_id: str, token: str, timeout: int = 60):
    """发送 /api/agent/runs 请求，收集 SSE 事件和 id sequence。"""
    url = f"{BASE_URL}/api/agent/runs"
    payload = {
        "prompt": prompt,
        "session_id": session_id,
        "task_type": "conversation",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    events = []
    current_event = None
    current_id = None

    with httpx.stream("POST", url, json=payload, headers=headers, timeout=timeout) as response:
        print(f"状态码: {response.status_code}")
        if response.status_code != 200:
            print(f"错误响应: {response.text[:500]}")
            return events

        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith("id: "):
                try:
                    current_id = int(line[4:].strip())
                except ValueError:
                    current_id = None
            elif line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    data = {"_raw": line[6:]}
                events.append({"id": current_id, "event": current_event, "data": data})

    return events


def get_latest_task_id(user_id: str, session_id: str) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT task_id FROM tasks
            WHERE user_id = ? AND session_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id, session_id),
        ).fetchone()
        return row["task_id"] if row else None
    finally:
        conn.close()


def list_events(task_id: str, after_sequence: int | None = None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        query = "SELECT * FROM events WHERE task_id = ?"
        params = [task_id]
        if after_sequence is not None:
            query += " AND sequence > ?"
            params.append(after_sequence)
        query += " ORDER BY sequence ASC"
        return [dict(row) for row in conn.execute(query, params).fetchall()]
    finally:
        conn.close()


def test_block_3() -> bool:
    print_section("Block 3: 事件系统（AgentTaskEvent 流）")

    user_id = "user_block3_event"
    token = create_access_token({"sub": user_id, "email": "block3@example.com", "name": "Block3"})
    session_id = f"session_block3_{uuid.uuid4().hex[:12]}"
    results = []

    print_section("Step 3.1: 运行任务并收集 SSE")
    start = time.time()
    events = send_agent_run("请简短回复：事件系统测试", session_id, token, timeout=60)
    elapsed = time.time() - start
    event_types = [event["event"] for event in events]
    sequences = [event["id"] for event in events if event["id"] is not None]
    print(f"耗时: {elapsed:.2f}s")
    print(f"事件数: {len(events)}")
    print(f"事件类型: {event_types}")
    print(f"SSE sequences: {sequences}")

    results.append(print_result(len(events) >= 4, "收到多个 SSE 事件"))
    results.append(print_result("runtime.started" in event_types, "包含 runtime.started"))
    results.append(print_result("message.completed" in event_types, "包含 message.completed"))
    results.append(print_result("runtime.completed" in event_types, "包含 runtime.completed"))
    results.append(print_result(sequences == sorted(sequences), "SSE sequence 单调递增"))
    results.append(print_result(len(sequences) == len(set(sequences)), "SSE sequence 不重复"))

    print_section("Step 3.2: 校验事件落盘")
    task_id = get_latest_task_id(user_id, session_id)
    print(f"task_id: {task_id}")
    db_events = list_events(task_id) if task_id else []
    db_event_types = [event["event_type"] for event in db_events]
    db_sequences = [event["sequence"] for event in db_events]
    print(f"DB 事件数: {len(db_events)}")
    print(f"DB 事件类型: {db_event_types}")
    print(f"DB sequences: {db_sequences}")

    results.append(print_result(bool(task_id), "可从 DB 找到本次 task"))
    results.append(print_result(len(db_events) >= len(events), "SSE 事件已落盘"))
    results.append(print_result(db_sequences == sorted(db_sequences), "DB sequence 单调递增"))
    results.append(print_result(len(db_sequences) == len(set(db_sequences)), "DB sequence 不重复"))
    results.append(print_result("runtime.started" in db_event_types, "DB 包含 runtime.started"))
    results.append(print_result("runtime.completed" in db_event_types, "DB 包含 runtime.completed"))

    print_section("Step 3.3: 校验 after_sequence 查询语义")
    if db_sequences:
        pivot = db_sequences[0]
        after_events = list_events(task_id, after_sequence=pivot)
        after_sequences = [event["sequence"] for event in after_events]
        print(f"after_sequence={pivot} 返回: {after_sequences}")
        results.append(print_result(all(seq > pivot for seq in after_sequences), "after_sequence 只返回后续事件"))
        results.append(print_result(len(after_events) == max(0, len(db_events) - 1), "after_sequence 数量正确"))
    else:
        results.append(print_result(False, "after_sequence 只返回后续事件"))
        results.append(print_result(False, "after_sequence 数量正确"))

    print_section("Block 3 汇总")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    return passed == total


if __name__ == "__main__":
    success = test_block_3()
    sys.exit(0 if success else 1)
