#!/usr/bin/env python3
"""
测试 Plan-Execute 模式是否正常工作

使用复杂任务强制触发 Plan 生成
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agent_platform.runtime import AgentRuntime
from app.agent_platform.adapters.openai_adapter import OpenAISDKAdapter
from app.agent_platform.repositories.sqlite import SQLiteAgentTaskRepository
from app.agent_platform.models import AgentTask, AgentTaskStatus


async def test_plan_detection():
    """测试 Plan 检测是否工作"""
    
    print("\n" + "=" * 60)
    print("测试 Plan-Execute 模式")
    print("=" * 60)
    
    # 创建 Runtime
    adapter = OpenAISDKAdapter(
        model="gpt-4o-mini",
        skills_dir="runtime/skills",
        sandbox_dir="runtime/agent/sandbox"
    )
    
    repo = SQLiteAgentTaskRepository(db_path="runtime/agent/tasks.db")
    
    runtime = AgentRuntime(
        adapter=adapter,
        repo=repo,
        enable_tracing=True
    )
    
    # 创建任务
    task = AgentTask(
        task_id=f"test_plan_{int(asyncio.get_event_loop().time())}",
        user_id="test_user",
        title="测试 Plan 检测",
        task_type="conversation",
        status=AgentTaskStatus.PENDING,
        context={"auth_token": "test_token_123"}
    )
    
    # 使用一个肯定会触发 Plan 的查询
    query = """
请帮我完成以下任务：
1. 分析数据分析 Skill 包含哪些工作流
2. 列出每个工作流的主要功能
3. 给出使用建议

请先制定执行计划，然后逐步完成。
    """.strip()
    
    print(f"\n📝 测试查询:")
    print(f"   {query}\n")
    print(f"🎯 预期: 应该检测到 Plan\n")
    
    plan_detected = False
    todo_events = []
    message_content = []
    
    try:
        async for event in runtime.run_task(task, query):
            # 检测 Plan 事件
            if event.event_type == "CUSTOM" and event.payload.get("subtype") == "plan.created":
                plan_detected = True
                todos = event.payload.get("todos", [])
                print(f"✅ 检测到 Plan!")
                print(f"   Plan ID: {event.payload.get('plan_id')}")
                print(f"   Todos: {len(todos)} 个\n")
                for i, todo in enumerate(todos, 1):
                    print(f"   {i}. {todo.get('title')}")
                print()
            
            # 检测 Todo 事件
            elif event.event_type == "CUSTOM" and "todo." in event.payload.get("subtype", ""):
                todo_events.append(event.payload.get("subtype"))
                todo_id = event.payload.get("todo_id")
                status = event.payload.get("subtype", "").replace("todo.", "")
                print(f"   📌 Todo 更新: {todo_id} → {status}")
            
            # 收集消息内容
            elif event.event_type in ["MESSAGE_UPDATED", "message.updated"]:
                content = event.payload.get("content", "") or event.payload.get("delta", "")
                if content:
                    message_content.append(content)
        
        print("\n" + "=" * 60)
        print("测试结果")
        print("=" * 60)
        print(f"Plan 检测: {'✅ 成功' if plan_detected else '❌ 失败'}")
        print(f"Todo 事件: {len(todo_events)} 个")
        print(f"消息长度: {len(''.join(message_content))} 字符")
        
        if not plan_detected:
            print("\n⚠️  Plan 未检测到！")
            print("\n可能原因：")
            print("1. Agent 没有输出 Plan 格式")
            print("2. PlanParser 没有匹配到格式")
            print("3. System Prompt 没有正确注入")
            print("\n💡 建议检查：")
            print("- System Prompt 是否包含 Plan-Execute 指导")
            print("- Agent 输出的消息格式")
            print("- PlanParser 的匹配规则")
        else:
            print("\n🎉 Plan-Execute 模式正常工作！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_plan_detection())
