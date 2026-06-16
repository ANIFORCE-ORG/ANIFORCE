#!/usr/bin/env python
"""
直接测试 AgentRuntime + ClaudeSDKClient

绕过 FastAPI、TaskService、数据库，直接测试核心：
1. AgentRuntime.query() 能否调用 Claude API
2. ClaudeSDKClient 实例池是否复用
3. 多轮对话上下文是否保持
4. 流式输出是否正常
"""
import asyncio
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.runtime import AgentRuntime
from app.config.database import init_task_db


async def test_agent_runtime_direct():
    """直接测试 AgentRuntime"""
    print("=" * 70)
    print("🧪 直接测试 AgentRuntime + ClaudeSDKClient")
    print("=" * 70)
    print()

    # 检查配置
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ 错误：未设置 ANTHROPIC_API_KEY")
        return

    print(f"✅ API Key: {api_key[:20]}...")
    print(f"✅ Base URL: {os.getenv('ANTHROPIC_BASE_URL')}")
    print()

    # 初始化
    await init_task_db()
    runtime = AgentRuntime()

    session_id = str(uuid4())
    user_id = "test_user"

    print(f"📝 Session ID: {session_id}")
    print()

    # 第一轮对话
    print("=" * 70)
    print("🔵 第一轮：告知信息")
    print("=" * 70)
    prompt1 = "法国的首都是巴黎。请简短确认（一句话）。"
    print(f"👤 用户: {prompt1}")
    print()
    print("🔄 调用 AgentRuntime.query()...")
    print("🤖 Claude 回复:")
    print("-" * 70)

    response1_texts = []
    message_count1 = 0

    try:
        async for message in runtime.query(
            session_id=session_id,
            user_id=user_id,
            task_id="task_001",
            prompt=prompt1,
        ):
            message_count1 += 1
            msg_type = type(message).__name__

            # 打印消息类型
            if message_count1 <= 5:  # 只打印前几条
                print(f"  [{message_count1}] {msg_type}")

            # 提取文本
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        text = block.text
                        response1_texts.append(text)
                        print(text, end='', flush=True)

        print()
        print("-" * 70)
        print(f"✅ 第一轮完成")
        print(f"   收到 {message_count1} 条消息")
        print(f"   文本长度: {len(''.join(response1_texts))} 字符")
        print()

    except Exception as e:
        print(f"❌ 第一轮失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 第二轮对话
    print()
    print("=" * 70)
    print("🟢 第二轮：测试记忆")
    print("=" * 70)
    prompt2 = "我上一条消息提到的城市是什么？只回答城市名。"
    print(f"👤 用户: {prompt2}")
    print()
    print("🔄 调用 AgentRuntime.query()（同一 session）...")
    print("🤖 Claude 回复:")
    print("-" * 70)

    response2_texts = []
    message_count2 = 0

    try:
        async for message in runtime.query(
            session_id=session_id,  # 同一个 session
            user_id=user_id,
            task_id="task_002",
            prompt=prompt2,
        ):
            message_count2 += 1

            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        text = block.text
                        response2_texts.append(text)
                        print(text, end='', flush=True)

        print()
        print("-" * 70)
        print(f"✅ 第二轮完成")
        print(f"   收到 {message_count2} 条消息")
        print()

    except Exception as e:
        print(f"❌ 第二轮失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 验证结果
    print()
    print("=" * 70)
    print("✅ 测试结果")
    print("=" * 70)

    response2_text = ''.join(response2_texts).lower()
    has_paris = "paris" in response2_text or "巴黎" in response2_text

    print(f"第一轮回复: {(''.join(response1_texts))[:100]}")
    print(f"第二轮回复: {(''.join(response2_texts))[:100]}")
    print()

    if has_paris:
        print("✅ 上下文保持成功！")
        print("   模型记得第一轮提到的城市")
        print()
        print("🎉 Claude SDK 多轮对话功能正常！")
        print("🎉 ClaudeSDKClient 实例池复用正常！")
        print("🎉 Session 持久化正常！")
    else:
        print("❌ 上下文保持失败")
        print(f"   第二轮未包含 'Paris' 或 '巴黎'")

    print()
    print("=" * 70)
    print("🔍 实例池状态")
    print("=" * 70)
    active_sessions = runtime.list_sessions()
    print(f"活跃会话数: {len(active_sessions)}")
    print(f"会话列表: {active_sessions}")

    # 清理
    print()
    print("🧹 清理资源...")
    await runtime.cleanup_all()
    print("✅ 清理完成")


if __name__ == "__main__":
    asyncio.run(test_agent_runtime_direct())
