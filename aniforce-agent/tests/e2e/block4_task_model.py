#!/usr/bin/env python3
"""
Block 4: 通用任务模型 + DB Schema 测试

验证：
- 任务 CRUD（创建/查询/列表）
- Output CRUD（查询/验证）
- Output 状态管理（pending_review / verified）
- 数据库表结构（tasks / task_outputs / events）
"""

import sys
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


def test_block_4():
    """执行 Block 4 测试"""

    print_section("Block 4: 通用任务模型 + DB Schema 测试")

    results = []
    base_url = "http://localhost:8020"

    # 生成测试 Token
    token = create_access_token(
        {"sub": "test_user_block4", "email": "block4@example.com", "name": "Test User Block 4"}
    )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print(f"测试 Token: {token[:50]}...")

    # Step 4.1: 通过 /runs 创建任务并产生 Output
    print_section("Step 4.1: 创建任务并产生 Output")

    session_id = str(uuid.uuid4())
    run_payload = {
        "prompt": "请只回复：测试产物",
        "session_id": session_id,
        "task_type": "conversation",
        "title": "block4 output test",
        "max_turns": 1,
    }

    task_id = None
    output_id = None

    try:
        with httpx.stream("POST", f"{base_url}/api/agent/runs", json=run_payload, headers=headers, timeout=120) as response:
            print(f"状态码: {response.status_code}")
            if response.status_code != 200:
                print(f"错误: {response.read().decode()}")
                results.append(print_result(False, "创建任务失败"))
                return False

            for line in response.iter_lines():
                if line.startswith("event: "):
                    current_event = line[7:]
                elif line.startswith("data: "):
                    import json

                    data = json.loads(line[6:])
                    task_id = data.get("taskId") or task_id
                    if current_event == "TaskOutputProduced":
                        output_id = data.get("output", {}).get("output_id")
                        print(f"  产生 Output: {output_id}")

        results.append(print_result(task_id is not None, "获取到 task_id"))
        results.append(print_result(output_id is not None, "获取到 output_id"))
    except Exception as e:
        print(f"请求失败: {e}")
        results.extend([False, False])
        return False

    if not task_id or not output_id:
        print("❌ 未能获取 task_id 或 output_id，终止测试")
        return False

    # Step 4.2: 查询任务详情
    print_section("Step 4.2: 查询任务详情")

    try:
        response = httpx.get(f"{base_url}/api/agent/tasks/{task_id}", headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            task_data = response.json()
            print(f"任务详情: task_id={task_data.get('task_id')}, status={task_data.get('status')}, title={task_data.get('title')}")
            results.append(print_result(task_data.get("status") == "completed", "任务状态为 completed"))
        else:
            print(f"错误: {response.text}")
            results.append(print_result(False, "查询任务详情失败"))
    except Exception as e:
        print(f"请求失败: {e}")
        results.append(print_result(False, "查询任务详情失败"))

    # Step 4.3: 查询任务 Outputs
    print_section("Step 4.3: 查询任务 Outputs")

    try:
        response = httpx.get(f"{base_url}/api/agent/tasks/{task_id}/outputs", headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            outputs_data = response.json()
            outputs = outputs_data.get("outputs", [])
            print(f"Output 数量: {len(outputs)}")

            if len(outputs) > 0:
                output = outputs[0]
                print(f"Output 详情: output_id={output.get('output_id')}, type={output.get('type')}, status={output.get('status')}")
                results.append(print_result(output.get("type") == "text", "Output type 为 text"))
                results.append(print_result(output.get("status") == "verified", "Output status 为 verified"))
            else:
                print("❌ 未找到 Output")
                results.extend([False, False])
        else:
            print(f"错误: {response.text}")
            results.extend([False, False])
    except Exception as e:
        print(f"请求失败: {e}")
        results.extend([False, False])

    # Step 4.4: 更新 Output 状态（验证）
    print_section("Step 4.4: 更新 Output 状态")

    # 先创建一个待验证的 Output（通过新任务）
    session_id_2 = str(uuid.uuid4())
    run_payload_2 = {
        "prompt": "请回复：待验证产物",
        "session_id": session_id_2,
        "task_type": "conversation",
        "title": "block4 verify test",
        "max_turns": 1,
    }

    task_id_2 = None
    output_id_2 = None

    try:
        with httpx.stream("POST", f"{base_url}/api/agent/runs", json=run_payload_2, headers=headers, timeout=120) as response:
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line.startswith("event: "):
                        current_event = line[7:]
                    elif line.startswith("data: "):
                        import json

                        data = json.loads(line[6:])
                        task_id_2 = data.get("taskId") or task_id_2
                        if current_event == "TaskOutputProduced":
                            output_id_2 = data.get("output", {}).get("output_id")

        if output_id_2:
            # 更新状态为 verified
            update_payload = {"status": "verified"}
            response = httpx.patch(
                f"{base_url}/api/agent/tasks/outputs/{output_id_2}",
                json=update_payload,
                headers=headers,
                timeout=10,
            )
            print(f"更新状态码: {response.status_code}")

            if response.status_code == 200:
                # 再次查询确认状态已更新
                response_get = httpx.get(f"{base_url}/api/agent/tasks/{task_id_2}/outputs", headers=headers, timeout=10)
                if response_get.status_code == 200:
                    outputs_data = response_get.json()
                    output_updated = outputs_data.get("outputs", [{}])[0]
                    print(f"更新后状态: {output_updated.get('status')}")
                    results.append(print_result(output_updated.get("status") == "verified", "Output 状态更新成功"))
                else:
                    results.append(print_result(False, "查询更新后状态失败"))
            else:
                print(f"错误: {response.text}")
                results.append(print_result(False, "更新 Output 状态失败"))
        else:
            print("❌ 未获取到 output_id_2")
            results.append(print_result(False, "未获取到待验证 Output"))
    except Exception as e:
        print(f"请求失败: {e}")
        results.append(print_result(False, "更新 Output 状态失败"))

    # Step 4.5: 列出用户任务
    print_section("Step 4.5: 列出用户任务")

    try:
        response = httpx.get(f"{base_url}/api/agent/tasks?limit=10", headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            tasks_data = response.json()
            tasks = tasks_data.get("tasks", [])
            print(f"任务数量: {len(tasks)}")
            results.append(print_result(len(tasks) >= 2, "列出至少 2 个任务"))
        else:
            print(f"错误: {response.text}")
            results.append(print_result(False, "列出任务失败"))
    except Exception as e:
        print(f"请求失败: {e}")
        results.append(print_result(False, "列出任务失败"))

    # Step 4.6: 查询任务事件流
    print_section("Step 4.6: 查询任务事件流")

    try:
        response = httpx.get(f"{base_url}/api/agent/tasks/{task_id}/events", headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            events_data = response.json()
            events = events_data.get("events", [])
            print(f"事件数量: {len(events)}")
            results.append(print_result(len(events) > 0, "查询到任务事件"))
        else:
            print(f"错误: {response.text}")
            results.append(print_result(False, "查询任务事件失败"))
    except Exception as e:
        print(f"请求失败: {e}")
        results.append(print_result(False, "查询任务事件失败"))

    # 总结
    print_section("Block 4 测试结果")
    passed_count = sum(results)
    total_count = len(results)
    print(f"\n通过: {passed_count}/{total_count}")

    if passed_count == total_count:
        print("\n🎉 Block 4 全部通过！")
        return True
    else:
        print("\n⚠️  Block 4 部分失败")
        return False


if __name__ == "__main__":
    success = test_block_4()
    sys.exit(0 if success else 1)
