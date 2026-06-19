#!/usr/bin/env python3
"""
Block 8: 对话历史 + resume + session 状态管理

生产验证点：
1. session 是用户拥有的长期会话，不是 task 派生字段
2. 同一 session_id 多轮对话能记住上文
3. 服务重启后 SQLiteSession 仍能 resume 上文
4. 用户不能 resume 其他用户的 session
5. 归档 session 后列表隐藏，且不能继续 run
"""

import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.auth import create_access_token


BASE_URL = "http://localhost:8020"
PROJECT_ROOT = Path(__file__).parent.parent.parent


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


def create_session(token: str) -> dict:
    resp = httpx.post(f"{BASE_URL}/api/agent/sessions", headers=auth_headers(token), timeout=20)
    print(f"创建 session 状态码: {resp.status_code}")
    resp.raise_for_status()
    data = resp.json()
    print(f"创建 session: {data}")
    return data


def list_sessions(token: str) -> list[dict]:
    resp = httpx.get(f"{BASE_URL}/api/agent/sessions", headers=auth_headers(token), timeout=20)
    print(f"session 列表状态码: {resp.status_code}")
    resp.raise_for_status()
    return resp.json()


def archive_session(token: str, session_id: str) -> httpx.Response:
    return httpx.post(
        f"{BASE_URL}/api/agent/sessions/{session_id}/archive",
        headers=auth_headers(token),
        timeout=20,
    )


def run_agent(prompt: str, session_id: str, token: str, timeout: int = 120) -> tuple[int, str, list[dict]]:
    payload = {"prompt": prompt, "session_id": session_id, "task_type": "conversation"}
    events = []
    text_content = ""
    current_event = None

    with httpx.stream(
        "POST",
        f"{BASE_URL}/api/agent/runs",
        json=payload,
        headers=auth_headers(token),
        timeout=timeout,
    ) as response:
        print(f"run 状态码: {response.status_code}")
        if response.status_code != 200:
            return response.status_code, response.read().decode("utf-8"), []

        for line in response.iter_lines():
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

    return 200, text_content, events


def restart_agent_service() -> None:
    print("重启 agent-service...")
    subprocess.run(["./start_dev.sh"], cwd=PROJECT_ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{BASE_URL}/health", timeout=3)
            if resp.status_code == 200:
                print("agent-service 已恢复")
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("agent-service 重启后未恢复")


def test_block_8() -> bool:
    print_section("Block 8: 对话历史 + resume + 状态管理")
    results = []
    suffix = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
    user_a = f"block8_user_a_{suffix}"
    user_b = f"block8_user_b_{suffix}"
    token_a = make_token(user_a)
    token_b = make_token(user_b)
    secret = f"block8-secret-{uuid.uuid4().hex[:8]}"

    print_section("Step 8.1: 创建用户 A session 元数据")
    session = create_session(token_a)
    session_id = session["session_id"]
    results.append(print_result(session_id.startswith("session_"), "创建真实 session_id"))
    sessions = list_sessions(token_a)
    results.append(print_result(any(s["session_id"] == session_id for s in sessions), "session 出现在用户 A 列表"))
    sessions_b = list_sessions(token_b)
    results.append(print_result(all(s["session_id"] != session_id for s in sessions_b), "用户 B 列表看不到用户 A session"))

    print_section("Step 8.2: 同 session 多轮记忆")
    status1, text1, events1 = run_agent(f"请记住暗号：{secret}。只回复：记住了。", session_id, token_a)
    print(f"第一轮回复: {text1[:300]}")
    results.append(print_result(status1 == 200, "第一轮 run 成功"))
    results.append(print_result(any(e["event"] == "runtime.completed" for e in events1), "第一轮 runtime.completed"))

    status2, text2, _ = run_agent("我刚才让你记住的暗号是什么？只回答暗号。", session_id, token_a)
    print(f"第二轮回复: {text2[:300]}")
    results.append(print_result(status2 == 200, "第二轮 run 成功"))
    results.append(print_result(secret in text2, "同 session 记得上文暗号"))

    print_section("Step 8.3: 服务重启后 resume")
    restart_agent_service()
    status3, text3, _ = run_agent("服务重启后，请再次回答我让你记住的暗号。只回答暗号。", session_id, token_a)
    print(f"重启后回复: {text3[:300]}")
    results.append(print_result(status3 == 200, "重启后 run 成功"))
    results.append(print_result(secret in text3, "重启后仍能 resume SQLiteSession 历史"))

    print_section("Step 8.4: 跨用户 resume 被拒绝")
    status_cross, body_cross, _ = run_agent("尝试读取别人的会话", session_id, token_b, timeout=30)
    print(f"跨用户状态码: {status_cross}, body: {body_cross[:300]}")
    results.append(print_result(status_cross == 404, "用户 B 不能 resume 用户 A session"))

    print_section("Step 8.5: 归档 session 后不可继续使用")
    archive_resp = archive_session(token_a, session_id)
    print(f"归档状态码: {archive_resp.status_code}, body: {archive_resp.text[:300]}")
    results.append(print_result(archive_resp.status_code == 200, "session 归档成功"))
    sessions_after_archive = list_sessions(token_a)
    results.append(print_result(all(s["session_id"] != session_id for s in sessions_after_archive), "归档 session 不再出现在 active 列表"))
    status_archived, body_archived, _ = run_agent("归档后尝试继续对话", session_id, token_a, timeout=30)
    print(f"归档后 run 状态码: {status_archived}, body: {body_archived[:300]}")
    results.append(print_result(status_archived == 404, "归档 session 不能继续 run"))

    print_section("Block 8 汇总")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    return passed == total


if __name__ == "__main__":
    success = test_block_8()
    sys.exit(0 if success else 1)
