#!/usr/bin/env python3
"""
AG-UI 协议测试脚本

测试场景：
1. 简单查询（ReAct 模式）
2. 复杂分析（Plan-Execute 模式）
3. 工具调用可视化
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agent_platform.runtime import AgentRuntime
from app.agent_platform.adapters.openai_adapter import OpenAISDKAdapter
from app.agent_platform.repositories.sqlite import SQLiteAgentTaskRepository
from app.agent_platform.models import AgentTask, AgentTaskStatus


async def test_simple_query():
    """测试 1: 简单查询（ReAct 模式）"""
    print("\n" + "=" * 60)
    print("测试 1: 简单查询（ReAct 模式）")
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
        enable_tracing=False
    )
    
    # 创建任务
    task = AgentTask(
        task_id=f"test_simple_{asyncio.get_event_loop().time()}",
        user_id="test_user",
        title="简单查询测试",
        task_type="conversation",
        status=AgentTaskStatus.PENDING,
        context={"auth_token": "test_token_123"}
    )
    
    print(f"\n📝 用户输入: \"列出可用的 Skills\"")
    print(f"🎯 预期: 直接返回 Skills 列表，不应该有 Plan\n")
    
    event_count = 0
    plan_detected = False
    
    try:
        async for event in runtime.run_task(task, "列出可用的 Skills"):
            event_count += 1
            
            if event.event_type == "CUSTOM" and event.payload.get("subtype") == "plan.created":
                plan_detected = True
                print(f"⚠️  检测到 Plan（不应该出现）")
            
            if event.event_type in ["MESSAGE_UPDATED", "message.updated"]:
                content = event.payload.get("content", "")
                if content:
                    print(content, end="", flush=True)
        
        print("\n")
        print(f"✅ 测试完成")
        print(f"   事件数量: {event_count}")
        print(f"   Plan 检测: {'❌ 不应该有' if plan_detected else '✅ 正确（无 Plan）'}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_complex_analysis():
    """测试 2: 复杂分析（Plan-Execute 模式）"""
    print("\n" + "=" * 60)
    print("测试 2: 复杂分析（Plan-Execute 模式）")
    print("=" * 60)
    
    adapter = OpenAISDKAdapter(
        model="gpt-4o-mini",
        skills_dir="runtime/skills",
        sandbox_dir="runtime/agent/sandbox"
    )
    
    repo = SQLiteAgentTaskRepository(db_path="runtime/agent/tasks.db")
    
    runtime = AgentRuntime(
        adapter=adapter,
        repo=repo,
        enable_tracing=False
    )
    
    task = AgentTask(
        task_id=f"test_complex_{asyncio.get_event_loop().time()}",
        user_id="test_user",
        title="复杂分析测试",
        task_type="conversation",
        status=AgentTaskStatus.PENDING,
        context={"auth_token": "test_token_123"}
    )
    
    print(f"\n📝 用户输入: \"帮我分析一下数据分析的 Skill 包含哪些工作流\"")
    print(f"🎯 预期: 生成 Plan → 加载 Skill → 分析内容\n")
    
    event_count = 0
    plan_detected = False
    todo_count = 0
    tool_calls = []
    
    try:
        async for event in runtime.run_task(task, "帮我分析一下数据分析的 Skill 包含哪些工作流"):
            event_count += 1
            
            # 检测 Plan
            if event.event_type == "CUSTOM" and event.payload.get("subtype") == "plan.created":
                plan_detected = True
                todos = event.payload.get("todos", [])
                todo_count = len(todos)
                print(f"\n✅ 检测到 Plan:")
                print(f"   Plan ID: {event.payload.get('plan_id')}")
                print(f"   Todos: {todo_count} 个")
                for i, todo in enumerate(todos, 1):
                    print(f"      {i}. {todo.get('title')}")
                print()
            
            # 检测 Todo 状态变化
            if event.event_type == "CUSTOM" and "todo." in event.payload.get("subtype", ""):
                subtype = event.payload.get("subtype")
                todo_id = event.payload.get("todo_id")
                title = event.payload.get("title", "")
                print(f"   📌 Todo 更新: {title} → {subtype.replace('todo.', '')}")
            
            # 检测工具调用
            if event.event_type == "tool_call.started":
                tool_name = event.payload.get("tool_name", "")
                tool_calls.append(tool_name)
                print(f"   🔧 工具调用: {tool_name}")
            
            # 输出消息内容
            if event.event_type in ["MESSAGE_UPDATED", "message.updated"]:
                content = event.payload.get("content", "")
                if content and not plan_detected:  # Plan 之前的内容
                    print(content, end="", flush=True)
        
        print("\n")
        print(f"✅ 测试完成")
        print(f"   事件数量: {event_count}")
        print(f"   Plan 检测: {'✅ 有 Plan' if plan_detected else '⚠️  无 Plan（应该有）'}")
        print(f"   Todo 数量: {todo_count}")
        print(f"   工具调用: {len(tool_calls)} 次")
        if tool_calls:
            print(f"   调用列表: {', '.join(tool_calls)}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """运行所有测试"""
    print("\n")
    print("🧪 " + "=" * 58 + " 🧪")
    print("   AG-UI 协议测试")
    print("🧪 " + "=" * 58 + " 🧪")
    
    # 测试 1: 简单查询
    await test_simple_query()
    
    await asyncio.sleep(2)
    
    # 测试 2: 复杂分析
    await test_complex_analysis()
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")
    print("=" * 60)
    print("\n💡 提示: 现在可以在浏览器中测试前端 UI")
    print("   访问: http://127.0.0.1:13003")
    print("   测试用户: test@animagus.com / test123")
    print()


if __name__ == "__main__":
    asyncio.run(main())
