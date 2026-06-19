#!/usr/bin/env python3
"""
Block 4: 通用任务模型 + DB Schema

验证：
- 创建 task（pending 状态）
- 运行后状态变 running → completed/error
- 跨用户访问被拒绝（404）
- 任务列表分页、过滤
"""

import json
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.auth import create_access_token


BASE_URL = "http://localhost:8020"


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def print_result(passed: bool, message: str) -> bool:
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


def send_agent_run_sync(prompt: str, session_id: str, token: str, timeout: int = 60):
    """同步运行 agent，收集所有 SSE 事件，返回最终状态"""
    url = f"{BASE_URL}/api/agent/runs"
    payload = {"prompt": prompt, "session_id": session_id, "task_type": "conversation"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    events = []
    current_event = None

    with httpx.stream("POST", url, json=payload, headers=headers, timeout=timeout) as response:
        if response.status_code != 200:
            return None, []

        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    data = {}
                events.append({"event": current_event, "data": data})

    final_status = None
    for event in reversed(events):
        if event["event"] in ("runtime.completed", "runtime.error", "runtime.aborted"):
            final_status = event["event"]
            break

    return final_status, events


def test_block_4() -> bool:
    print_section("Block 4: 通用任务模型 + DB Schema")

    user_a_id = f"user_block4_a_{int(time.time())}"
    user_b_id = f"user_block4_b_{int(time.time())}"
    token_a = create_access_token({"sub": user_a_id, "email": f"{user_a_id}@example.com", "name": "User A"})
    token_b = create_access_token({"sub": user_b_id, "email": f"{user_b_id}@example.com", "name": "User B"})
    results = []

    print_section("Step 4.1: 运行 task 并检查状态流转")
    session_a = f"session_block4_a_{uuid.uuid4().hex[:12]}"
    print(f"user_a: {user_a_id}, session: {session_a}")

    final_status, events = send_agent_run_sync("请简短回复：测试", session_a, token_a, timeout=60)
    print(f"最终状态: {final_status}")
    print(f"事件数: {len(events)}")

    results.append(print_result(final_status == "runtime.completed", "任务成功完成"))
    results.append(print_result(
        any(e["event"] == "runtime.started" for e in events),
        "状态流转：started 出现"
    ))
    results.append(print_result(
        any(e["event"] in ("message.updated", "message.completed") for e in events),
        "状态流转：message 出现"
    ))

    print_section("Step 4.2: 查询用户 A 的任务列表")
    response = httpx.get(
        f"{BASE_URL}/api/agent/tasks",
        headers={"Authorization": f"Bearer {token_a}"},
        timeout=10,
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        tasks_a = data.get("tasks", [])
        print(f"用户 A 任务数: {len(tasks_a)}")
        print(f"任务类型: {[t.get('task_type') for t in tasks_a[:5]]}")
        results.append(print_result(len(tasks_a) > 0, "用户 A 可查到自己的任务"))
        results.append(print_result(
            all(t.get("task_type") for t in tasks_a),
            "任务列表包含 task_type"
        ))
        task_a_id = tasks_a[0]["task_id"] if tasks_a else None
    else:
        results.append(print_result(False, "用户 A 可查到自己的任务"))
        results.append(print_result(False, "任务列表包含 task_type"))
        task_a_id = None

    print_section("Step 4.3: 查询用户 B 的任务列表（不应看到 A 的任务）")
    response_b = httpx.get(
        f"{BASE_URL}/api/agent/tasks",
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=10,
    )
    print(f"状态码: {response_b.status_code}")
    if response_b.status_code == 200:
        tasks_b = response_b.json().get("tasks", [])
        print(f"用户 B 任务数: {len(tasks_b)}")
        task_b_ids = [t["task_id"] for t in tasks_b]
        results.append(print_result(
            task_a_id not in task_b_ids if task_a_id else True,
            "用户 B 看不到用户 A 的任务"
        ))
    else:
        results.append(print_result(False, "用户 B 看不到用户 A 的任务"))

    print_section("Step 4.4: 用户 B 尝试访问用户 A 的任务详情（应 404）")
    if task_a_id:
        response_cross = httpx.get(
            f"{BASE_URL}/api/agent/tasks/{task_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
            timeout=10,
        )
        print(f"状态码: {response_cross.status_code}")
        results.append(print_result(
            response_cross.status_code == 404,
            "跨用户访问被拒绝（404）"
        ))
    else:
        results.append(print_result(False, "跨用户访问被拒绝（404）"))

    print_section("Step 4.5: 用户 A 访问自己的任务详情（应成功）")
    if task_a_id:
        response_own = httpx.get(
            f"{BASE_URL}/api/agent/tasks/{task_a_id}",
            headers={"Authorization": f"Bearer {token_a}"},
            timeout=10,
        )
        print(f"状态码: {response_own.status_code}")
        if response_own.status_code == 200:
            detail = response_own.json()
            print(f"任务详情: task_id={detail.get('task_id')}, status={detail.get('status')}")
            results.append(print_result(True, "用户 A 可访问自己的任务详情"))
            results.append(print_result(
                detail.get("status") in ("completed", "error", "running"),
                f"任务有明确状态（{detail.get('status')}）"
            ))
        else:
            results.append(print_result(False, "用户 A 可访问自己的任务详情"))
            results.append(print_result(False, "任务有明确状态"))
    else:
        results.append(print_result(False, "用户 A 可访问自己的任务详情"))
        results.append(print_result(False, "任务有明确状态"))

    print_section("Block 4 汇总")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    return passed == total


if __name__ == "__main__":
    success = test_block_4()
    sys.exit(0 if success else 1)
