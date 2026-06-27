"""
测试请求上下文系统

验证：
1. 上下文中间件正确设置用户信息
2. get_current_user() 可以正确获取用户
3. 未登录用户抛出 401
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from datetime import datetime, timedelta

from app.core.context import (
    get_current_user,
    get_current_user_optional,
    get_request_id,
    set_request_context,
)
from app.middleware.context import RequestContextMiddleware
from app.config.settings import get_settings


# 创建测试 app
app = FastAPI()
app.add_middleware(RequestContextMiddleware)


@app.get("/protected")
def protected_endpoint():
    """需要鉴权的端点"""
    user = get_current_user()
    return {"user_id": user["id"], "email": user["email"]}


@app.get("/optional")
def optional_endpoint():
    """可选鉴权的端点"""
    user = get_current_user_optional()
    if user:
        return {"logged_in": True, "user_id": user["id"]}
    return {"logged_in": False}


@app.get("/request-id")
def request_id_endpoint():
    """测试 request_id"""
    return {"request_id": get_request_id()}


client = TestClient(app)


def create_test_token(user_id: str = "test_user_001", email: str = "test@example.com") -> str:
    """创建测试 JWT Token"""
    settings = get_settings()
    payload = {
        "sub": user_id,
        "email": email,
        "name": "Test User",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def test_authenticated_request():
    """测试：已认证请求应该正常工作"""
    token = create_test_token()
    
    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test_user_001"
    assert data["email"] == "test@example.com"


def test_unauthenticated_request():
    """测试：未认证请求应该返回 401"""
    response = client.get("/protected")
    
    assert response.status_code == 401


def test_optional_authentication_with_token():
    """测试：可选鉴权端点（有 token）"""
    token = create_test_token()
    
    response = client.get(
        "/optional",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["logged_in"] is True
    assert data["user_id"] == "test_user_001"


def test_optional_authentication_without_token():
    """测试：可选鉴权端点（无 token）"""
    response = client.get("/optional")
    
    assert response.status_code == 200
    data = response.json()
    assert data["logged_in"] is False


def test_request_id_auto_generated():
    """测试：request_id 自动生成"""
    response = client.get("/request-id")
    
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert len(data["request_id"]) > 0


def test_request_id_from_header():
    """测试：使用客户端提供的 request_id"""
    custom_request_id = "custom_req_12345"
    
    response = client.get(
        "/request-id",
        headers={"x-request-id": custom_request_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == custom_request_id
    # 响应头也应该返回 request_id
    assert response.headers.get("x-request-id") == custom_request_id


def test_invalid_token():
    """测试：无效 token 应该被忽略（不报错，视为未登录）"""
    response = client.get(
        "/optional",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["logged_in"] is False


def test_context_isolation():
    """测试：不同请求的上下文隔离"""
    token1 = create_test_token("user_001", "user1@example.com")
    token2 = create_test_token("user_002", "user2@example.com")
    
    # 并发请求
    response1 = client.get("/protected", headers={"Authorization": f"Bearer {token1}"})
    response2 = client.get("/protected", headers={"Authorization": f"Bearer {token2}"})
    
    data1 = response1.json()
    data2 = response2.json()
    
    # 验证上下文正确隔离
    assert data1["user_id"] == "user_001"
    assert data2["user_id"] == "user_002"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
