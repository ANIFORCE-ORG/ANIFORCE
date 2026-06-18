#!/usr/bin/env python3
"""
Block 10: 生产并发安全测试 —— 多用户状态隔离验证

验证闭包注入方案：
- 两个用户并发发起 /runs
- 都触发 HITL 确认
- 验证：用户 A 的 HITL 不会落到用户 B 的 task
- 验证：用户 A 的 backend 工具不会用用户 B 的 JWT

这是生产部署前的 P0 安全门禁。
"""

import sys
import asyncio
import json
import uuid
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from app.core.auth import create_access_token
from app.config.settings import get_settings


def print_section(title):
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def print_result(passed, message):
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


async def consume_run_with_hitl(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    payload: dict,
    label: str,
    timeout: float = 240,
):
    """消费一个 run 的 SSE 流，自动响应它自己的 HITL，返回 task_id 和工具序列"""
    events = []
    tool_calls = []
    current_event = None
    task_id = None
    hitl_responded = False

    async def hitl_poller(tid: str):
        nonlocal hitl_responded
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = httpx.get(
                    f"{base_url}/api/agent/tasks/{tid}/outputs",
                    headers=headers,
                    timeout=10,
                )
                if r.status_code == 200:
                    for out in r.json().get("outputs", []):
                        if (
                            out.get("type") == "hitl_request"
                            and out.get("status") == "pending_review"
                        ):
                            hitl_id = out["output_id"]
                            content = out.get("content", {})
                            print(f"  [{label}] HITL: action={content.get('action')}")
                            # 只响应自己的 HITL（用本请求的 headers）
                            resp = httpx.post(
                                f"{base_url}/api/agent/hitl/{hitl_id}/respond",
                                json={"approved": True, "feedback": f"auto by {label}"},
                                headers=headers,
                                timeout=10,
                            )
                            print(f"  [{label}] HITL 响应 status={resp.status_code}")
                            hitl_responded = True
                            return
            except Exception:
                pass
            await asyncio.sleep(1)

    async with client.stream("POST", f"{base_url}/api/agent/runs", json=payload, headers=headers, timeout=timeout) as response:
        if response.status_code != 200:
            body = await response.aread()
            print(f"  [{label}] ❌ HTTP {response.status_code}: {body.decode()[:200]}")
            return None, [], False

        poller = None
        async for line in response.aiter_lines():
            if line.startswith("event: "):
                current_event = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                events.append((current_event, data))
                if current_event == "TaskCreated":
                    task_id = data.get("taskId")
                    poller = asyncio.create_task(hitl_poller(task_id))
                elif current_event == "TaskProgressUpdated":
                    tool_info = data.get("progress", {}).get("tool")
                    if tool_info and isinstance(tool_info, dict):
                        tool_calls.append(tool_info.get("name", ""))
                        print(f"  [{label}] 工具: {tool_info.get('name')}")

        if poller:
            poller.cancel()
            try:
                await poller
            except asyncio.CancelledError:
                pass

    return task_id, tool_calls, hitl_responded


async def test_block_10():
    """执行 Block 10 并发安全测试"""

    print_section("Block 10: 生产并发安全 —— 多用户状态隔离")

    results = []
    base_url = "http://localhost:8020"
    settings = get_settings()

    # 两个用户
    user_a = "user_concurrent_a"
    user_b = "user_concurrent_b"
    token_a = create_access_token({"sub": user_a, "email": "a@e.com", "name": "A"})
    token_b = create_access_token({"sub": user_b, "email": "b@e.com", "name": "B"})
    headers_a = {"Authorization": f"Bearer {token_a}", "Content-Type": "application/json"}
    headers_b = {"Authorization": f"Bearer {token_b}", "Content-Type": "application/json"}
    backend_headers_a = {**headers_a, "X-Internal-Token": settings.INTERNAL_TOKEN}
    backend_headers_b = {**headers_b, "X-Internal-Token": settings.INTERNAL_TOKEN}

    # 准备：两个用户各建一个项目
    print_section("准备：两个用户各建项目")
    r = httpx.post("http://localhost:18003/api/v1/mcp/tools/create_project",
                   json={"name": "create_project", "arguments": {"name": f"ConcurrentA_{uuid.uuid4().hex[:6]}", "total_budget": 10000}},
                   headers=backend_headers_a, timeout=15)
    proj_a = eval(r.json()["content"][0]["text"])
    pid_a = proj_a["id"]
    print(f"用户 A 项目: {pid_a} (user_id={proj_a['user_id']})")

    r = httpx.post("http://localhost:18003/api/v1/mcp/tools/create_project",
                   json={"name": "create_project", "arguments": {"name": f"ConcurrentB_{uuid.uuid4().hex[:6]}", "total_budget": 10000}},
                   headers=backend_headers_b, timeout=15)
    proj_b = eval(r.json()["content"][0]["text"])
    pid_b = proj_b["id"]
    print(f"用户 B 项目: {pid_b} (user_id={proj_b['user_id']})")

    results.append(print_result(proj_a["user_id"] == user_a and proj_b["user_id"] == user_b, "两用户项目归属正确"))

    # 并发：两个用户同时创建广告计划（都触发 HITL）
    print_section("并发：两用户同时跑 Agent（含 HITL）")

    payload_a = {
        "prompt": f"在项目 {proj_a['name']} 下创建 Meta 广告计划，名字 ConcurrentA_Campaign，预算 3000。创建前先确认。",
        "session_id": str(uuid.uuid4()),
        "task_type": "conversation",
        "title": "concurrent A",
        "max_turns": 15,
    }
    payload_b = {
        "prompt": f"在项目 {proj_b['name']} 下创建 Meta 广告计划，名字 ConcurrentB_Campaign，预算 7000。创建前先确认。",
        "session_id": str(uuid.uuid4()),
        "task_type": "conversation",
        "title": "concurrent B",
        "max_turns": 15,
    }

    async with httpx.AsyncClient() as client:
        # 真正并发
        task_a = asyncio.create_task(consume_run_with_hitl(client, base_url, headers_a, payload_a, "A"))
        task_b = asyncio.create_task(consume_run_with_hitl(client, base_url, headers_b, payload_b, "B"))
        result_a = await task_a
        result_b = await task_b

    task_id_a, tools_a, hitl_a = result_a
    task_id_b, tools_b, hitl_b = result_b

    print(f"\n用户 A: task={task_id_a}, hitl={hitl_a}, tools={tools_a}")
    print(f"用户 B: task={task_id_b}, hitl={hitl_b}, tools={tools_b}")

    # 验证 1：两个 task 是不同的
    results.append(print_result(task_id_a != task_id_b, "两用户 task 不同"))

    # 验证 2：两个 HITL 都被响应了
    results.append(print_result(hitl_a and hitl_b, "两用户 HITL 都被响应"))

    # 验证 3：用户 A 的计划只建在 A 的项目下，B 的只建在 B 的项目下（JWT 隔离）
    r = httpx.post("http://localhost:18003/api/v1/mcp/tools/list_campaigns",
                   json={"name": "list_campaigns", "arguments": {"project_id": pid_a}},
                   headers=backend_headers_a, timeout=15)
    camps_a = eval(r.json()["content"][0]["text"]).get("campaigns", [])
    has_a_camp = any("concurrenta_campaign" in c.get("name", "").lower() for c in camps_a)
    has_b_camp_in_a = any("concurrentb_campaign" in c.get("name", "").lower() for c in camps_a)

    r = httpx.post("http://localhost:18003/api/v1/mcp/tools/list_campaigns",
                   json={"name": "list_campaigns", "arguments": {"project_id": pid_b}},
                   headers=backend_headers_b, timeout=15)
    camps_b = eval(r.json()["content"][0]["text"]).get("campaigns", [])
    has_b_camp = any("concurrentb_campaign" in c.get("name", "").lower() for c in camps_b)
    has_a_camp_in_b = any("concurrenta_campaign" in c.get("name", "").lower() for c in camps_b)

    print(f"\n用户 A 项目下的计划: {[c['name'] for c in camps_a]}")
    print(f"用户 B 项目下的计划: {[c['name'] for c in camps_b]}")

    results.append(print_result(has_a_camp and not has_b_camp_in_a, "用户 A 计划只建在 A 项目下（无 B 穿越到 A）"))
    results.append(print_result(has_b_camp and not has_a_camp_in_b, "用户 B 计划只建在 B 项目下（无 A 穿越到 B）"))

    # 验证 4：用户 A 不能访问 B 的项目
    r = httpx.post("http://localhost:18003/api/v1/mcp/tools/list_campaigns",
                   json={"name": "list_campaigns", "arguments": {"project_id": pid_b}},
                   headers=backend_headers_a, timeout=15)
    a_access_b = r.status_code == 200
    # 期望 A 访问 B 的项目被拒（403/404）
    results.append(print_result(not a_access_b or "error" in r.text.lower() or "permission" in r.text.lower() or "not found" in r.text.lower(),
                                "用户 A 无法访问 B 的项目（跨用户隔离）"))

    # 总结
    print_section("Block 10 测试结果")
    passed_count = sum(results)
    total_count = len(results)
    print(f"\n通过: {passed_count}/{total_count}")

    if passed_count == total_count:
        print("\n🎉 Block 10 全部通过！并发隔离安全")
        return True
    else:
        print("\n⚠️  Block 10 部分失败 —— 存在并发状态穿越风险")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_block_10())
    sys.exit(0 if success else 1)
