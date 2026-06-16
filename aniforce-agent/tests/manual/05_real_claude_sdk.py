#!/usr/bin/env python
"""
真实 Claude SDK 测试：通过 HTTP API 直接测试对话能力

测试步骤：
1. 发送第一轮对话："法国的首都是巴黎"
2. 等待回复
3. 发送第二轮对话："我上一条消息提到的城市是什么"
4. 验证是否回答 "巴黎"（证明记住了上下文）
"""
import asyncio
import httpx
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.auth import create_access_token

BASE_URL = "http://localhost:8020"


async def test_multi_turn_conversation():
    """测试多轮对话上下文"""
    print("=" * 70)
    print("🧪 真实 Claude SDK 测试：多轮对话上下文")
    print("=" * 70)
    print()

    # 生成 Token 和 Session ID
    token = create_access_token({"sub": "test_claude", "email": "test@example.com"})
    session_id = str(uuid4())

    print(f"📝 Session ID: {session_id}")
    print(f"🔐 JWT Token: {token[:30]}...")
    print()

    async with httpx.AsyncClient(timeout=120.0) as client:
        # 第一轮对话
        print("=" * 70)
        print("🔵 第一轮：告知信息")
        print("=" * 70)
        prompt1 = "法国的首都是巴黎。请简短确认你收到了这个信息（一句话）。"
        print(f"👤 用户: {prompt1}")
        print()

        try:
            print("🔄 发送请求...")
            response1 = await client.post(
                f"{BASE_URL}/api/agent/copilotkit/agent/default/run",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "messages": [{"role": "user", "content": prompt1}],
                    "threadId": session_id,
                },
            )

            print(f"📊 状态码: {response1.status_code}")

            if response1.status_code != 200:
                print(f"❌ 请求失败: {response1.text}")
                return

            # 解析 SSE 流
            print("🤖 Claude 回复:")
            print("-" * 70)

            full_response1 = ""
            for line in response1.text.split('\n'):
                if line.startswith('data: '):
                    try:
                        import json
                        data = json.loads(line[6:])
                        if 'content' in data:
                            content = data['content']
                            print(content, end='', flush=True)
                            full_response1 += content
                    except:
                        pass

            print()
            print("-" * 70)
            print(f"✅ 第一轮完成，收到 {len(full_response1)} 字符")
            print()

        except Exception as e:
            print(f"❌ 第一轮失败: {e}")
            import traceback
            traceback.print_exc()
            return

        # 第二轮对话（测试上下文）
        print()
        print("=" * 70)
        print("🟢 第二轮：测试记忆")
        print("=" * 70)
        prompt2 = "我上一条消息提到的城市是什么？只回答城市名。"
        print(f"👤 用户: {prompt2}")
        print()

        try:
            print("🔄 发送请求...")
            response2 = await client.post(
                f"{BASE_URL}/api/agent/copilotkit/agent/default/run",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "messages": [{"role": "user", "content": prompt2}],
                    "threadId": session_id,  # 同一个 session
                },
            )

            print(f"📊 状态码: {response2.status_code}")

            if response2.status_code != 200:
                print(f"❌ 请求失败: {response2.text}")
                return

            # 解析第二轮回复
            print("🤖 Claude 回复:")
            print("-" * 70)

            full_response2 = ""
            for line in response2.text.split('\n'):
                if line.startswith('data: '):
                    try:
                        import json
                        data = json.loads(line[6:])
                        if 'content' in data:
                            content = data['content']
                            print(content, end='', flush=True)
                            full_response2 += content
                    except:
                        pass

            print()
            print("-" * 70)
            print()

            # 验证结果
            print("=" * 70)
            print("✅ 测试结果")
            print("=" * 70)

            response2_lower = full_response2.lower()
            has_paris = "paris" in response2_lower or "巴黎" in response2_lower

            if has_paris:
                print("✅ 上下文保持成功！")
                print(f"   模型记得第一轮提到的城市")
                print(f"   第二轮回答包含 'Paris' 或 '巴黎'")
                print()
                print("🎉 Claude SDK 多轮对话功能正常！")
            else:
                print("❌ 上下文保持失败")
                print(f"   第二轮回答: {full_response2[:100]}")
                print(f"   未包含 'Paris' 或 '巴黎'")
                print()
                print("⚠️  可能原因：")
                print("   1. ClaudeSDKClient 实例未复用")
                print("   2. Session Store 未生效")
                print("   3. session_id 未正确传递")

        except Exception as e:
            print(f"❌ 第二轮失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_multi_turn_conversation())
