#!/usr/bin/env python3
"""
Block 12: 中途进入与长程状态恢复测试

重点不是完整业务流程，而是测试用户从任意业务工位进入时：
- 历史会话 resume
- 上下文感知与 DB 事实校验
- 沙箱产物 v1/v2 持续性
- 预算调整幂等保护
- HITL 写操作确认
- session 跨用户隔离

日志：logs/block12_context_resume_versioning_260618.log
"""

import asyncio
import builtins
import json
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from jose import jwt

from app.config.settings import get_settings


LOG_PATH = Path(__file__).parent.parent.parent / "logs" / "block12_context_resume_versioning_260618.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
_LOG_FILE = LOG_PATH.open("w", encoding="utf-8", buffering=1)
_ORIGINAL_PRINT = builtins.print


def print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    _ORIGINAL_PRINT(*args, **kwargs)
    file_kwargs = dict(kwargs)
    file_kwargs["file"] = _LOG_FILE
    _ORIGINAL_PRINT(*args, **file_kwargs)
    _LOG_FILE.flush()


def create_token(user_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "email": f"{user_id}@block12.local",
        "name": user_id,
        "exp": datetime.utcnow() + timedelta(hours=8),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def headers_for(user_id: str) -> dict:
    return {"Authorization": f"Bearer {create_token(user_id)}", "Content-Type": "application/json"}


def backend_headers_for(user_id: str) -> dict:
    settings = get_settings()
    headers = headers_for(user_id)
    headers["X-Internal-Token"] = settings.INTERNAL_TOKEN
    return headers


def parse_tool_text(response: dict) -> dict:
    text = response.get("content", [{}])[0].get("text", "")
    if text.startswith("Error:"):
        return {"error": text}
    try:
        return eval(text)
    except Exception:
        return {"raw": text}


def print_act(num: int, title: str):
    print("\n" + "=" * 90)
    print(f"🎬 Block12 第 {num} 幕：{title}")
    print("=" * 90)


def print_result(ok: bool, msg: str):
    print(f"{'✅' if ok else '❌'} {msg}")
    return ok


async def call_backend_tool(client: httpx.AsyncClient, user_id: str, tool_name: str, arguments: dict) -> dict:
    response = await client.post(
        "http://localhost:18003/api/v1/mcp/tools/" + tool_name,
        json={"name": tool_name, "arguments": arguments},
        headers=backend_headers_for(user_id),
        timeout=20,
    )
    return parse_tool_text(response.json())


async def seed_context(client: httpx.AsyncClient, user_id: str) -> dict:
    """准备一个非 0 起点：已有项目、两个 running 计划。"""
    suffix = uuid.uuid4().hex[:6]
    project = await call_backend_tool(
        client,
        user_id,
        "create_project",
        {"name": f"Block12Context_{suffix}", "total_budget": 60000, "description": "Block12 中途进入测试项目"},
    )
    project_id = project["id"]

    campaign_a = await call_backend_tool(
        client,
        user_id,
        "create_campaign",
        {"project_id": project_id, "name": "计划 A - Meta", "platform": "Meta", "budget": 5000, "status": "draft"},
    )
    campaign_b = await call_backend_tool(
        client,
        user_id,
        "create_campaign",
        {"project_id": project_id, "name": "计划 B - Google", "platform": "Google", "budget": 3000, "status": "draft"},
    )
    await call_backend_tool(client, user_id, "update_campaign_status", {"campaign_id": campaign_a["id"], "status": "active"})
    await call_backend_tool(client, user_id, "update_campaign_status", {"campaign_id": campaign_b["id"], "status": "active"})

    perf_a = await call_backend_tool(client, user_id, "get_campaign_performance", {"campaign_id": campaign_a["id"], "date_range": "last_7d"})
    perf_b = await call_backend_tool(client, user_id, "get_campaign_performance", {"campaign_id": campaign_b["id"], "date_range": "last_7d"})

    return {
        "project": project,
        "campaign_a": campaign_a,
        "campaign_b": campaign_b,
        "perf_a": perf_a,
        "perf_b": perf_b,
    }


async def run_agent(
    client: httpx.AsyncClient,
    user_id: str,
    session_id: str,
    prompt: str,
    title: str,
    max_turns: int = 20,
) -> Dict[str, Any]:
    """调用 /runs，追踪工具、HITL、输出。"""
    base_url = "http://localhost:8020"
    payload = {
        "prompt": prompt,
        "session_id": session_id,
        "task_type": "conversation",
        "title": title,
        "max_turns": max_turns,
    }
    current_event = None
    task_id = None
    tools = []
    outputs = []
    hitl_count = 0
    final_message = ""

    async def hitl_poller(tid: str):
        nonlocal hitl_count
        responded = set()
        start = time.time()
        async with httpx.AsyncClient(timeout=10) as hitl_client:
            while time.time() - start < 360:
                try:
                    r = await hitl_client.get(f"{base_url}/api/agent/tasks/{tid}/outputs", headers=headers_for(user_id))
                    if r.status_code == 200:
                        for out in r.json().get("outputs", []):
                            if out.get("type") == "hitl_request" and out.get("status") == "pending_review" and out.get("output_id") not in responded:
                                hitl_id = out["output_id"]
                                action = out.get("content", {}).get("action", "unknown")
                                print(f"   🔔 HITL: {action} -> auto approve")
                                resp = await hitl_client.post(
                                    f"{base_url}/api/agent/hitl/{hitl_id}/respond",
                                    headers=headers_for(user_id),
                                    json={"approved": True, "feedback": "block12 auto approve"},
                                )
                                responded.add(hitl_id)
                                if resp.status_code == 200:
                                    hitl_count += 1
                except Exception as exc:
                    print(f"   ⚠️ HITL poll error: {type(exc).__name__}: {exc}")
                await asyncio.sleep(1)

    poller = None
    stream_timeout = httpx.Timeout(connect=10, read=None, write=10, pool=10)
    async with client.stream("POST", f"{base_url}/api/agent/runs", json=payload, headers=headers_for(user_id), timeout=stream_timeout) as response:
        if response.status_code != 200:
            body = await response.aread()
            return {"http_status": response.status_code, "error": body.decode()[:500]}

        async for line in response.aiter_lines():
            if line.startswith("event: "):
                current_event = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                if current_event == "TaskCreated":
                    task_id = data.get("taskId")
                    print(f"   🧩 task_id={task_id} session_id={session_id}")
                    poller = asyncio.create_task(hitl_poller(task_id))
                elif current_event == "TaskProgressUpdated":
                    tool = data.get("progress", {}).get("tool")
                    if isinstance(tool, dict):
                        tool_name = tool.get("name", "")
                        tools.append(tool_name)
                        print(f"   🔧 tool={tool_name}")
                elif current_event == "TaskOutputProduced":
                    output = data.get("output", {})
                    outputs.append(output)
                    text = str(output.get("content", ""))[:180].replace("\n", " ")
                    print(f"   📋 output={output.get('type')}:{output.get('category')} {text}")
                elif current_event == "TaskCompleted":
                    final_message = json.dumps(data.get("summary", {}), ensure_ascii=False)

    if poller:
        poller.cancel()
        try:
            await poller
        except asyncio.CancelledError:
            pass

    return {"task_id": task_id, "tools": tools, "outputs": outputs, "hitl_count": hitl_count, "final_message": final_message}


async def main() -> int:
    print("=" * 90)
    print("🎯 Block 12: 中途进入与长程状态恢复测试")
    print(f"日志文件: {LOG_PATH}")
    print("=" * 90)

    user_a = "user_block12_a"
    user_b = "user_block12_b"
    session_id = str(uuid.uuid4())
    settings = get_settings()
    sandbox_workspace = (Path(settings.RUNTIME_DIR) / session_id / "workspace").resolve()
    results = []

    async with httpx.AsyncClient() as client:
        print_act(0, "Seed 已有业务上下文（不是从创建项目开始）")
        ctx = await seed_context(client, user_a)
        project_id = ctx["project"]["id"]
        campaign_a_id = ctx["campaign_a"]["id"]
        campaign_b_id = ctx["campaign_b"]["id"]
        print(f"项目={project_id}")
        print(f"计划A={campaign_a_id} ROI={ctx['perf_a']['metrics']['roi']} budget=5000")
        print(f"计划B={campaign_b_id} ROI={ctx['perf_b']['metrics']['roi']} budget=3000")
        low_campaign = campaign_a_id if ctx["perf_a"]["metrics"]["roi"] < ctx["perf_b"]["metrics"]["roi"] else campaign_b_id
        high_campaign = campaign_b_id if low_campaign == campaign_a_id else campaign_a_id
        low_name = "计划 A" if low_campaign == campaign_a_id else "计划 B"
        high_name = "计划 B" if high_campaign == campaign_b_id else "计划 A"
        print(f"低 ROI 计划={low_name}({low_campaign})；高 ROI 计划={high_name}({high_campaign})")

        print_act(1, "中途进入：复盘工位生成报告 v1 + 沙箱文件")
        prompt1 = f"""
我是投放经理，不是从头开始。请接手已有项目 {project_id}。
已有两个投放计划：计划 A={campaign_a_id}，计划 B={campaign_b_id}。
请先重新查询 DB/工具里的当前计划与过去 7 天投放数据，以 DB 和工具结果为事实源，不要只相信我的描述。
然后生成一份分析报告 v1，并必须用 Write 工具保存到这个沙箱绝对路径：{sandbox_workspace / 'analysis_report_v1.md'}。
报告里明确标注 performance 是 Mock 数据。不要写入 /workspace 根目录。
"""
        r1 = await run_agent(client, user_a, session_id, prompt1, "block12 act1 report v1")
        v1_file = sandbox_workspace / "analysis_report_v1.md"
        results.append(print_result(r1.get("task_id") is not None, "Act1 任务完成"))
        results.append(print_result(any("get_campaign_performance" in t for t in r1.get("tools", [])), "Act1 重新查询 performance（DB/工具事实源）"))
        results.append(print_result(v1_file.exists(), f"Act1 沙箱报告 v1 存在: {v1_file}"))

        print_act(2, "历史会话 resume：从素材工位切入生成 v2，不覆盖 v1")
        prompt2 = f"""
继续刚才那份报告。现在我是素材同学，从素材工位进入系统。
请根据上一轮分析识别“表现差的那个计划”，不要让我重复提供计划 ID。
为表现差计划生成一版新的夏季促销素材方向（Mock AI 生成即可），并基于 v1 生成更新版报告 v2。
必须先 Read 这个沙箱文件：{sandbox_workspace / 'analysis_report_v1.md'}。
然后必须立刻调用 Write 工具，把新版报告写到：{sandbox_workspace / 'analysis_report_v2.md'}。
不允许只说“现在生成 v2”，必须实际完成 Write 后再回复；不允许覆盖 v1，也不要写入 /workspace 根目录。
"""
        r2 = await run_agent(client, user_a, session_id, prompt2, "block12 act2 report v2")
        v2_file = sandbox_workspace / "analysis_report_v2.md"
        if not v2_file.exists():
            print("   ⚠️ Act2 首次未落 v2 文件，执行半完成恢复：只补写 v2，不重复生成素材")
            recover_prompt = f"""
上一轮你已经读取 v1 并生成了素材，但没有实际写入 v2 文件。现在只做恢复动作：
1. Read {sandbox_workspace / 'analysis_report_v1.md'}；
2. 基于上一轮素材建议和 v1 内容，必须调用 Write 写入 {sandbox_workspace / 'analysis_report_v2.md'}；
3. 不要重新调用 generate_material_ai，不要覆盖 v1，不要写入 /workspace 根目录。
"""
            r2_recover = await run_agent(client, user_a, session_id, recover_prompt, "block12 act2 recover v2", max_turns=12)
            r2["tools"].extend(r2_recover.get("tools", []))
            r2["outputs"].extend(r2_recover.get("outputs", []))
        results.append(print_result(any("generate_material_ai" in t for t in r2.get("tools", [])), "Act2 识别低 ROI 计划并生成素材方案"))
        results.append(print_result(v1_file.exists() and v2_file.exists(), "Act2 v1/v2 沙箱文件同时存在"))
        if v1_file.exists() and v2_file.exists():
            results.append(print_result(v1_file.read_text(encoding="utf-8") != v2_file.read_text(encoding="utf-8"), "Act2 v2 未覆盖 v1，内容有演进"))
        else:
            results.append(False)

        print_act(3, "预算工位：保守预算调整 + HITL + budget_plan_v1")
        prompt3 = f"""
我是审批人。基于刚才的报告 v2，执行一个保守预算调整：低 ROI 的计划减少 500，高 ROI 的计划增加 500，总预算不变。
执行前必须 confirm_action 确认。执行后必须 Write 到沙箱绝对路径 {sandbox_workspace / 'budget_plan_v1.json'}，记录 old_budget/new_budget/campaign_id/reason/version。
不要写入 /workspace 根目录。
"""
        before_low = 5000 if low_campaign == campaign_a_id else 3000
        before_high = 3000 if high_campaign == campaign_b_id else 5000
        r3 = await run_agent(client, user_a, session_id, prompt3, "block12 act3 budget v1")
        budget_file = sandbox_workspace / "budget_plan_v1.json"
        campaigns_after = await call_backend_tool(client, user_a, "list_campaigns", {"project_id": project_id, "limit": 10})
        campaign_map = {c["id"]: c for c in campaigns_after.get("campaigns", [])}
        low_budget_after = campaign_map.get(low_campaign, {}).get("budget")
        high_budget_after = campaign_map.get(high_campaign, {}).get("budget")
        results.append(print_result(r3.get("hitl_count", 0) >= 1, "Act3 预算写操作前 HITL"))
        results.append(print_result(any("update_campaign_budget" in t for t in r3.get("tools", [])), "Act3 调用了预算更新工具"))
        results.append(print_result(low_budget_after == before_low - 500 and high_budget_after == before_high + 500, f"Act3 DB 预算符合保守调整: low={low_budget_after}, high={high_budget_after}"))
        results.append(print_result(budget_file.exists(), f"Act3 budget_plan_v1.json 存在: {budget_file}"))

        print_act(4, "幂等保护：重复执行同一预算调整，不应再次修改")
        prompt4 = f"""
重复执行刚才那个预算调整。
注意：如果你发现 budget_plan_v1 已经执行过，或者 DB 当前预算已经等于调整后的目标值，就不要再次调用 update_campaign_budget。
请先 Read 沙箱文件 {sandbox_workspace / 'budget_plan_v1.json'} 并查询 DB 当前预算，然后说明是否跳过。
不要写入 /workspace 根目录。
"""
        r4 = await run_agent(client, user_a, session_id, prompt4, "block12 act4 idempotency")
        campaigns_after_repeat = await call_backend_tool(client, user_a, "list_campaigns", {"project_id": project_id, "limit": 10})
        campaign_map_repeat = {c["id"]: c for c in campaigns_after_repeat.get("campaigns", [])}
        low_budget_repeat = campaign_map_repeat.get(low_campaign, {}).get("budget")
        high_budget_repeat = campaign_map_repeat.get(high_campaign, {}).get("budget")
        no_repeat_tool = not any("update_campaign_budget" in t for t in r4.get("tools", []))
        budgets_unchanged = low_budget_repeat == low_budget_after and high_budget_repeat == high_budget_after
        results.append(print_result(no_repeat_tool, "Act4 未重复调用预算更新工具"))
        results.append(print_result(budgets_unchanged, f"Act4 DB 预算未重复变化: low={low_budget_repeat}, high={high_budget_repeat}"))

        print_act(5, "跨用户 session 安全：用户 B 不能 resume 用户 A 会话")
        forbidden = await client.post(
            "http://localhost:8020/api/agent/runs",
            headers=headers_for(user_b),
            json={
                "prompt": "继续刚才那个 LongTaskDemo 项目，告诉我项目和计划详情。",
                "session_id": session_id,
                "task_type": "conversation",
                "title": "block12 user b forbidden",
                "max_turns": 3,
            },
            timeout=20,
        )
        results.append(print_result(forbidden.status_code == 403, f"Act5 跨用户复用 session 被拒绝: status={forbidden.status_code}"))

    print("\n" + "=" * 90)
    print("🎯 Block 12 验证结果")
    print("=" * 90)
    passed = sum(1 for x in results if x)
    total = len(results)
    print(f"通过: {passed}/{total}")
    if passed == total:
        print("🎉 Block 12A 全部通过：中途进入、resume、沙箱版本、幂等、安全隔离成立")
        return 0
    print("⚠️ Block 12A 存在失败项，请查看日志和 DB")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
