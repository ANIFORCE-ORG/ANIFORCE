"""
测试 Block 4：Plan-Execute 集成到 Runtime

测试内容：
1. System Prompt 正确生成
2. Plan 检测功能
3. Todo 跟踪功能
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agent_platform.runtime import AgentRuntime
from app.agent_platform.adapters.openai_adapter import OpenAISDKAdapter
from app.agent_platform.repositories.sqlite import SQLiteAgentTaskRepository
from app.agent_platform.models import AgentTask, AgentTaskStatus
from uuid import uuid4


def test_system_prompt_generation():
    """测试 System Prompt 生成"""
    print("=" * 60)
    print("测试 1: System Prompt 生成")
    print("=" * 60)
    print()
    
    # 创建 Runtime
    adapter = OpenAISDKAdapter(
        model="gpt-4o-mini",
        skills_dir="runtime/skills",
        sandbox_dir="runtime/agent/sandbox"
    )
    
    repo = SQLiteAgentTaskRepository(db_path="runtime/agent/test_tasks.db")
    
    runtime = AgentRuntime(
        adapter=adapter,
        repo=repo,
        enable_tracing=False
    )
    
    # 生成 System Prompt
    prompt = runtime._get_system_prompt("conversation")
    
    print(f"✅ System Prompt 生成成功")
    print(f"   长度: {len(prompt)} 字符")
    print()
    
    # 验证关键内容
    checks = [
        ("包含 Skills 索引", "load_skill" in prompt),
        ("包含 project-management", "project-management" in prompt),
        ("包含 MCP Tools", "list_projects" in prompt),
        ("包含执行计划说明", "执行计划" in prompt),
        ("包含约束", "必须遵守" in prompt),
    ]
    
    print("✅ 内容检查:")
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
    
    all_passed = all(check[1] for check in checks)
    assert all_passed, "System Prompt 内容检查未通过"
    
    print()
    print("✅ 测试 1 通过")
    print()


def test_plan_detection():
    """测试 Plan 检测"""
    print("=" * 60)
    print("测试 2: Plan 检测")
    print("=" * 60)
    print()
    
    adapter = OpenAISDKAdapter(
        model="gpt-4o-mini",
        skills_dir="runtime/skills"
    )
    
    repo = SQLiteAgentTaskRepository(db_path="runtime/agent/test_tasks.db")
    
    runtime = AgentRuntime(
        adapter=adapter,
        repo=repo,
        enable_tracing=False
    )
    
    # 模拟 Agent 输出包含执行计划的消息
    message_with_plan = """
好的，我来帮您分析项目数据。

## 执行计划

1. 查询项目列表
2. 获取项目详情
3. 分析预算使用情况
4. 生成分析报告

现在开始执行第一步...
    """
    
    # 同步调用异步方法（用于测试）
    import asyncio
    
    async def test():
        result = await runtime._detect_and_extract_plan(
            message_with_plan,
            task_id="test_task_123",
            current_sequence=10
        )
        return result
    
    result = asyncio.run(test())
    
    assert result is not None, "应该检测到 Plan"
    plan, event = result
    
    print(f"✅ 检测到 Plan:")
    print(f"   Plan ID: {plan.plan_id}")
    print(f"   Todos 数量: {len(plan.todos)}")
    print()
    
    print(f"✅ 生成的事件:")
    print(f"   事件类型: {event.event_type}")
    print(f"   Subtype: {event.payload.get('subtype')}")
    print(f"   Todos: {len(event.payload.get('todos', []))}")
    print()
    
    assert len(plan.todos) == 4, f"应该有 4 个 Todo，实际: {len(plan.todos)}"
    assert event.event_type == "CUSTOM", "事件类型应该是 CUSTOM"
    assert event.payload.get('subtype') == "plan.created", "Subtype 应该是 plan.created"
    
    print("✅ 测试 2 通过")
    print()


def test_todo_tracking():
    """测试 Todo 跟踪"""
    print("=" * 60)
    print("测试 3: Todo 跟踪")
    print("=" * 60)
    print()
    
    adapter = OpenAISDKAdapter(
        model="gpt-4o-mini",
        skills_dir="runtime/skills"
    )
    
    repo = SQLiteAgentTaskRepository(db_path="runtime/agent/test_tasks.db")
    
    runtime = AgentRuntime(
        adapter=adapter,
        repo=repo,
        enable_tracing=False
    )
    
    # 先设置一个 Plan
    from app.agent_platform.models import ExecutionPlan, TodoItem, TodoStatus
    
    runtime.current_plan = ExecutionPlan(
        plan_id="plan_test",
        task_id="task_test",
        todos=[
            TodoItem(id="todo_1", title="查询项目", status=TodoStatus.PENDING),
            TodoItem(id="todo_2", title="分析数据", status=TodoStatus.PENDING),
        ]
    )
    
    print(f"✅ 设置测试 Plan:")
    print(f"   Plan ID: {runtime.current_plan.plan_id}")
    print(f"   Todos: {len(runtime.current_plan.todos)}")
    print()
    
    # 模拟工具调用
    import asyncio
    
    async def test():
        event = await runtime._track_todo_execution(
            tool_name="list_projects",
            task_id="task_test",
            current_sequence=15
        )
        return event
    
    event = asyncio.run(test())
    
    assert event is not None, "应该生成 TODO_STARTED 事件"
    
    print(f"✅ 生成 TODO_STARTED 事件:")
    print(f"   Todo ID: {event.payload.get('todo_id')}")
    print(f"   Title: {event.payload.get('title')}")
    print(f"   Tool: {event.payload.get('tool_name')}")
    print()
    
    # 验证 Todo 状态已更新
    assert runtime.current_plan.todos[0].status == "running", "第一个 Todo 状态应该是 running"
    print(f"✅ Todo 状态已更新: {runtime.current_plan.todos[0].status}")
    print()
    
    print("✅ 测试 3 通过")
    print()


if __name__ == "__main__":
    print("\n")
    print("🧪 " + "=" * 58 + " 🧪")
    print("   Block 4 集成测试：Plan-Execute Runtime")
    print("🧪 " + "=" * 58 + " 🧪")
    print("\n")
    
    try:
        test_system_prompt_generation()
        test_plan_detection()
        test_todo_tracking()
        
        print("=" * 60)
        print("🎉 所有测试通过！Block 4 集成成功！")
        print("=" * 60)
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 测试失败: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        exit(1)
