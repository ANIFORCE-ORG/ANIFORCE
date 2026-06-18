#!/usr/bin/env python3
"""
Block 1: 基础连通性测试

验证：
- 服务启动
- 健康检查
- JWT 认证
- 基础 API 可用性
"""

import sys
import httpx
from pathlib import Path

# 添加项目根目录到 path
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


def test_block_1():
    """执行 Block 1 测试"""
    
    print_section("Block 1: 基础连通性测试")
    
    base_url = "http://localhost:8020"
    results = []
    
    # Step 1.1: 健康检查
    print_section("Step 1.1: 健康检查")
    try:
        response = httpx.get(f"{base_url}/health", timeout=10)
        passed = response.status_code == 200
        data = response.json()
        print(f"状态码: {response.status_code}")
        print(f"响应: {data}")
        results.append(print_result(
            passed and data.get("status") == "healthy",
            "健康检查"
        ))
    except Exception as e:
        print(f"错误: {e}")
        results.append(print_result(False, "健康检查"))
    
    # Step 1.2: Agent Tasks API
    print_section("Step 1.2: Agent Tasks API")
    try:
        response = httpx.get(f"{base_url}/api/agent/tasks", timeout=10)
        passed = response.status_code == 401
        print(f"状态码: {response.status_code}")
        results.append(print_result(passed, "Agent Tasks API 需要认证"))
    except Exception as e:
        print(f"错误: {e}")
        results.append(print_result(False, "Agent Tasks API"))
    
    # Step 1.3: 无认证请求被拒绝
    print_section("Step 1.3: 无认证请求被拒绝")
    try:
        response = httpx.post(
            f"{base_url}/api/agent/tasks",
            json={"task_type": "test", "title": "test"},
            timeout=10
        )
        passed = response.status_code == 401
        print(f"状态码: {response.status_code}")
        results.append(print_result(passed, "无认证请求返回 401"))
    except Exception as e:
        print(f"错误: {e}")
        results.append(print_result(False, "无认证请求返回 401"))
    
    # Step 1.4: JWT Token 生成和使用
    print_section("Step 1.4: JWT Token 生成和使用")
    try:
        # 生成 Token
        token = create_access_token({
            "sub": "test_user_block1",
            "email": "block1@example.com",
            "name": "Test User"
        })
        print(f"Token 生成成功: {token[:50]}...")
        
        # 使用 Token 创建任务
        response = httpx.post(
            f"{base_url}/api/agent/tasks",
            json={
                "task_type": "conversation",
                "title": "Block 1 Test Task",
                "input_data": {"prompt": "hello"}
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        passed = response.status_code == 200
        data = response.json()
        print(f"状态码: {response.status_code}")
        print(f"响应: {data}")
        
        if passed:
            task_id = data.get("task_id")
            print(f"任务创建成功: {task_id}")
        
        results.append(print_result(passed, "JWT 认证和任务创建"))
    except Exception as e:
        print(f"错误: {e}")
        results.append(print_result(False, "JWT 认证和任务创建"))
    
    # Step 1.5: 数据库文件验证
    print_section("Step 1.5: 数据库文件验证")
    try:
        db_path = Path(__file__).parent.parent.parent / "runtime" / "agent" / "tasks.db"
        exists = db_path.exists()
        print(f"数据库路径: {db_path}")
        print(f"文件存在: {exists}")
        if exists:
            size = db_path.stat().st_size
            print(f"文件大小: {size} bytes")
        results.append(print_result(exists, "数据库文件存在"))
    except Exception as e:
        print(f"错误: {e}")
        results.append(print_result(False, "数据库文件存在"))
    
    # 总结
    print_section("Block 1 测试结果")
    passed_count = sum(results)
    total_count = len(results)
    print(f"\n通过: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("\n🎉 Block 1 全部通过！")
        return True
    else:
        print("\n⚠️  Block 1 部分失败，请检查上述错误")
        return False


if __name__ == "__main__":
    success = test_block_1()
    sys.exit(0 if success else 1)
