#!/usr/bin/env python3
"""
Block 2: OpenAI SDK 集成测试

验证：
- 真实 OpenAI/兼容 API 调用（deepseek 模型）
- 流式 SSE 输出（AgentTaskEvent）
- 多轮对话上下文保持（SQLiteSession）
- Session 隔离
"""

import sys
import httpx
import json
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.auth import create_access_token


def print_section(title):
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def print_result(passed, message):
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


def send_agent_run(prompt, session_id, token, timeout=60):
    """发送 /api/agent/runs 请求，收集 SSE 事件"""
    url = "http://localhost:8020/api/agent/runs"
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
    text_content = ""
    current_event = None

    try:
        with httpx.stream("POST", url, json=payload, headers=headers, timeout=timeout) as response:
            print(f"状态码: {response.status_code}")
            if response.status_code != 200:
                print(f"错误响应: {response.text[:500]}")
                return events, text_content

            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                elif line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    events.append({"event": current_event, "data": data})

                    # 累积文本 delta
                    if current_event == "message.updated":
                        text_content += data.get("delta", "")
                    elif current_event == "message.completed":
                        text_content = data.get("content", text_content)
    except Exception as e:
        print(f"请求错误: {e}")

    return events, text_content


def test_block_2():
    """执行 Block 2 测试"""
    print_section("Block 2: OpenAI SDK 集成测试")

    token = create_access_token({"sub": "user_test_001", "email": "test@animagus.com", "name": "Test"})
    results = []

    # Step 2.1: 单轮对话（流式）
    print_section("Step 2.1: 单轮对话（流式 SSE）")
    session_id = f"session_{uuid.uuid4().hex[:16]}"
    print(f"Session: {session_id}")

    t0 = time.time()
    events, text = send_agent_run("你好，请回复'收到'", session_id, token, timeout=60)
    elapsed = time.time() - t0
    print(f"耗时: {elapsed:.2f}s")
    print(f"事件数: {len(events)}")
    print(f"事件类型: {[e['event'] for e in events]}")
    print(f"回复内容: {text[:200]}")

    results.append(print_result(len(events) > 0, "收到 SSE 事件"))
    results.append(print_result(
        any(e["event"] == "runtime.started" for e in events),
        "runtime.started 事件"
    ))
    results.append(print_result(
        any(e["event"] == "message.updated" for e in events),
        "message.updated（流式 delta）"
    ))
    results.append(print_result(
        any(e["event"] == "message.completed" for e in events),
        "message.completed 事件"
    ))
    results.append(print_result(
        any(e["event"] == "runtime.completed" for e in events),
        "runtime.completed 事件"
    ))
    results.append(print_result(
        bool(text.strip()),
        f"有文本回复（内容: {text[:50]}）"
    ))
    results.append(print_result(
        elapsed < 30,
        f"响应时间 < 30s（实际 {elapsed:.1f}s）"
    ))

    # Step 2.2: 多轮对话上下文保持
    print_section("Step 2.2: 多轮对话上下文保持（同一 session）")
    print(f"复用 Session: {session_id}")
    print("第2轮: '我上一条消息说了什么？'")

    events2, text2 = send_agent_run("我上一条消息说了什么？", session_id, token, timeout=60)
    print(f"回复: {text2[:200]}")

    # 验证模型记得上文（回复里应该提到"收到"）
    remembers = "收到" in text2 or "你好" in text2
    results.append(print_result(remembers, f"模型记得上文（回复含上文关键词）"))

    # Step 2.3: Session 隔离
    print_section("Step 2.3: Session 隔离（新 session 不记得上文）")
    new_session = f"session_{uuid.uuid4().hex[:16]}"
    print(f"新 Session: {new_session}")
    events3, text3 = send_agent_run("我上一条消息说了什么？", new_session, token, timeout=60)
    print(f"回复: {text3[:200]}")

    forgets = "收到" not in text3 and "不知道" in text3 or "没有" in text3 or "首次" in text3 or "第一" in text3
    results.append(print_result(forgets, "新 session 不记得上文（隔离生效）"))

    # 汇总
    print_section("Block 2 汇总")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    return passed == total


if __name__ == "__main__":
    success = test_block_2()
    sys.exit(0 if success else 1)
