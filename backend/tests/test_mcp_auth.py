"""
测试 MCP 鉴权系统

验证：
1. MCP 中间件正确验证 JWT Token
2. get_current_user_id() 可以获取用户身份
3. 未鉴权请求返回 401
4. 不同用户的数据隔离
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from datetime import datetime, timedelta

from app.agent_platform.mcp import (
    MCPAuthMiddleware,
    get_current_user_id,
    get_current_user_type,
    set_mcp_request_context,
)
from app.config.settings import get_settings


# 创建测试 MCP app
app = FastAPI()
app.add_middleware(MCPAuthMiddleware)


@app.middleware("http")
async def set_context(request, call_next):
    """设置 MCP 上下文"""
    set_mcp_request_context(request)
    response = await call_next(request)
    return response


@app.post("/mcp")
def mcp_tool_call():
    """模拟 MCP 工具调用"""
    user_id = get_current_user_id()
    user_type = get_current_user_type()
    return {
        "user_id": user_id,
        "user_type": user_type,
        "result": f"Tool executed by {user_id}"
    }


client = TestClient(app)


def create_test_token(user_id: str = "test_user_001", user_type: str = "user") -> str:
    """创建测试 JWT Token"""
    settings = get_settings()
    payload = {
        "sub": user_id,
        "type": user_type,
        "email": "test@example.com",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def test_mcp_authenticated_request():
    """测试：已认证的 MCP 请求"""
    token = create_test_token("user_001")
    
    response = client.post(
        "/mcp",
        headers={"Authorization": f"Bearer {token}"},
        json={"method": "tools/call", "params": {"name": "test_tool"}}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user_001"
    assert data["user_type"] == "user"


def test_mcp_unauthenticated_request():
    """测试：未认证的 MCP 请求应该返回 401"""
    response = client.post(
        "/mcp",
        json={"method": "tools/call", "params": {"name": "test_tool"}}
    )
    
    assert response.status_code == 401
    assert "authorization" in response.json()["detail"].lower()


def test_mcp_invalid_token():
    """测试：无效 token 应该返回 401"""
    response = client.post(
        "/mcp",
        headers={"Authorization": "Bearer invalid_token"},
        json={"method": "tools/call"}
    )
    
    assert response.status_code == 401


def test_mcp_admin_user():
    """测试：管理员用户"""
    token = create_test_token("admin_001", "admin")
    
    response = client.post(
        "/mcp",
        headers={"Authorization": f"Bearer {token}"},
        json={"method": "tools/call"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "admin_001"
    assert data["user_type"] == "admin"


def test_mcp_user_isolation():
    """测试：不同用户的请求隔离"""
    token1 = create_test_token("user_001")
    token2 = create_test_token("user_002")
    
    response1 = client.post(
        "/mcp",
        headers={"Authorization": f"Bearer {token1}"},
        json={"method": "tools/call"}
    )
    
    response2 = client.post(
        "/mcp",
        headers={"Authorization": f"Bearer {token2}"},
        json={"method": "tools/call"}
    )
    
    data1 = response1.json()
    data2 = response2.json()
    
    # 验证用户隔离
    assert data1["user_id"] == "user_001"
    assert data2["user_id"] == "user_002"
    assert data1["user_id"] != data2["user_id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
