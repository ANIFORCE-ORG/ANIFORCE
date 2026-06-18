#!/usr/bin/env python3
"""
Block 11: 长程任务全链路验证 —— 从创建到投放到数据分析

完整业务流程（10 个阶段）：
1. 创建项目
2. 创建两个广告计划（A 和 B）
3. AI 生成素材
4. 编辑/创建更多素材
5. 发起投放（更新状态为 active）
6. 【模拟时间流逝】
7. 获取投放数据
8. 对比分析两个计划的 ROI
9. 生成分析报告
10. 调整预算（把预算从低 ROI 计划挪到高 ROI 计划）

验证目标：
- Agent 能完成多步骤复杂任务
- 跨轮对话保持上下文（resume）
- HITL 确认在关键操作
- Mock 工具能展示完整能力
- 日志层面可追溯每个 action
"""

import sys
import asyncio
import json
import uuid
import time
import builtins
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from app.core.auth import create_access_token
from app.config.settings import get_settings


LOG_PATH = Path(__file__).parent.parent.parent / "logs" / "block11_long_task_260618.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
_LOG_FILE = LOG_PATH.open("w", encoding="utf-8", buffering=1)
_ORIGINAL_PRINT = builtins.print


def print(*args, **kwargs):
    """同时输出到控制台和日志文件，逐行 flush，便于 tail -f 实时查看。"""
    kwargs.setdefault("flush", True)
    _ORIGINAL_PRINT(*args, **kwargs)
    file_kwargs = dict(kwargs)
    file_kwargs["file"] = _LOG_FILE
    _ORIGINAL_PRINT(*args, **file_kwargs)
    _LOG_FILE.flush()


# ============================================================
# 剧本日志工具
# ============================================================

def safe_eval_response(text: str) -> dict:
    """安全解析后端响应（处理 Error 情况）"""
    if text.startswith("Error:"):
        return {}
    try:
        return eval(text)
    except Exception:
        return {}

def print_act(act_num: int, title: str):
    """打印幕次标题"""
    print("\n" + "=" * 80)
    print(f"🎬 第 {act_num} 幕：{title}")
    print("=" * 80)


def print_pm(message: str):
    """打印 PM 的话"""
    print(f"👤 [PM] {message}")


def print_agent_action(action: str):
    """打印 Agent 动作"""
    print(f"🤖 [Agent] {action}")


def print_tool_call(tool_name: str, args: Optional[Dict] = None):
    """打印工具调用"""
    args_str = f" | {args}" if args else ""
    print(f"   🔧 工具调用: {tool_name}{args_str}")


def print_hitl(action: str, approved: bool):
    """打印 HITL 确认"""
    status = "✅ 确认" if approved else "❌ 拒绝"
    print(f"   🔔 HITL 请求: {action} → {status}")


def print_output(output_type: str, category: str, summary: str):
    """打印产出"""
    print(f"   📋 产出: type={output_type}, category={category}")
    if summary:
        print(f"      {summary[:100]}")


def print_result(passed: bool, message: str):
    """打印验证结果"""
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")


def print_act_complete(act_num: int):
    """打印幕次完成"""
    print(f"✅ 第 {act_num} 幕完成\n")


# ============================================================
# SSE 消费与工具追踪
# ============================================================

async def run_and_track(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    prompt: str,
    session_id: str,
    timeout: float = 180,
) -> Dict[str, Any]:
    """
    发起一次 /runs 并追踪工具调用、HITL、产出
    
    Returns:
        {
            "task_id": str,
            "tools": [tool_name, ...],
            "hitl_count": int,
            "outputs": [output, ...],
            "final_message": str,
        }
    """
    payload = {
        "prompt": prompt,
        "session_id": session_id,
        "task_type": "conversation",
        "title": f"Act {prompt[:20]}",
        "max_turns": 20,
    }
    
    task_id = None
    tools = []
    hitl_count = 0
    outputs = []
    final_message = ""
    current_event = None

    async def hitl_poller(tid: str):
        """自动响应 HITL（模拟 PM 确认），支持同一轮内连续多个 HITL。"""
        nonlocal hitl_count
        responded_ids = set()
        start = time.time()
        async with httpx.AsyncClient(timeout=10) as hitl_client:
            while time.time() - start < timeout:
                try:
                    r = await hitl_client.get(
                        f"{base_url}/api/agent/tasks/{tid}/outputs",
                        headers=headers,
                    )
                    if r.status_code == 200:
                        for out in r.json().get("outputs", []):
                            if (
                                out.get("type") == "hitl_request"
                                and out.get("status") == "pending_review"
                                and out.get("output_id") not in responded_ids
                            ):
                                hitl_id = out["output_id"]
                                content = out.get("content", {})
                                action = content.get("action", "unknown")
                                print_hitl(action, True)
                                resp = await hitl_client.post(
                                    f"{base_url}/api/agent/hitl/{hitl_id}/respond",
                                    json={"approved": True, "feedback": "auto approve"},
                                    headers=headers,
                                )
                                responded_ids.add(hitl_id)
                                if resp.status_code == 200:
                                    hitl_count += 1
                                else:
                                    print(f"   ⚠️ HITL 响应失败: {hitl_id}, status={resp.status_code}")
                except Exception as e:
                    print(f"   ⚠️ HITL 轮询异常: {type(e).__name__}: {e}")
                await asyncio.sleep(1)

    poller = None
    stream_timeout = httpx.Timeout(connect=10, read=None, write=10, pool=10)
    async with client.stream(
        "POST", f"{base_url}/api/agent/runs", json=payload, headers=headers, timeout=stream_timeout
    ) as response:
        if response.status_code != 200:
            body = await response.aread()
            print(f"❌ HTTP {response.status_code}: {body.decode()[:200]}")
            return {}

        async for line in response.aiter_lines():
            if line.startswith("event: "):
                current_event = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                
                if current_event == "TaskCreated":
                    task_id = data.get("taskId")
                    poller = asyncio.create_task(hitl_poller(task_id))
                
                elif current_event == "TaskProgressUpdated":
                    tool_info = data.get("progress", {}).get("tool")
                    if tool_info and isinstance(tool_info, dict):
                        tool_name = tool_info.get("name", "")
                        tools.append(tool_name)
                        print_tool_call(tool_name)
                
                elif current_event == "TaskOutputProduced":
                    output = data.get("output", {})
                    outputs.append(output)
                    print_output(
                        output.get("type", ""),
                        output.get("category", ""),
                        str(output.get("content", ""))[:100]
                    )
                
                elif current_event == "TaskCompleted":
                    final_message = data.get("result", {}).get("message", "")

    if poller:
        poller.cancel()
        try:
            await poller
        except asyncio.CancelledError:
            pass

    return {
        "task_id": task_id,
        "tools": tools,
        "hitl_count": hitl_count,
        "outputs": outputs,
        "final_message": final_message,
    }


# ============================================================
# Block 11 长程任务测试
# ============================================================

async def test_block_11():
    """执行 Block 11 长程任务测试"""
    
    print("=" * 80)
    print("🎯 Block 11: 长程任务全链路验证")
    print("   从创建项目 → 投放 → 数据分析 → 预算调整")
    print(f"   日志文件: {LOG_PATH}")
    print("=" * 80)
    
    base_url = "http://localhost:8020"
    settings = get_settings()
    user_id = "user_long_task_demo"
    token = create_access_token({"sub": user_id, "email": "demo@long.com", "name": "Long Task Demo"})
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    session_id = str(uuid.uuid4())
    results = []
    
    # 用于跟踪关键 ID
    project_id = None
    campaign_a_id = None
    campaign_b_id = None
    
    async with httpx.AsyncClient() as client:
        
        # ========== 第 1 幕：创建项目 ==========
        print_act(1, "创建项目")
        print_pm("创建项目 LongTaskDemo，总预算 50000")
        
        result = await run_and_track(
            client, base_url, headers,
            "创建项目 LongTaskDemo，总预算 50000。创建前请确认。",
            session_id
        )
        
        # 从工具调用中提取 project_id（简化：从 final_message 或手动查）
        # 这里简化，直接查后端
        r = httpx.post(
            "http://localhost:18003/api/v1/mcp/tools/list_projects",
            json={"name": "list_projects", "arguments": {"limit": 1}},
            headers={**headers, "X-Internal-Token": settings.INTERNAL_TOKEN},
            timeout=10
        )
        projects = safe_eval_response(r.json()["content"][0]["text"]).get("projects", [])
        project_id = projects[0]["id"] if projects else None
        
        print_agent_action(f"项目已创建，ID={project_id}")
        results.append(result.get("hitl_count", 0) > 0)
        print_result(results[-1], f"HITL 确认: {result.get('hitl_count', 0)} 次")
        print_act_complete(1)
        
        # ========== 第 2 幕：创建两个广告计划 ==========
        print_act(2, "创建两个广告计划")
        print_pm("在 LongTaskDemo 项目下创建两个计划：A（Meta，预算 5000）和 B（Google，预算 3000）")
        
        result = await run_and_track(
            client, base_url, headers,
            f"在项目 {project_id} 下创建两个广告计划：计划 A，平台 Meta，预算 5000；计划 B，平台 Google，预算 3000。创建前请分别确认。",
            session_id
        )
        
        # 查计划 ID
        r = httpx.post(
            "http://localhost:18003/api/v1/mcp/tools/list_campaigns",
            json={"name": "list_campaigns", "arguments": {"project_id": project_id, "limit": 10}},
            headers={**headers, "X-Internal-Token": settings.INTERNAL_TOKEN},
            timeout=10
        )
        campaigns = safe_eval_response(r.json()["content"][0]["text"]).get("campaigns", [])
        for c in campaigns:
            if "A" in c["name"] or "a" in c["name"].lower():
                campaign_a_id = c["id"]
            elif "B" in c["name"] or "b" in c["name"].lower():
                campaign_b_id = c["id"]
        
        print_agent_action(f"计划 A: {campaign_a_id}, 计划 B: {campaign_b_id}")
        results.append(len(result.get("tools", [])) >= 2)
        print_result(results[-1], f"工具调用: {len(result.get('tools', []))} 次")
        print_act_complete(2)
        
        # ========== 第 3 幕：AI 生成素材 ==========
        print_act(3, "AI 生成素材")
        print_pm("为计划 A 生成 3 张广告图，主题：夏季促销")
        
        result = await run_and_track(
            client, base_url, headers,
            f"为项目 {project_id} 的计划 A 生成 3 张广告图，主题：夏季促销，色调清新",
            session_id
        )
        
        has_ai_gen = any("generate_material_ai" in t for t in result.get("tools", []))
        ai_output_text = str(result.get("outputs", [])) + result.get("final_message", "")
        ai_success = has_ai_gen and "错误" not in ai_output_text and "Error" not in ai_output_text
        results.append(ai_success)
        print_result(results[-1], f"AI 生成素材成功: tool_called={has_ai_gen}, no_error={ai_success}")
        print_act_complete(3)
        
        # ========== 第 4 幕：创建更多素材 ==========
        print_act(4, "手动创建素材")
        print_pm("为计划 B 创建 2 个文案素材")
        
        result = await run_and_track(
            client, base_url, headers,
            f"为项目 {project_id} 的计划 B 创建 2 个文案素材，内容：'全场 8 折' 和 '新品上市'",
            session_id
        )
        
        has_create = any("create_material" in t for t in result.get("tools", []))
        results.append(has_create)
        print_result(results[-1], f"创建素材工具调用: {has_create}")
        print_act_complete(4)
        
        # ========== 第 5 幕：发起投放 ==========
        print_act(5, "发起投放")
        print_pm("把计划 A 和 B 都设置为 active 状态，开始投放")
        
        result = await run_and_track(
            client, base_url, headers,
            f"把计划 A ({campaign_a_id}) 和计划 B ({campaign_b_id}) 的状态改为 active，开始投放。操作前请确认。",
            session_id
        )
        
        has_status = any("update_campaign_status" in t for t in result.get("tools", []))
        results.append(has_status)
        print_result(results[-1], f"更新状态工具调用: {has_status}")
        print_act_complete(5)
        
        # ========== 第 6 幕：模拟时间流逝 ==========
        print_act(6, "模拟时间流逝（7 天后）")
        print("⏰ 【模拟：7 天后，PM 回来查看数据】")
        print_act_complete(6)
        
        # ========== 第 7 幕：获取投放数据 ==========
        print_act(7, "获取投放数据")
        print_pm("查看计划 A 和 B 过去 7 天的投放数据")
        
        result = await run_and_track(
            client, base_url, headers,
            f"查看计划 A ({campaign_a_id}) 和计划 B ({campaign_b_id}) 过去 7 天的投放数据，包括展示、点击、花费、转化、ROI",
            session_id
        )
        
        has_perf = any("get_campaign_performance" in t for t in result.get("tools", []))
        results.append(has_perf)
        print_result(results[-1], f"性能数据工具调用: {has_perf}")
        print_act_complete(7)
        
        # ========== 第 8 幕：对比分析 ==========
        print_act(8, "对比分析")
        print_pm("对比 A 和 B，哪个 ROI 更好？给出详细分析")
        
        result = await run_and_track(
            client, base_url, headers,
            f"对比计划 A 和计划 B 的投放数据，分析哪个 ROI 更好，给出详细的数据对比和优化建议",
            session_id
        )
        
        has_analysis = len(result.get("outputs", [])) > 0
        results.append(has_analysis)
        print_result(results[-1], f"分析产出: {len(result.get('outputs', []))} 个")
        print_act_complete(8)
        
        # ========== 第 9 幕：调整预算 ==========
        print_act(9, "预算调整")
        print_pm("根据数据分析，把 ROI 低的计划的预算调低 1000，ROI 高的加 1000")
        
        result = await run_and_track(
            client, base_url, headers,
            f"根据前面的分析，调整预算：ROI 低的计划减少 1000 预算，ROI 高的计划增加 1000 预算。调整前请确认。",
            session_id
        )
        
        has_budget = any("update_campaign_budget" in t for t in result.get("tools", []))
        results.append(has_budget)
        print_result(results[-1], f"预算调整工具调用: {has_budget}")
        print_act_complete(9)
        
        # ========== 第 10 幕：总结 ==========
        print_act(10, "任务总结")
        print_pm("总结一下我们完成了什么")
        
        result = await run_and_track(
            client, base_url, headers,
            "总结一下这次任务，我们从创建项目开始，做了哪些事情，最终的优化结果是什么",
            session_id
        )
        
        print_agent_action("任务总结完成")
        print_act_complete(10)
    
    # ========== 最终验证 ==========
    print("\n" + "=" * 80)
    print("🎯 Block 11 验证结果")
    print("=" * 80)
    
    checklist = [
        "HITL 确认（创建项目）",
        "创建计划工具调用",
        "AI 生成素材工具调用",
        "创建素材工具调用",
        "更新状态工具调用",
        "获取性能数据工具调用",
        "分析产出生成",
        "预算调整工具调用",
    ]
    
    for i, item in enumerate(checklist):
        print_result(results[i] if i < len(results) else False, item)
    
    passed_count = sum(results)
    total_count = len(checklist)
    print(f"\n通过: {passed_count}/{total_count}")
    
    if passed_count >= total_count - 1:  # 允许 1 个失败
        print("\n🎉 Block 11 基本通过！Agent 完成长程任务全链路")
        return True
    else:
        print("\n⚠️  Block 11 部分失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_block_11())
    sys.exit(0 if success else 1)
