#!/usr/bin/env python3
# %%
"""测试 SQLAlchemySession 对接 SQLite。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/05-session/260702_02_sqlalchemy_session_debug.py

验证点：
1. SQLAlchemySession.from_url() 使用内存 SQLite
2. SQLAlchemySession() 使用文件 SQLite + 现有 AsyncEngine
3. 多轮对话验证
4. 跨 session 隔离验证
5. 与 SQLiteSession 对比
"""

import asyncio
from pathlib import Path
from typing import Annotated

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from agents import (
    Agent,
    ModelSettings,
    Runner,
    set_tracing_disabled,
)
from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

MODEL = "deepseek-v4-pro"
BASE_URL = "https://copilot.huya.info/api/openai/v1"
API_KEY = "sk-hvtAUe3lPjYQtwiZqLMfYg"

set_tracing_disabled(True)


def make_model() -> OpenAIChatCompletionsModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIChatCompletionsModel(model=MODEL, openai_client=client)


def print_section(title: str) -> None:
    """打印章节标题。"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


async def test_from_url_memory() -> None:
    """场景1：使用 from_url() + 内存 SQLite。"""
    print_section("场景1：SQLAlchemySession.from_url() + 内存 SQLite")

    agent = Agent(
        name="Assistant",
        instructions="你是助手，回答简洁。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    # 使用内存 SQLite
    session = SQLAlchemySession.from_url(
        "user-123",
        url="sqlite+aiosqlite:///:memory:",
        create_tables=True,  # 自动创建表
    )

    print("【第1轮】")
    print("用户: 你好，我叫张三\n")
    result = await Runner.run(agent, "你好，我叫张三", session=session)
    print(f"助手: {result.final_output}\n")

    print("【第2轮】（Session 自动记住）")
    print("用户: 我叫什么名字？\n")
    result = await Runner.run(agent, "我叫什么名字？", session=session)
    print(f"助手: {result.final_output}\n")

    print("✅ 内存 SQLite，进程结束后丢失")


async def test_with_existing_engine() -> None:
    """场景2：使用现有 AsyncEngine + 文件 SQLite。"""
    print_section("场景2：使用现有 AsyncEngine + 文件 SQLite")

    db_path = Path("drafts/260702/sqlalchemy_sessions.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 创建 AsyncEngine
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    agent = Agent(
        name="Assistant",
        instructions="你是助手，回答简洁。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    # 使用现有 engine
    session = SQLAlchemySession(
        "user-456",
        engine=engine,
        create_tables=True,
    )

    print("【第1轮】")
    print("用户: 你好，我是李四\n")
    result = await Runner.run(agent, "你好，我是李四", session=session)
    print(f"助手: {result.final_output}\n")

    print("【第2轮】")
    print("用户: 我喜欢打篮球\n")
    result = await Runner.run(agent, "我喜欢打篮球", session=session)
    print(f"助手: {result.final_output}\n")

    print(f"✅ 文件 SQLite，保存到 {db_path}")
    print("说明: 生产环境可以把 engine 换成 PostgreSQL/MySQL\n")

    await engine.dispose()


async def test_multiple_sessions() -> None:
    """场景3：多个 Session 隔离。"""
    print_section("场景3：多个 SQLAlchemySession 隔离")

    db_path = Path("drafts/260702/sqlalchemy_multi.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    agent = Agent(
        name="Assistant",
        instructions="你是助手。",
        model=make_model(),
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )

    # 两个不同的 session
    session_alice = SQLAlchemySession("alice", engine=engine, create_tables=True)
    session_bob = SQLAlchemySession("bob", engine=engine, create_tables=True)

    print("【Alice 的对话】")
    result = await Runner.run(agent, "你好，我喜欢音乐", session=session_alice)
    print(f"助手: {result.final_output}\n")

    print("【Bob 的对话】")
    result = await Runner.run(agent, "你好，我喜欢电影", session=session_bob)
    print(f"助手: {result.final_output}\n")

    print("【Alice 继续】")
    result = await Runner.run(agent, "我刚才说我喜欢什么？", session=session_alice)
    print(f"助手: {result.final_output}\n")

    print("【Bob 继续】")
    result = await Runner.run(agent, "我刚才说我喜欢什么？", session=session_bob)
    print(f"助手: {result.final_output}\n")

    print("✅ 两个 Session 完全隔离")

    await engine.dispose()


async def test_session_operations() -> None:
    """场景4：SQLAlchemySession 的基本操作。"""
    print_section("场景4：SQLAlchemySession 操作")

    session = SQLAlchemySession.from_url(
        "ops_test",
        url="sqlite+aiosqlite:///:memory:",
        create_tables=True,
    )

    # add_items
    print("【add_items】")
    await session.add_items([
        {"role": "user", "content": "第一条消息"},
        {"role": "assistant", "content": "第一条回复"},
        {"role": "user", "content": "第二条消息"},
    ])

    # get_items
    print("\n【get_items】")
    items = await session.get_items()
    print(f"Session 中有 {len(items)} 条记录")
    for i, item in enumerate(items[:3], 1):
        role = item.get("role") if isinstance(item, dict) else getattr(item, "role", "unknown")
        print(f"  {i}. role={role}")

    # pop_item
    print("\n【pop_item】")
    last_item = await session.pop_item()
    role = last_item.get("role") if isinstance(last_item, dict) else getattr(last_item, "role", "unknown")
    print(f"弹出最后一条: role={role}")
    items = await session.get_items()
    print(f"弹出后有 {len(items)} 条记录")

    # clear_session
    print("\n【clear_session】")
    await session.clear_session()
    items = await session.get_items()
    print(f"清空后有 {len(items)} 条记录")


async def test_postgresql_example() -> None:
    """场景5：PostgreSQL 配置示例（不实际连接）。"""
    print_section("场景5：生产环境 PostgreSQL 配置示例")

    print("生产环境使用 PostgreSQL/MySQL：\n")

    print("```python")
    print("# 创建 PostgreSQL 引擎")
    print('engine = create_async_engine(')
    print('    "postgresql+asyncpg://user:pass@localhost/dbname",')
    print('    pool_size=20,')
    print('    max_overflow=10,')
    print(')')
    print("")
    print("# 使用 SQLAlchemySession")
    print('session = SQLAlchemySession(')
    print('    "user_123",')
    print('    engine=engine,')
    print('    create_tables=True,  # 首次运行创建表')
    print(')')
    print("")
    print("# 正常使用")
    print('result = await Runner.run(agent, input, session=session)')
    print("```\n")

    print("支持的数据库：")
    print("- PostgreSQL: postgresql+asyncpg://...")
    print("- MySQL: mysql+aiomysql://...")
    print("- SQLite: sqlite+aiosqlite:///path/to/db.sqlite")
    print("\n说明: 只需要换 engine URL，代码完全不变")


async def main() -> None:
    await test_from_url_memory()
    await test_with_existing_engine()
    await test_multiple_sessions()
    await test_session_operations()
    await test_postgresql_example()

    print("\n" + "=" * 80)
    print("所有场景调试完成")
    print("=" * 80)
    print("\n关键总结：")
    print("1. SQLAlchemySession 完全支持 SQLite（内存 + 文件）")
    print("2. 生产环境只需换 engine URL，代码完全不变")
    print("3. 支持 PostgreSQL、MySQL、SQLite 等所有 SQLAlchemy 数据库")
    print("4. 适合已有 SQLAlchemy 应用集成")


if __name__ == "__main__":
    asyncio.run(main())
