#!/usr/bin/env python
"""
真实场景测试 1：ClaudeSDKClient 实例池 + 多轮对话

目标：验证同一 session 内多轮对话是否记得上下文

步骤：
1. 创建一个 session
2. 第一轮：告诉 Agent "法国的首都是巴黎"
3. 第二轮：问"我上一条消息提到的城市是什么"
4. 观察：模型是否回答"巴黎"（证明记得上下文）

预期结果：
- 第二轮回答包含 "Paris" 或 "巴黎"
- 两轮使用同一个 session_id
- Client 实例被复用（从日志观察）
"""
import asyncio
import sys
import os
from uuid import uuid4

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.runtime import AgentRuntime
from app.config.database import init_task_db


async def main():
    # 检查 API Key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ 错误：未设置 ANTHROPIC_API_KEY 环境变量")
        print("请运行：export ANTHROPIC_API_KEY=sk-ant-xxxxx")
        return

    print("=" * 60)
    print("真实场景测试 1：多轮对话上下文保持")
    print("=" * 60)
    print()

    # 初始化
    print("📦 初始化数据库...")
    await init_task_db()

    runtime = AgentRuntime()
    session_id = str(uuid4())
    user_id = "test_user_001"

    print(f"✅ Session ID: {session_id}")
    print()

    # 第一轮对话
    print("🔵 第一轮对话：告知信息")
    print("-" * 60)
    prompt1 = "法国的首都是巴黎。请简短确认你收到了这个信息。"
    print(f"👤 用户: {prompt1}")
    print()

    response1 = []
    async for message in runtime.query(
        session_id=session_id,
        user_id=user_id,
        task_id="task_001",
        prompt=prompt1,
    ):
        # SDK 返回对象，需要检查类型
        if hasattr(message, 'type'):
            msg_type = message.type
        elif hasattr(message, '__class__'):
            msg_type = message.__class__.__name__
        else:
            continue

        # AssistantMessage
        if 'AssistantMessage' in str(type(message)) or msg_type == 'assistant':
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        text = block.text
                        response1.append(text)
                        print(f"🤖 Claude: {text}")
        # ResultMessage
        elif 'ResultMessage' in str(type(message)):
            if hasattr(message, 'session_id'):
                print(f"\n📊 第一轮完成 - Session: {message.session_id[:8]}...")

    print()
    print()

    # 第二轮对话（测试上下文）
    print("🟢 第二轮对话：测试记忆")
    print("-" * 60)
    prompt2 = "我上一条消息提到的城市是什么？只回答城市名。"
    print(f"👤 用户: {prompt2}")
    print()

    response2 = []
    async for message in runtime.query(
        session_id=session_id,
        user_id=user_id,
        task_id="task_002",
        prompt=prompt2,
    ):
        if hasattr(message, 'type'):
            msg_type = message.type
        elif hasattr(message, '__class__'):
            msg_type = message.__class__.__name__
        else:
            continue

        if 'AssistantMessage' in str(type(message)) or msg_type == 'assistant':
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        text = block.text
                        response2.append(text)
                        print(f"🤖 Claude: {text}")
        elif 'ResultMessage' in str(type(message)):
            if hasattr(message, 'session_id'):
                print(f"\n📊 第二轮完成 - Session: {message.session_id[:8]}...")

    print()
    print()

    # 验证结果
    print("=" * 60)
    print("✅ 测试结果")
    print("=" * 60)

    response2_text = "".join(response2).lower()
    has_paris = "paris" in response2_text or "巴黎" in response2_text

    if has_paris:
        print("✅ 上下文保持成功：模型记得第一轮提到的城市")
        print(f"   第二轮回答包含 'Paris' 或 '巴黎'")
    else:
        print("❌ 上下文保持失败：模型不记得第一轮的信息")
        print(f"   第二轮回答：{response2_text[:100]}")

    print()
    print("🔍 实例池状态:")
    active_sessions = runtime.list_sessions()
    print(f"   活跃会话数: {len(active_sessions)}")
    print(f"   会话 ID: {active_sessions}")

    # 清理
    print()
    print("🧹 清理资源...")
    await runtime.cleanup_all()
    print("✅ 清理完成")


if __name__ == "__main__":
    asyncio.run(main())
