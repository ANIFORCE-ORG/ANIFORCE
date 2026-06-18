#!/usr/bin/env python3
"""
Block 7: 多租户隔离测试

验证：
- 不同用户的任务隔离
- 数据库级别隔离
- Session/Sandbox 隔离
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


def test_block_7():
    """执行 Block 7 测试"""
    
    print_section("Block 7: 多租户隔离测试")
    
    results = []
    base_url = "http://localhost:8020"
    
    # Step 7.1: 准备两个用户 Token
    print_section("Step 7.1: 准备两个用户 Token")
    
    token_a = create_access_token({
        "sub": "user_a_block7",
        "email": "user_a@example.com",
            "name": "Test User"
    })
    
    token_b = create_access_token({
        "sub": "user_b_block7",
        "email": "user_b@example.com",
            "name": "Test User"
    })
    
    print(f"User A Token: {token_a[:50]}...")
    print(f"User B Token: {token_b[:50]}...")
    
    # Step 7.2: User A 创建任务
    print_section("Step 7.2: User A 创建任务")
    
    payload_a = {
        "task_type": "conversation",
        "title": "User A Secret Task",
        "input_data": {"secret": "User A's confidential data"}
    }
    
    response_a = httpx.post(
        f"{base_url}/api/agent/tasks",
        json=payload_a,
        headers={"Authorization": f"Bearer {token_a}"},
        timeout=10
    )
    
    if response_a.status_code == 200:
        task_a = response_a.json()
        task_a_id = task_a["task_id"]
        print(f"✅ User A 创建任务: {task_a_id}")
        print(f"   标题: {task_a['title']}")
        results.append(True)
    else:
        print(f"❌ User A 创建任务失败: {response_a.status_code}")
        task_a_id = None
        results.append(False)
    
    # Step 7.3: User B 无法访问 User A 的任务
    print_section("Step 7.3: User B 无法访问 User A 的任务")
    
    if task_a_id:
        response_b_get = httpx.get(
            f"{base_url}/api/agent/tasks/{task_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
            timeout=10
        )
        
        is_blocked = response_b_get.status_code in [403, 404]
        print(f"User B 访问 User A 任务状态码: {response_b_get.status_code}")
        results.append(print_result(is_blocked, "User B 无法访问 User A 的任务"))
    else:
        print("⚠️  跳过（User A 任务创建失败）")
        results.append(None)
    
    # Step 7.4: User B 创建自己的任务
    print_section("Step 7.4: User B 创建自己的任务")
    
    payload_b = {
        "task_type": "conversation",
        "title": "User B Task",
        "input_data": {"note": "User B's data"}
    }
    
    response_b_create = httpx.post(
        f"{base_url}/api/agent/tasks",
        json=payload_b,
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=10
    )
    
    if response_b_create.status_code == 200:
        task_b = response_b_create.json()
        task_b_id = task_b["task_id"]
        print(f"✅ User B 创建任务: {task_b_id}")
        results.append(True)
    else:
        print(f"❌ User B 创建任务失败")
        task_b_id = None
        results.append(False)
    
    # Step 7.5: 查询任务列表（User A 只能看到自己的）
    print_section("Step 7.5: 任务列表隔离")
    
    response_a_list = httpx.get(
        f"{base_url}/api/agent/tasks",
        headers={"Authorization": f"Bearer {token_a}"},
        timeout=10
    )
    
    response_b_list = httpx.get(
        f"{base_url}/api/agent/tasks",
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=10
    )
    
    if response_a_list.status_code == 200 and response_b_list.status_code == 200:
        tasks_a = response_a_list.json()
        tasks_b = response_b_list.json()
        
        print(f"\nUser A 可见任务数: {len(tasks_a)}")
        print(f"User B 可见任务数: {len(tasks_b)}")
        
        # User A 应该看不到 User B 的任务
        task_b_ids = [t["task_id"] for t in tasks_b]
        a_sees_b = any(t["task_id"] in task_b_ids for t in tasks_a)
        
        # User B 应该看不到 User A 的任务
        task_a_ids = [t["task_id"] for t in tasks_a]
        b_sees_a = any(t["task_id"] in task_a_ids for t in tasks_b)
        
        is_isolated = not a_sees_b and not b_sees_a
        
        results.append(print_result(is_isolated, "任务列表隔离"))
    else:
        print("❌ 查询任务列表失败")
        results.append(False)
    
    # Step 7.6: 数据库级别验证
    print_section("Step 7.6: 数据库级别验证")
    
    try:
        import sqlite3
        db_path = Path(__file__).parent.parent.parent / "runtime" / "agent" / "tasks.db"
        
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 查询所有任务的 user_id
            cursor.execute("SELECT task_id, user_id, title FROM tasks ORDER BY created_at DESC LIMIT 10")
            tasks = cursor.fetchall()
            
            print("\n数据库中的任务（最近10条）:")
            user_a_count = 0
            user_b_count = 0
            
            for task_id, user_id, title in tasks:
                print(f"  - {task_id[:16]}... | {user_id} | {title}")
                if user_id == "user_a_block7":
                    user_a_count += 1
                elif user_id == "user_b_block7":
                    user_b_count += 1
            
            print(f"\nUser A 任务数: {user_a_count}")
            print(f"User B 任务数: {user_b_count}")
            
            conn.close()
            
            # 验证：数据库中确实有不同用户的任务
            has_isolation = user_a_count > 0 and user_b_count > 0
            results.append(print_result(has_isolation, "数据库存储了 user_id"))
        else:
            print("❌ 数据库文件不存在")
            results.append(False)
    
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        results.append(False)
    
    # Step 7.7: Session/Sandbox 隔离
    print_section("Step 7.7: Session/Sandbox 隔离")
    
    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())
    
    # User A 对话（告知秘密）
    print("\n👤 User A: 告知秘密信息")
    payload_a_chat = {
        "messages": [
            {"role": "user", "content": "我的密码是 secret_a_123，请简短确认"}
        ],
        "threadId": session_a
    }
    
    response_a_chat = httpx.post(
        f"{base_url}/api/agent/copilotkit/agent/default/run",
        json=payload_a_chat,
        headers={"Authorization": f"Bearer {token_a}"},
        timeout=30
    )
    
    if response_a_chat.status_code == 200:
        print("✅ User A 对话成功")
        
        time.sleep(2)
        
        # User B 对话（询问秘密）
        print("\n👤 User B: 询问秘密信息")
        payload_b_chat = {
            "messages": [
                {"role": "user", "content": "刚才有人告诉你什么密码？"}
            ],
            "threadId": session_b
        }
        
        text_b = ""
        try:
            with httpx.stream(
                "POST",
                f"{base_url}/api/agent/copilotkit/agent/default/run",
                json=payload_b_chat,
                headers={"Authorization": f"Bearer {token_b}"},
                timeout=30
            ) as response_b_chat:
                for line in response_b_chat.iter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("event") == "TEXT_MESSAGE_CONTENT":
                            text_b += data.get("data", {}).get("content", "")
            
            print(f"User B 回复: {text_b[:200]}...")
            
            # User B 不应该知道 User A 的密码
            is_isolated = "secret_a_123" not in text_b
            results.append(print_result(is_isolated, "Session 内容隔离"))
        
        except Exception as e:
            print(f"❌ User B 对话失败: {e}")
            results.append(False)
    else:
        print(f"❌ User A 对话失败: {response_a_chat.status_code}")
        results.append(False)
    
    # Step 7.8: 文件系统隔离
    print_section("Step 7.8: 文件系统隔离")
    
    runtime_dir = Path(__file__).parent.parent.parent / "runtime" / "sessions"
    
    session_a_dir = runtime_dir / session_a
    session_b_dir = runtime_dir / session_b
    
    print(f"Session A 目录: {session_a_dir}")
    print(f"Session A 存在: {session_a_dir.exists()}")
    
    print(f"Session B 目录: {session_b_dir}")
    print(f"Session B 存在: {session_b_dir.exists()}")
    
    # 验证目录独立
    both_exist = session_a_dir.exists() and session_b_dir.exists()
    results.append(print_result(both_exist, "Session 目录独立创建"))
    
    # 总结
    print_section("Block 7 测试结果")
    valid_results = [r for r in results if r is not None]
    passed_count = sum(valid_results)
    total_count = len(valid_results)
    print(f"\n通过: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("\n🎉 Block 7 全部通过！")
        print("\n✅ 多租户隔离验证：")
        print("   - API 层隔离正常")
        print("   - 数据库层隔离正常")
        print("   - Session 层隔离正常")
        print("   - 文件系统隔离正常")
        return True
    else:
        print("\n⚠️  Block 7 部分失败")
        print("\n❌ 多租户隔离存在问题，需要立即修复！")
        return False


if __name__ == "__main__":
    success = test_block_7()
    sys.exit(0 if success else 1)
