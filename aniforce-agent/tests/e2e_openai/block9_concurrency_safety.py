#!/usr/bin/env python3
"""
Block 9: 生产并发安全

生产验证点：
1. 多用户多 session 并发 run 全部成功
2. 并发写 SQLite 不出现 database is locked
3. 每个用户只能看到自己的 task/session
4. 同一 session 并发请求被服务端串行化，避免历史和 sandbox 竞态写
"""

import asyncio
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
PROJECT_ROOT = Path(__file__).parent.parent.parent
TASK_DB = PROJECT_ROOT / "runtime/agent/tasks.db"


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def print_result(passed: bool, message: str) -> bool:
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


def make_token(user_id: str) -> str:
    return create_access_token({"sub": user_id, "email": f"{user_id}@example.com", "name": user_id})


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def create_session(client: httpx.AsyncClient, token: str) -> str:
    resp = await client.post(f"{BASE_URL}/api/agent/sessions", headers=auth_headers(token))
    resp.raise_for_status()
    return resp.json()["session_id"]


async def list_sessions(client: httpx.AsyncClient, token: str) -> list[dict]:
    resp = await client.get(f"{BASE_URL}/api/agent/sessions", headers=auth_headers(token))
    resp.raise_for_status()
    return resp.json()


async def list_tasks(client: httpx.AsyncClient, token: str) -> list[dict]:
    resp = await client.get(f"{BASE_URL}/api/agent/tasks", headers=auth_headers(token))
    resp.raise_for_status()
    return resp.json().get("tasks", [])


async def run_agent(client: httpx.AsyncClient, token: str, session_id: str, marker: str) -> dict:
    payload = {
        "prompt": f"请只回复这个标记，不要解释：{marker}",
        "session_id": session_id,
        "task_type": "conversation",
    }
    events = []
    text_content = ""
    current_event = None
    started_at = time.perf_counter()

    try:
        async with client.stream("POST", f"{BASE_URL}/api/agent/runs", json=payload, headers=auth_headers(token)) as response:
            status_code = response.status_code
            if status_code != 200:
                body = await response.aread()
                return {
                    "ok": False,
                    "status_code": status_code,
                    "marker": marker,
                    "session_id": session_id,
                    "text": body.decode("utf-8", errors="ignore"),
                    "events": [],
                    "elapsed": time.perf_counter() - started_at,
                }

            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                    continue
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    data = {}
                events.append({"event": current_event, "data": data})
                if current_event == "message.updated":
                    text_content += data.get("delta", "")
                elif current_event == "message.completed":
                    text_content = data.get("content", text_content)
    except Exception as exc:
        return {
            "ok": False,
            "status_code": 0,
            "marker": marker,
            "session_id": session_id,
            "text": str(exc),
            "events": [],
            "elapsed": time.perf_counter() - started_at,
        }

    event_names = [event["event"] for event in events]
    has_error = any(event["event"] in {"runtime.error", "error"} for event in events)
    locked_error = "database is locked" in text_content.lower() or any(
        "database is locked" in json.dumps(event, ensure_ascii=False).lower() for event in events
    )

    return {
        "ok": status_code == 200 and "runtime.completed" in event_names and marker in text_content and not has_error and not locked_error,
        "status_code": status_code,
        "marker": marker,
        "session_id": session_id,
        "text": text_content,
        "events": events,
        "elapsed": time.perf_counter() - started_at,
        "has_error": has_error,
        "locked_error": locked_error,
    }


def check_sqlite_wal() -> tuple[bool, str]:
    conn = sqlite3.connect(TASK_DB)
    try:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        return journal_mode.lower() == "wal" and busy_timeout >= 5000, f"journal_mode={journal_mode}, busy_timeout={busy_timeout}"
    finally:
        conn.close()


async def test_block_9_async() -> bool:
    print_section("Block 9: 生产并发安全")
    results = []
    suffix = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"

    async with httpx.AsyncClient(timeout=180) as client:
        print_section("Step 9.1: SQLite WAL / busy_timeout 配置")
        wal_ok, wal_info = check_sqlite_wal()
        print(wal_info)
        results.append(print_result(wal_ok, "tasks.db 启用 WAL 且 busy_timeout >= 5000ms"))

        print_section("Step 9.2: 准备 5 用户 × 2 session")
        users = []
        all_session_ids = set()
        for user_index in range(5):
            user_id = f"block9_user_{user_index}_{suffix}"
            token = make_token(user_id)
            session_a = await create_session(client, token)
            session_b = await create_session(client, token)
            users.append({"user_id": user_id, "token": token, "sessions": [session_a, session_b]})
            all_session_ids.update([session_a, session_b])
            print(f"用户 {user_index}: {user_id}, sessions={session_a}, {session_b}")

        results.append(print_result(len(all_session_ids) == 10, "10 个 session_id 全部唯一"))

        print_section("Step 9.3: 10 个跨用户请求并发执行")
        jobs = []
        expected_markers = []
        for user_index, user in enumerate(users):
            for session_index, session_id in enumerate(user["sessions"]):
                marker = f"block9-ok-u{user_index}-s{session_index}-{suffix}"
                expected_markers.append(marker)
                jobs.append(run_agent(client, user["token"], session_id, marker))

        started = time.perf_counter()
        run_results = await asyncio.gather(*jobs)
        elapsed = time.perf_counter() - started
        print(f"并发总耗时: {elapsed:.2f}s")

        for item in run_results:
            print(
                f"marker={item['marker']} ok={item['ok']} status={item['status_code']} "
                f"elapsed={item['elapsed']:.2f}s text={item['text'][:80]!r}"
            )

        results.append(print_result(all(item["status_code"] == 200 for item in run_results), "10 个并发 run HTTP 200"))
        results.append(print_result(all(item["ok"] for item in run_results), "10 个并发 run 全部完成且回复各自 marker"))
        results.append(print_result(not any(item.get("locked_error") for item in run_results), "并发过程中无 database is locked"))
        results.append(print_result(not any(item.get("has_error") for item in run_results), "并发过程中无 runtime.error"))

        print_section("Step 9.4: 用户 task/session 列表隔离")
        for user_index, user in enumerate(users):
            sessions = await list_sessions(client, user["token"])
            tasks = await list_tasks(client, user["token"])
            visible_session_ids = {s["session_id"] for s in sessions}
            visible_task_sessions = {t.get("session_id") for t in tasks}
            own_session_ids = set(user["sessions"])
            print(
                f"用户 {user_index}: visible_sessions={len(visible_session_ids)}, "
                f"visible_tasks={len(tasks)}, own_sessions_visible={own_session_ids <= visible_session_ids}"
            )
            results.append(print_result(own_session_ids <= visible_session_ids, f"用户 {user_index} 可见自己的 session"))
            results.append(print_result(own_session_ids <= visible_task_sessions, f"用户 {user_index} 可见自己的 task run"))
            results.append(print_result(visible_session_ids.isdisjoint(all_session_ids - own_session_ids), f"用户 {user_index} 看不到其他用户 session"))
            results.append(print_result(visible_task_sessions.isdisjoint(all_session_ids - own_session_ids), f"用户 {user_index} 看不到其他用户 task"))

        print_section("Step 9.5: 同一 session 并发请求串行安全")
        same_user = users[0]
        same_session = await create_session(client, same_user["token"])
        marker_a = f"block9-same-a-{suffix}"
        marker_b = f"block9-same-b-{suffix}"
        same_results = await asyncio.gather(
            run_agent(client, same_user["token"], same_session, marker_a),
            run_agent(client, same_user["token"], same_session, marker_b),
        )
        for item in same_results:
            print(
                f"same-session marker={item['marker']} ok={item['ok']} "
                f"status={item['status_code']} elapsed={item['elapsed']:.2f}s text={item['text'][:80]!r}"
            )
        results.append(print_result(all(item["ok"] for item in same_results), "同一 session 双并发请求均成功完成"))
        results.append(print_result(not any(item.get("locked_error") for item in same_results), "同一 session 双并发无 SQLite 锁错误"))

    print_section("Block 9 汇总")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    return passed == total


def test_block_9() -> bool:
    return asyncio.run(test_block_9_async())


if __name__ == "__main__":
    success = test_block_9()
    sys.exit(0 if success else 1)
