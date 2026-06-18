#!/usr/bin/env python3
"""
Block 7 调试：验证 MCP 工具注册

目标：确认 Backend MCP 工具是否真的被 Claude SDK 加载
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
from app.core.auth import create_access_token
from app.core.context import set_jwt_token, set_user_context
from app.agent.runtime import AgentRuntime
from app.config.settings import get_settings


async def test_mcp_registration():
    """测试 MCP 工具注册"""
    
    print("=" * 70)
    print("🔍 Block 7 调试：MCP 工具注册验证")
    print("=" * 70)
    
    settings = get_settings()
    
    # 创建测试用户和 Token
    user_id = "test_mcp_user"
    token = create_access_token({"sub": user_id, "email": "test@example.com", "name": "Test User"})
    
    # 设置上下文（模拟 middleware）
    set_user_context({"id": user_id, "email": "test@example.com", "name": "Test User"})
    set_jwt_token(token)
    
    print(f"\n✅ JWT Token 已设置到 context")
    print(f"   Backend URL: {settings.BACKEND_URL}")
    print(f"   Internal Token: {settings.INTERNAL_TOKEN[:20]}...")
    
    # 创建 Runtime
    runtime = AgentRuntime()
    
    # 创建 Client（会触发 MCP 配置）
    session_id = str(uuid.uuid4())
    task_id = f"task_{uuid.uuid4().hex[:16]}"
    
    print(f"\n🚀 创建 SDK Client: session_id={session_id}")
    
    # 调试：手动检查 MCP 配置
    from app.core.context import get_jwt_token
    from app.mcp.remote import create_backend_mcp_servers
    
    jwt_from_context = get_jwt_token()
    print(f"\n🔍 调试信息：")
    print(f"   JWT from context: {'<present>' if jwt_from_context else '<MISSING>'}")
    
    if jwt_from_context:
        test_mcp = create_backend_mcp_servers(auth_token=jwt_from_context)
        print(f"   MCP config keys: {list(test_mcp.keys())}")
        print(f"   MCP config: {test_mcp}")
    
    client = await runtime.get_or_create_client(
        session_id=session_id,
        user_id=user_id,
        task_id=task_id,
        model="claude-sonnet-4-20250514",
        max_turns=5,
    )
    
    print(f"✅ Client 创建成功")
    
    # 检查 Client 的配置
    print(f"\n📋 Client 配置信息：")
    print(f"   Model: {client._options.model if hasattr(client, '_options') else 'unknown'}")
    print(f"   MCP Servers: {client._options.mcp_servers if hasattr(client, '_options') and hasattr(client._options, 'mcp_servers') else 'unknown'}")
    
    # 尝试查询（不等待完整响应，只看初始化）
    print(f"\n🧪 发送测试查询...")
    
    await client.query("列出可用的工具")
    
    # 读取第一条消息（应该是 SystemMessage with init）
    async for message in client.receive_response():
        print(f"   收到消息: {type(message).__name__}")
        
        if hasattr(message, 'subtype') and message.subtype == 'init':
            data = message.data or {}
            tools = data.get('tools', [])
            print(f"\n✅ SDK 初始化消息：")
            print(f"   工具数量: {len(tools)}")
            print(f"   工具列表:")
            for tool in tools:
                print(f"      - {tool}")
            
            # 检查是否包含 Backend MCP 工具
            backend_tools = [t for t in tools if 'list_projects' in t or 'list_campaigns' in t]
            if backend_tools:
                print(f"\n🎉 找到 Backend MCP 工具: {backend_tools}")
            else:
                print(f"\n❌ 未找到 Backend MCP 工具（list_projects / list_campaigns）")
            
            break
        
        # 只读取前几条消息
        if message:
            break
    
    # 清理
    await runtime.disconnect_client(session_id)
    print(f"\n✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_mcp_registration())
