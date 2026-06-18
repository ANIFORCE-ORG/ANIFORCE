#!/usr/bin/env python3
"""
Block 3: 业务事件系统测试

验证：
- /api/agent/runs 新入口
- TaskCreated / TaskProgressUpdated / TaskOutputDelta / TaskOutputProduced / TaskCompleted 事件流
- 运行元数据（model / tools / skills / telemetry）
- 数据库落盘（tasks / events / task_outputs）
"""

import sys
import json
import sqlite3
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from app.core.auth import create_access_token


def print_section(title):
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def print_result(passed, message):
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


def test_block_3():
    """执行 Block 3 测试"""
    
    print_section("Block 3: 业务事件系统测试")
    
    results = []
    
    # 生成测试 Token
    token = create_access_token({
        "sub": "test_user_block3",
        "email": "block3@example.com",
        "name": "Test User Block 3"
    })
    print(f"测试 Token: {token[:50]}...")
    
    # Step 3.1: 新入口可用
    print_section("Step 3.1: /api/agent/runs 入口测试")
    
    session_id = str(uuid.uuid4())
    payload = {
        "prompt": "请只回复一句话：收到",
        "session_id": session_id,
        "task_type": "conversation",
        "title": "block3 test",
        "max_turns": 1,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"session_id: {session_id}")
    
    events = []
    text_delta = []
    task_id = None
    
    try:
        with httpx.stream(
            "POST",
            "http://localhost:8020/api/agent/runs",
            json=payload,
            headers=headers,
            timeout=120
        ) as response:
            print(f"状态码: {response.status_code}")
            
            if response.status_code != 200:
                print(f"错误响应: {response.read().decode()}")
                results.append(print_result(False, "新入口请求失败"))
                return False
            
            current_event = None
            for line in response.iter_lines():
                if line.startswith("event: "):
                    current_event = line[7:]
                elif line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append((current_event, data))
                    task_id = data.get("taskId") or task_id
                    
                    if current_event == "TaskOutputDelta":
                        text_delta.append(data.get("delta", ""))
                    
                    # 打印关键事件
                    if current_event in {"TaskCreated", "TaskOutputProduced", "TaskCompleted"}:
                        print(f"  [{current_event}] {str(data)[:200]}")
        
        results.append(print_result(True, "新入口请求成功"))
    
    except Exception as e:
        print(f"请求失败: {e}")
        results.append(print_result(False, "新入口请求失败"))
        return False
    
    # Step 3.2: 事件流完整性
    print_section("Step 3.2: 事件流完整性检查")
    
    event_types = {evt_type for evt_type, _ in events}
    
    has_created = "TaskCreated" in event_types
    has_progress = "TaskProgressUpdated" in event_types
    has_delta = "TaskOutputDelta" in event_types
    has_output = "TaskOutputProduced" in event_types
    has_completed = "TaskCompleted" in event_types
    
    print(f"\n收到事件类型: {sorted(event_types)}")
    print(f"总事件数: {len(events)}")
    print(f"流式文本: {repr(''.join(text_delta)[:100])}")
    
    results.append(print_result(has_created, "收到 TaskCreated"))
    results.append(print_result(has_progress, "收到 TaskProgressUpdated"))
    results.append(print_result(has_delta, "收到 TaskOutputDelta"))
    results.append(print_result(has_output, "收到 TaskOutputProduced"))
    results.append(print_result(has_completed, "收到 TaskCompleted"))
    results.append(print_result(len(text_delta) > 0, "文本增量非空"))
    
    # Step 3.3: 运行元数据检查
    print_section("Step 3.3: 运行元数据检查")
    
    # 找一个 TaskCompleted 事件检查元数据
    completed_event = next((data for evt, data in events if evt == "TaskCompleted"), None)
    
    if completed_event:
        runtime = completed_event.get("runtime", {})
        telemetry = completed_event.get("summary", {})
        
        has_model = runtime.get("model") is not None
        has_tools = isinstance(runtime.get("tools"), list) and len(runtime.get("tools", [])) > 0
        has_skills = isinstance(runtime.get("skills"), list)
        has_duration = telemetry.get("duration") is not None
        has_cost = telemetry.get("cost") is not None
        
        print(f"\nruntime.model: {runtime.get('model')}")
        print(f"runtime.tools: {len(runtime.get('tools', []))} 个")
        print(f"runtime.skills: {runtime.get('skills', [])}")
        print(f"telemetry.duration: {telemetry.get('duration')} ms")
        print(f"telemetry.cost: ${telemetry.get('cost')}")
        
        results.append(print_result(has_model, "运行元数据包含 model"))
        results.append(print_result(has_tools, "运行元数据包含 tools"))
        results.append(print_result(has_skills, "运行元数据包含 skills"))
        results.append(print_result(has_duration, "telemetry 包含 duration"))
        results.append(print_result(has_cost, "telemetry 包含 cost"))
    else:
        print("❌ 未找到 TaskCompleted 事件")
        results.extend([False] * 5)
    
    # Step 3.4: 数据库落盘检查
    print_section("Step 3.4: 数据库落盘检查")
    
    try:
        db_path = Path(__file__).parent.parent.parent / "runtime" / "agent" / "tasks.db"
        
        if not db_path.exists():
            print(f"❌ 数据库文件不存在: {db_path}")
            results.extend([False] * 3)
        else:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            
            # 检查 tasks 表
            cur.execute(
                "SELECT task_id, task_type, status, title FROM tasks WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,)
            )
            task_row = cur.fetchone()
            print(f"\ntasks 表: {task_row}")
            results.append(print_result(task_row is not None, "tasks 表有记录"))
            
            # 检查 events 表
            if task_id:
                cur.execute(
                    "SELECT event_type, COUNT(*) FROM events WHERE task_id = ? GROUP BY event_type ORDER BY event_type",
                    (task_id,)
                )
                event_counts = cur.fetchall()
                print(f"events 表: {event_counts}")
                results.append(print_result(len(event_counts) > 0, "events 表有记录"))
                
                # 检查 task_outputs 表
                cur.execute(
                    "SELECT output_id, output_type, category, status FROM task_outputs WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
                    (task_id,)
                )
                output_row = cur.fetchone()
                print(f"task_outputs 表: {output_row}")
                results.append(print_result(output_row is not None and output_row[1] == "text", "task_outputs 表有 text 类型记录"))
            else:
                print("❌ 未获取到 task_id")
                results.extend([False] * 2)
            
            conn.close()
    
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        results.extend([False] * 3)
    
    # 总结
    print_section("Block 3 测试结果")
    passed_count = sum(results)
    total_count = len(results)
    print(f"\n通过: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("\n🎉 Block 3 全部通过！")
        return True
    else:
        print("\n⚠️  Block 3 部分失败")
        return False


if __name__ == "__main__":
    success = test_block_3()
    sys.exit(0 if success else 1)
