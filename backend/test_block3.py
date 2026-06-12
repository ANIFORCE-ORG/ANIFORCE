"""
Block 3 功能验证脚本

验证：
1. SDK Adapter 事件转换
2. Runtime 完整执行流程
3. 异常处理
"""

import asyncio
from datetime import datetime

from app.agent_platform.models import AgentTask, AgentTaskStatus
from app.agent_platform.repositories.memory import MemoryAgentTaskRepository
from app.agent_platform.adapters.openai_adapter import OpenAISDKAdapter
from app.agent_platform.runtime import AgentRuntime
from app.config.settings import get_settings


async def test_runtime_basic():
    """测试 Runtime 基本执行"""
    print("=" * 60)
    print("测试 1: Runtime 基本执行")
    print("=" * 60)
    
    settings = get_settings()
    repo = MemoryAgentTaskRepository()
    
    # 初始化 Adapter
    adapter = OpenAISDKAdapter(
        model=getattr(settings, "OPENAI_AGENTS_MODEL", "gpt-4o-mini"),
        api_key=settings.OPENAI_API_KEY,
        base_url=getattr(settings, "OPENAI_BASE_URL", None),
    )
    print(f"✓ SDK Adapter initialized: {adapter.model}")
    
    # 初始化 Runtime
    runtime = AgentRuntime(
        adapter=adapter,
        repo=repo,
        session_db_path="runtime/agent/test_sessions.db",
    )
    print("✓ Runtime initialized")
    
    # 创建任务
    task = AgentTask(
        task_id="test_task_001",
        user_id="test_user",
        task_type="conversation",
        title="Runtime test",
        status=AgentTaskStatus.PENDING,
    )
    await repo.create(task)
    print(f"✓ Task created: {task.task_id}")
    
    # 运行任务
    print("\n开始执行任务...")
    event_count = 0
    message_deltas = []
    
    async for event in runtime.run_task(task, "你好，请简单介绍一下自己"):
        event_count += 1
        print(f"  [{event.sequence}] {event.event_type}")
        
        # 收集消息增量
        if event.event_type == "message.updated":
            delta = event.payload.get("delta", "")
            message_deltas.append(delta)
            print(f"    delta: {delta[:50]}...")
        
        # 打印最终消息
        if event.event_type == "message.completed":
            content = event.payload.get("content", "")
            print(f"\n完整回复:\n{content}\n")
    
    print(f"✓ Task completed, received {event_count} events")
    print(f"✓ Message deltas: {len(message_deltas)} chunks")
    
    # 验证任务状态
    final_task = await repo.get_user_task("test_user", "test_task_001")
    assert final_task.status == AgentTaskStatus.COMPLETED
    print(f"✓ Task status: {final_task.status.value}")
    
    # 验证事件持久化
    events = await repo.list_user_task_events("test_user", "test_task_001")
    assert len(events) == event_count
    print(f"✓ Events persisted: {len(events)} events")
    
    print()


async def test_session_continuity():
    """测试 Session 连续性（多轮对话）"""
    print("=" * 60)
    print("测试 2: Session 连续性（多轮对话）")
    print("=" * 60)
    
    settings = get_settings()
    repo = MemoryAgentTaskRepository()
    
    adapter = OpenAISDKAdapter(
        model=getattr(settings, "OPENAI_AGENTS_MODEL", "gpt-4o-mini"),
        api_key=settings.OPENAI_API_KEY,
        base_url=getattr(settings, "OPENAI_BASE_URL", None),
    )
    
    runtime = AgentRuntime(
        adapter=adapter,
        repo=repo,
        session_db_path="runtime/agent/test_sessions.db",
    )
    
    # 第一轮对话
    task1 = AgentTask(
        task_id="test_task_multi_1",
        user_id="test_user",
        task_type="conversation",
        title="Multi-turn test 1",
        status=AgentTaskStatus.PENDING,
    )
    await repo.create(task1)
    
    print("第一轮对话...")
    session_id = None
    async for event in runtime.run_task(task1, "我叫张三，请记住我的名字"):
        if event.event_type == "message.completed":
            content = event.payload.get("content", "")
            print(f"  助手: {content[:100]}...")
    
    # 获取 session_id
    final_task1 = await repo.get_user_task("test_user", "test_task_multi_1")
    session_id = final_task1.session_id
    print(f"✓ Session created: {session_id}")
    
    # 第二轮对话（复用 session）
    task2 = AgentTask(
        task_id="test_task_multi_2",
        user_id="test_user",
        task_type="conversation",
        title="Multi-turn test 2",
        status=AgentTaskStatus.PENDING,
        session_id=session_id,  # 复用 session
    )
    await repo.create(task2)
    
    print("\n第二轮对话（测试记忆）...")
    async for event in runtime.run_task(task2, "我叫什么名字？"):
        if event.event_type == "message.completed":
            content = event.payload.get("content", "")
            print(f"  助手: {content[:200]}...")
            # 应该能记住名字
            if "张三" in content:
                print("✓ Session continuity verified: 助手记住了用户名字")
            else:
                print("⚠ Session continuity may not work: 助手没有提到用户名字")
    
    print()


async def test_error_handling():
    """测试错误处理"""
    print("=" * 60)
    print("测试 3: 错误处理")
    print("=" * 60)
    
    repo = MemoryAgentTaskRepository()
    
    # 使用错误的 API key
    adapter = OpenAISDKAdapter(
        model="gpt-4o-mini",
        api_key="invalid_key_for_test",
    )
    
    runtime = AgentRuntime(
        adapter=adapter,
        repo=repo,
        session_db_path="runtime/agent/test_sessions.db",
    )
    
    task = AgentTask(
        task_id="test_task_error",
        user_id="test_user",
        task_type="conversation",
        title="Error test",
        status=AgentTaskStatus.PENDING,
    )
    await repo.create(task)
    
    print("运行任务（预期失败）...")
    error_received = False
    
    async for event in runtime.run_task(task, "测试错误处理"):
        if event.event_type == "runtime.error":
            error_received = True
            print(f"✓ Error event received: {event.payload.get('code')}")
            print(f"  Message: {event.payload.get('message')}")
    
    # 验证任务状态
    final_task = await repo.get_user_task("test_user", "test_task_error")
    assert final_task.status == AgentTaskStatus.ERROR
    assert error_received
    print(f"✓ Task status: {final_task.status.value}")
    print(f"✓ Error handling works correctly")
    
    print()


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Block 3 功能验证")
    print("=" * 60 + "\n")
    
    await test_runtime_basic()
    await test_session_continuity()
    await test_error_handling()
    
    print("=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
