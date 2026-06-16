"""
Phase 2.1：ClaudeSDKClient 实例池管理测试

目标：验证 Client 实例正确创建、复用和清理

验证点：
1. 同一 session_id 两次调用，复用同一 Client 实例
2. 不同 session_id，创建不同 Client 实例
3. disconnect_client 后，实例从池中移除
4. cleanup_all 清理所有实例

注意：此测试需要真实 Claude API Key，但不发送实际请求（只创建 Client）
"""
import pytest
from uuid import uuid4
from app.agent.runtime import AgentRuntime
from app.config.database import init_task_db


@pytest.fixture
async def agent_runtime():
    """创建 AgentRuntime 实例"""
    # 初始化数据库
    await init_task_db()
    runtime = AgentRuntime()
    yield runtime
    # 清理
    await runtime.cleanup_all()


@pytest.mark.asyncio
async def test_client_reuse_same_session(agent_runtime):
    """
    测试：同一 session_id 两次调用，复用同一 Client 实例
    """
    session_id = str(uuid4())  # 使用 UUID
    user_id = "user_001"
    task_id = "task_001"

    # 第一次创建 Client
    client1 = await agent_runtime.get_or_create_client(
        session_id=session_id,
        user_id=user_id,
        task_id=task_id,
    )

    # 第二次获取 Client（应复用）
    client2 = await agent_runtime.get_or_create_client(
        session_id=session_id,
        user_id=user_id,
        task_id=task_id,
    )

    # 验证：两次返回同一实例
    assert client1 is client2, "Same session_id should return the same client instance"

    # 验证：实例池中只有一个 Client
    assert len(agent_runtime._clients) == 1
    assert session_id in agent_runtime._clients


@pytest.mark.asyncio
async def test_client_different_sessions(agent_runtime):
    """
    测试：不同 session_id，创建不同 Client 实例
    """
    session_id_1 = str(uuid4())  # 使用 UUID
    session_id_2 = str(uuid4())
    user_id = "user_001"
    task_id = "task_001"

    # 创建第一个 Client
    client1 = await agent_runtime.get_or_create_client(
        session_id=session_id_1,
        user_id=user_id,
        task_id=task_id,
    )

    # 创建第二个 Client
    client2 = await agent_runtime.get_or_create_client(
        session_id=session_id_2,
        user_id=user_id,
        task_id=task_id,
    )

    # 验证：两个不同的实例
    assert client1 is not client2, "Different session_id should create different client instances"

    # 验证：实例池中有两个 Client
    assert len(agent_runtime._clients) == 2
    assert session_id_1 in agent_runtime._clients
    assert session_id_2 in agent_runtime._clients


@pytest.mark.asyncio
async def test_client_disconnect(agent_runtime):
    """
    测试：disconnect_client 后，实例从池中移除
    """
    session_id = str(uuid4())  # 使用 UUID
    user_id = "user_001"
    task_id = "task_001"

    # 创建 Client
    client = await agent_runtime.get_or_create_client(
        session_id=session_id,
        user_id=user_id,
        task_id=task_id,
    )

    # 验证：实例在池中
    assert session_id in agent_runtime._clients
    assert len(agent_runtime._clients) == 1

    # 断开 Client
    await agent_runtime.disconnect_client(session_id)

    # 验证：实例已移除
    assert session_id not in agent_runtime._clients
    assert len(agent_runtime._clients) == 0


@pytest.mark.asyncio
async def test_cleanup_all(agent_runtime):
    """
    测试：cleanup_all 清理所有实例
    """
    # 创建多个 Client
    for i in range(3):
        await agent_runtime.get_or_create_client(
            session_id=str(uuid4()),  # 使用 UUID
            user_id="user_001",
            task_id=f"task_{i:03d}",
        )

    # 验证：3 个实例在池中
    assert len(agent_runtime._clients) == 3

    # 清理所有实例
    await agent_runtime.cleanup_all()

    # 验证：所有实例已清理
    assert len(agent_runtime._clients) == 0


@pytest.mark.asyncio
async def test_client_concurrent_creation(agent_runtime):
    """
    测试：并发创建同一 session_id 的 Client，只创建一个实例
    """
    import asyncio

    session_id = str(uuid4())  # 使用 UUID
    user_id = "user_001"

    # 并发创建 10 个请求（同一 session_id）
    tasks = [
        agent_runtime.get_or_create_client(
            session_id=session_id,
            user_id=user_id,
            task_id=f"task_{i:03d}",
        )
        for i in range(10)
    ]

    clients = await asyncio.gather(*tasks)

    # 验证：所有返回的都是同一个实例
    first_client = clients[0]
    for client in clients:
        assert client is first_client, "Concurrent calls should return the same instance"

    # 验证：实例池中只有一个 Client
    assert len(agent_runtime._clients) == 1


@pytest.mark.asyncio
async def test_session_info(agent_runtime):
    """
    测试：get_session_info 返回正确的会话信息
    """
    session_id = str(uuid4())  # 使用 UUID
    user_id = "user_001"
    task_id = "task_001"

    # 创建 Client
    await agent_runtime.get_or_create_client(
        session_id=session_id,
        user_id=user_id,
        task_id=task_id,
    )

    # 获取会话信息
    info = agent_runtime.get_session_info(session_id)

    # 验证
    assert info["session_id"] == session_id
    assert info["has_client"] is True
    assert "session_dir" in info
    assert "skills_dir" in info


@pytest.mark.asyncio
async def test_list_sessions(agent_runtime):
    """
    测试：list_sessions 返回所有活跃会话
    """
    # 创建 3 个 Client
    session_ids = [str(uuid4()) for _ in range(3)]  # 使用 UUID
    for session_id in session_ids:
        await agent_runtime.get_or_create_client(
            session_id=session_id,
            user_id="user_001",
            task_id=f"task_{session_id}",
        )

    # 获取会话列表
    active_sessions = agent_runtime.list_sessions()

    # 验证
    assert len(active_sessions) == 3
    assert set(active_sessions) == set(session_ids)
