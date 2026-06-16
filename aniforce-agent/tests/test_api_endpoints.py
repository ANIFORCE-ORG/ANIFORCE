"""测试 API 端点（不需要真实 Claude API Key）"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models.task import TaskStatus


@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock 认证中间件"""
    with patch("app.middleware.auth.get_current_user_id", return_value="test_user_123"):
        yield


def test_root_endpoint(client):
    """测试根路径健康检查"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "aniforce-agent"}


def test_health_endpoint(client):
    """测试详细健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "aniforce-agent"
    assert data["version"] == "1.0.0"


def test_copilotkit_info(client):
    """测试 CopilotKit /info 端点"""
    response = client.get("/api/agent/copilotkit/info")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert len(data["agents"]) > 0
    agent = data["agents"][0]
    assert agent["name"] == "default"
    assert "description" in agent
    assert "capabilities" in agent


@pytest.mark.asyncio
async def test_create_task_requires_auth(client):
    """测试创建任务需要认证"""
    response = client.post(
        "/api/agent/tasks",
        json={
            "task_type": "conversation",
            "title": "Test task",
        },
    )
    # 应该返回 401 或 403（具体看认证中间件实现）
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_list_tasks_requires_auth(client):
    """测试列出任务需要认证"""
    response = client.get("/api/agent/tasks")
    # 应该返回 401 或 403
    assert response.status_code in [401, 403]


def test_copilotkit_run_requires_auth(client):
    """测试运行 Agent 需要认证"""
    response = client.post(
        "/api/agent/copilotkit/agent/default/run",
        json={
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )
    # 应该返回 401 或 403
    assert response.status_code in [401, 403]
