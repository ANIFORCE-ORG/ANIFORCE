#!/usr/bin/env python3
"""
Block 1: 基础连通性测试（OpenAI Agent Service 版）

验证：
- 服务启动
- 健康检查（返回 deepseek 模型）
- JWT 认证
- 基础 API 可用性
"""

import sys
import httpx
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


def test_block_1():
    """执行 Block 1 测试"""

    print_section("Block 1: 基础连通性测试（OpenAI Agent Service）")

    base_url = "http://localhost:8020"
    results = []

    # Step 1.1: 健康检查
    print_section("Step 1.1: 健康检查")
    try:
        response = httpx.get(f"{base_url}/health", timeout=10)
        data = response.json()
        print(f"状态码: {response.status_code}")
        print(f"响应: {data}")
        results.append(print_result(
            response.status_code == 200 and data.get("status") == "healthy",
            "健康检查"
        ))
        results.append(print_result(
            data.get("model") == "deepseek/deepseek-v4-pro",
            f"模型为 deepseek/deepseek-v4-pro（实际: {data.get('model')}）"
        ))
    except Exception as e:
        print(f"错误: {e}")
        results.append(print_result(False, "健康检查"))

    # Step 1.2: JWT 生成
    print_section("Step 1.2: JWT 生成（sub 字段，对齐 backend）")
    try:
        token = create_access_token({"sub": "user_test_001", "email": "test@animagus.com", "name": "Test"})
        print(f"Token: {token[:50]}...")
        results.append(print_result(bool(token), "JWT 生成成功"))
    except Exception as e:
        print(f"错误: {e}")
        token = None
        results.append(print_result(False, "JWT 生成"))

    # Step 1.3: 无认证请求被拒绝
    print_section("Step 1.3: 无认证请求被拒绝")
    try:
        response = httpx.post(
            f"{base_url}/api/agent/runs",
            json={"prompt": "hi", "task_type": "conversation"},
            timeout=10
        )
        passed = response.status_code == 401
        print(f"状态码: {response.status_code}")
        results.append(print_result(passed, "无认证请求返回 401"))
    except Exception as e:
        print(f"错误: {e}")
        results.append(print_result(False, "无认证请求拒绝"))

    # Step 1.4: 带 JWT 的 Tasks API
    print_section("Step 1.4: Tasks API（带 JWT）")
    if token:
        try:
            response = httpx.get(
                f"{base_url}/api/agent/tasks",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text[:200]}")
            results.append(print_result(
                response.status_code == 200,
                "Tasks API 带 JWT 可访问"
            ))
        except Exception as e:
            print(f"错误: {e}")
            results.append(print_result(False, "Tasks API"))

    # Step 1.5: Sessions API
    print_section("Step 1.5: Sessions API")
    if token:
        try:
            response = httpx.get(
                f"{base_url}/api/agent/sessions",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            print(f"状态码: {response.status_code}")
            results.append(print_result(
                response.status_code == 200,
                "Sessions API 可访问"
            ))
        except Exception as e:
            print(f"错误: {e}")
            results.append(print_result(False, "Sessions API"))

    # 汇总
    print_section("Block 1 汇总")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    return passed == total


if __name__ == "__main__":
    success = test_block_1()
    sys.exit(0 if success else 1)
