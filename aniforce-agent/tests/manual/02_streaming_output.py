#!/usr/bin/env python
"""
真实场景测试 2：流式输出验证

目标：验证 include_partial_messages=True 是否生效

步骤：
1. 让 Claude 写一段较长的代码
2. 观察是否收到增量文本块（StreamEvent）
3. 统计收到的消息数量

预期结果：
- 收到多条 content_block_delta 消息（不是一条完整消息）
- 能看到文字逐步输出的效果
- 消息类型包含 StreamEvent
"""
import asyncio
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.runtime import AgentRuntime
from app.config.database import init_task_db


async def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ 错误：未设置 ANTHROPIC_API_KEY")
        return

    print("=" * 60)
    print("真实场景测试 2：流式输出验证")
    print("=" * 60)
    print()

    await init_task_db()
    runtime = AgentRuntime()
    session_id = str(uuid4())

    prompt = "写一个 Python 函数，实现快速排序算法，包含详细注释。"
    print(f"👤 用户: {prompt}")
    print()
    print("🔄 观察流式输出...")
    print("-" * 60)

    message_count = 0
    text_blocks = []
    stream_events = 0

    async for message in runtime.query(
        session_id=session_id,
        user_id="test_user",
        task_id="task_stream",
        prompt=prompt,
    ):
        message_count += 1
        msg_type = message.get("type")

        # 检测流式事件
        if msg_type == "stream_event":
            stream_events += 1
            event_type = message.get("event_type")
            if event_type == "content_block_delta":
                delta = message.get("delta", {})
                text = delta.get("text", "")
                if text:
                    print(text, end="", flush=True)
                    text_blocks.append(text)
        elif msg_type == "assistant":
            for block in message.get("content", []):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text and not text_blocks:  # 如果没有流式事件，输出完整文本
                        print(text)
                        text_blocks.append(text)

    print()
    print()
    print("=" * 60)
    print("✅ 测试结果")
    print("=" * 60)
    print(f"📊 总消息数: {message_count}")
    print(f"🌊 流式事件数: {stream_events}")
    print(f"📝 文本块数: {len(text_blocks)}")
    print()

    if stream_events > 10:
        print("✅ 流式输出正常：收到大量增量事件")
        print(f"   include_partial_messages=True 生效")
    elif len(text_blocks) == 1:
        print("⚠️  流式输出可能未生效：只收到一个完整文本块")
        print(f"   可能 include_partial_messages=False 或未配置")
    else:
        print(f"❓ 流式状态不确定：收到 {len(text_blocks)} 个文本块")

    await runtime.cleanup_all()


if __name__ == "__main__":
    asyncio.run(main())
