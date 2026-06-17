#!/usr/bin/env python3
"""
Block 2: Claude SDK 集成测试

验证：
- 真实 Claude API 调用
- 流式 SSE 输出
- 多轮对话上下文保持
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


def send_agent_run_request(prompt, session_id, token, timeout=60):
    """发送 Agent Run 请求并收集 ANIFORCE 业务 SSE 事件"""
    url = "http://localhost:8020/api/agent/runs"

    payload = {
        "prompt": prompt,
        "session_id": session_id,
        "task_type": "conversation",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    events = []
    text_content = ""
    current_event = None

    try:
        with httpx.stream("POST", url, json=payload, headers=headers, timeout=timeout) as response:
            print(f"状态码: {response.status_code}")

            if response.status_code != 200:
                print(f"错误响应: {response.text}")
                return None, None

            for line in response.iter_lines():
                if line.startswith("event: "):
                    current_event = line[7:]
                elif line.startswith("data: "):
                    try:
                        payload_data = json.loads(line[6:])
                        event_type = current_event or payload_data.get("type")
                        event = {"event": event_type, "data": payload_data}
                        events.append(event)

                        print(f"  [{event_type}]", end="")

                        if event_type == "TaskOutputDelta":
                            content = payload_data.get("delta", "")
                            text_content += content
                            if content:
                                print(f" {content[:50]}...", end="")

                        print()

                    except json.JSONDecodeError as e:
                        print(f"  [JSON 解析错误: {e}]")

    except Exception as e:
        print(f"请求失败: {e}")
        return None, None

    return events, text_content


def test_block_2():
    """执行 Block 2 测试"""
    
    print_section("Block 2: Claude SDK 集成测试")
    
    results = []
    
    # 生成测试 Token
    token = create_access_token({
        "sub": "test_user_block2",
        "email": "block2@example.com",
            "name": "Test User"
    })
    print(f"测试 Token: {token[:50]}...")
    
    # Step 2.1: 单轮对话
    print_section("Step 2.1: 单轮对话（流式响应）")
    
    thread_id = str(uuid.uuid4())

    events, text = send_agent_run_request("你好，请用一句话自我介绍", thread_id, token)

    if events:
        has_created = any(e.get("event") == "TaskCreated" for e in events)
        has_delta = any(e.get("event") == "TaskOutputDelta" for e in events)
        has_output = any(e.get("event") == "TaskOutputProduced" for e in events)
        has_completed = any(e.get("event") == "TaskCompleted" for e in events)

        print(f"\n收到事件: {len(events)} 个")
        print(f"文本内容: {text[:200]}...")

        results.append(print_result(has_created, "收到 TaskCreated"))
        results.append(print_result(has_delta and len(text) > 0, "收到有效流式文本"))
        results.append(print_result(has_output, "收到 TaskOutputProduced"))
        results.append(print_result(has_completed, "收到 TaskCompleted"))
    else:
        print("❌ 请求失败，未收到事件")
        results.extend([False, False, False, False])
    
    # Step 2.2: 多轮对话上下文保持
    print_section("Step 2.2: 多轮对话上下文保持")
    
    session_id = str(uuid.uuid4())
    
    # 第一轮：告知信息
    print("\n👤 第一轮：告知信息")
    events_1, text_1 = send_agent_run_request(
        "我的名字是张三，请简短确认你记住了（一句话）",
        session_id,
        token,
    )
    
    if not events_1:
        print("❌ 第一轮请求失败")
        results.append(False)
    else:
        print(f"\n第一轮完成，Claude 回复: {text_1[:100]}")
        
        time.sleep(2)  # 等待 Session 持久化
        
        # 第二轮：测试记忆
        print("\n👤 第二轮：测试记忆")
        events_2, text_2 = send_agent_run_request(
            "我刚才告诉你我叫什么名字？只回答名字",
            session_id,
            token,
        )
        
        if events_2:
            print(f"\n第二轮完成，Claude 回复: {text_2[:100]}")
            
            # 检查是否包含 "张三"
            has_context = "张三" in text_2 or "Zhang San" in text_2 or "张 三" in text_2
            
            results.append(print_result(has_context, "上下文保持（记住了名字）"))
        else:
            print("❌ 第二轮请求失败")
            results.append(False)
    
    # Step 2.3: 不同 Session 相互隔离
    print_section("Step 2.3: 不同 Session 相互隔离")
    
    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())
    
    # Session A：告知信息
    print("\n👤 Session A：告知幸运数字")
    events_a, text_a = send_agent_run_request(
        "我的幸运数字是 42，请简短确认",
        session_a,
        token,
    )
    
    if events_a:
        print(f"Session A 回复: {text_a[:100]}")
        
        time.sleep(1)
        
        # Session B：询问（应该不知道）
        print("\n👤 Session B：询问幸运数字")
        events_b, text_b = send_agent_run_request(
            "我刚才告诉你的幸运数字是什么？",
            session_b,
            token,
        )
        
        if events_b:
            print(f"Session B 回复: {text_b[:100]}")
            
            # Session B 不应该知道 42
            is_isolated = "42" not in text_b and "四十二" not in text_b
            
            results.append(print_result(is_isolated, "Session 隔离（Session B 不知道 A 的数据）"))
        else:
            print("❌ Session B 请求失败")
            results.append(False)
    else:
        print("❌ Session A 请求失败")
        results.append(False)
    
    # Step 2.4: Session Store 数据库验证
    print_section("Step 2.4: Session Store 数据库验证")
    try:
        import sqlite3
        db_path = Path(__file__).parent.parent.parent / "runtime" / "agent" / "sessions.db"
        
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 查询 session_id
            cursor.execute("SELECT session_id, COUNT(*) FROM sessions GROUP BY session_id")
            sessions = cursor.fetchall()
            
            print(f"\n数据库中的 Session:")
            for session_id, count in sessions:
                print(f"  - {session_id}: {count} 条记录")
            
            conn.close()
            
            results.append(print_result(len(sessions) > 0, "Session Store 有数据"))
        else:
            print(f"❌ 数据库文件不存在: {db_path}")
            results.append(False)
    
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        results.append(False)
    
    # 总结
    print_section("Block 2 测试结果")
    passed_count = sum(results)
    total_count = len(results)
    print(f"\n通过: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("\n🎉 Block 2 全部通过！")
        return True
    else:
        print("\n⚠️  Block 2 部分失败")
        print("\n常见问题排查:")
        print("1. Claude API 认证失败 → 检查 ANTHROPIC_API_KEY")
        print("2. 空响应 → 检查服务日志，可能是 SDK 初始化问题")
        print("3. 上下文丢失 → 检查 Session Store 和 session_id 传递")
        return False


if __name__ == "__main__":
    success = test_block_2()
    sys.exit(0 if success else 1)
