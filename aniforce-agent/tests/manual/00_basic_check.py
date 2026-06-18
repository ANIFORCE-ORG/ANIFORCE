#!/usr/bin/env python
"""
简化测试：直接测试 API 配置和基础功能

不依赖 Claude SDK，直接验证：
1. 环境变量配置正确
2. SQLite 数据库可创建
3. JWT Token 可生成
4. Session Store 可读写
5. HTTP MCP 配置正确
"""
import asyncio
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import init_task_db
from app.core.auth import create_access_token, decode_access_token
from app.agent.session_store import SQLiteSessionStore
from app.mcp.remote import create_backend_mcp_servers
from app.core.context import set_jwt_token, get_jwt_token


async def test_environment():
    """测试环境变量配置"""
    print("=" * 60)
    print("测试 1：环境变量配置")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    backend_url = os.getenv("BACKEND_URL")

    print(f"✅ ANTHROPIC_API_KEY: {api_key[:20]}..." if api_key else "❌ 未设置")
    print(f"✅ ANTHROPIC_BASE_URL: {base_url}" if base_url else "❌ 未设置")
    print(f"✅ BACKEND_URL: {backend_url}" if backend_url else "❌ 未设置")
    print()


async def test_database():
    """测试数据库初始化"""
    print("=" * 60)
    print("测试 2：数据库初始化")
    print("=" * 60)

    try:
        await init_task_db()
        print("✅ SQLite 数据库初始化成功")

        db_path = os.getenv("TASK_DB_PATH")
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"✅ 数据库文件存在: {db_path} ({size} bytes)")
        else:
            print(f"❌ 数据库文件不存在: {db_path}")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
    print()


async def test_jwt_auth():
    """测试 JWT 认证"""
    print("=" * 60)
    print("测试 3：JWT 认证")
    print("=" * 60)

    try:
        # 创建 Token
        token = create_access_token({"sub": "test_user", "email": "test@example.com"})
        print(f"✅ JWT Token 创建成功: {token[:30]}...")

        # 解析 Token
        payload = decode_access_token(token)
        print(f"✅ JWT Token 解析成功: user_id={payload['sub']}")

        # Context 存储
        set_jwt_token(token)
        retrieved = get_jwt_token()
        if retrieved == token:
            print("✅ JWT Token Context 存储/读取正常")
        else:
            print("❌ JWT Token Context 存储失败")
    except Exception as e:
        print(f"❌ JWT 认证失败: {e}")
    print()


async def test_session_store():
    """测试 Session Store"""
    print("=" * 60)
    print("测试 4：Session Store 持久化")
    print("=" * 60)

    try:
        session_db_path = os.getenv("SESSION_DB_PATH")
        store = SQLiteSessionStore(session_db_path)

        # 测试写入
        test_key = {"project_key": "aniforce", "session_id": str(uuid4())}
        test_entries = [{"type": "test", "data": "hello"}]

        await store.append(test_key, test_entries)
        print("✅ Session 写入成功")

        # 测试读取
        loaded = await store.load(test_key)
        if loaded and len(loaded) == 1:
            print(f"✅ Session 读取成功: {len(loaded)} 条记录")
        else:
            print(f"❌ Session 读取失败")
    except Exception as e:
        print(f"❌ Session Store 失败: {e}")
    print()


async def test_http_mcp_config():
    """测试 HTTP MCP 配置"""
    print("=" * 60)
    print("测试 5：HTTP MCP 配置")
    print("=" * 60)

    try:
        token = create_access_token({"sub": "test_user"})
        config = create_backend_mcp_servers(auth_token=token)

        if config and "backend" in config:
            print("✅ HTTP MCP 配置生成成功")
            backend_config = config["backend"]
            print(f"   command: {backend_config.get('command')}")
            print(f"   args: {backend_config.get('args')}")

            headers = backend_config.get('env', {}).get('HTTP_HEADERS', '')
            if 'Authorization' in headers and 'X-Internal-Token' in headers:
                print("✅ HTTP 请求头配置正确（包含认证信息）")
            else:
                print("❌ HTTP 请求头配置错误")
        else:
            print("❌ HTTP MCP 配置生成失败")
    except Exception as e:
        print(f"❌ HTTP MCP 配置失败: {e}")
    print()


async def main():
    print()
    print("🧪 ANIFORCE Agent 服务基础功能测试")
    print()

    await test_environment()
    await test_database()
    await test_jwt_auth()
    await test_session_store()
    await test_http_mcp_config()

    print("=" * 60)
    print("✅ 所有基础测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
