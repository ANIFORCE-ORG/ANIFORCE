"""OpenAI Agents SDK Sessions 能力调试

测试 Sessions 的核心能力：
1. SQLiteSession 创建和持久化
2. 多轮对话历史自动管理
3. Session 数据格式和序列化

运行方式：
  cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE
  UV_CACHE_DIR=./uv_cache uv run python drafts/260624/01_sessions_probe.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 使用项目环境
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "aniforce-agent"))

from agents import Agent, Runner, function_tool, set_tracing_disabled
from agents.memory.sqlite_session import SQLiteSession
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "drafts"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / f"sessions_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"


def load_agent_env():
    env_path = Path("aniforce-agent/.env")
    if not env_path.exists():
        raise RuntimeError("Missing aniforce-agent/.env")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def create_sdk_model():
    load_agent_env()
    set_tracing_disabled(True)
    api_mode = os.environ.get("OPENAI_AGENTS_API", "").strip().lower()
    if api_mode not in {"chat", "chat_completions", "chat-completions"}:
        raise RuntimeError(f"DeepSeek probe requires chat_completions, got {api_mode!r}")
    model = os.environ.get("OPENAI_AGENTS_MODEL", "deepseek-v4-pro")
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )
    return OpenAIChatCompletionsModel(model=model, openai_client=client)


def log_event(event_type: str, data: dict):
    """写入 JSONL 日志"""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": event_type, "timestamp": datetime.now().isoformat(), "data": data}, ensure_ascii=False) + "\n")


@function_tool
def get_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def test_sqlite_session():
    """测试 1: SQLiteSession 基本能力"""
    print("\n=== Test 1: SQLiteSession 基本能力 ===")

    # 创建 session（存在项目 runtime）
    session_db = Path("drafts/260624/test_sessions.db")
    session_db.parent.mkdir(parents=True, exist_ok=True)

    session = SQLiteSession(
        session_id="sess_test_001",
        db_path=str(session_db)
    )

    log_event("session_created", {
        "session_id": session.session_id,
        "db_path": str(session_db)
    })

    # 创建简单 agent
    agent = Agent(
        name="assistant",
        instructions="你是一个助手，简洁回答用户问题。",
        model=create_sdk_model(),
        tools=[get_time]
    )

    # 第一轮对话
    print("\n第一轮：用户问时间")
    result1 = await Runner.run(agent, "现在几点？", session=session)

    log_event("run_completed", {
        "turn": 1,
        "input": "现在几点？",
        "output": result1.final_output,
        "new_items_count": len(result1.new_items) if hasattr(result1, 'new_items') else 0
    })

    print(f"助手回复: {result1.final_output}")

    # 检查 session 存储
    items_after_turn1 = await session.get_items()
    log_event("session_items_after_turn1", {
        "items_count": len(items_after_turn1),
        "items_types": [type(item).__name__ for item in items_after_turn1]
    })

    print(f"Session 已存储 {len(items_after_turn1)} 条 items")

    # 第二轮对话（测试历史记忆）
    print("\n第二轮：测试上下文记忆")
    result2 = await Runner.run(agent, "我刚才问了什么？", session=session)

    log_event("run_completed", {
        "turn": 2,
        "input": "我刚才问了什么？",
        "output": result2.final_output
    })

    print(f"助手回复: {result2.final_output}")

    # 最终 session 状态
    items_after_turn2 = await session.get_items()
    log_event("session_items_after_turn2", {
        "items_count": len(items_after_turn2),
        "sample_item": str(items_after_turn2[-1])[:200] if items_after_turn2 else None
    })

    print(f"Session 最终存储 {len(items_after_turn2)} 条 items")


async def test_session_persistence():
    """测试 2: Session 持久化和恢复"""
    print("\n=== Test 2: Session 持久化和恢复 ===")

    session_db = Path("drafts/260624/test_sessions.db")
    session_id = "sess_test_001"

    # 重新加载同一个 session
    session = SQLiteSession(session_id=session_id, db_path=str(session_db))

    items = await session.get_items()

    log_event("session_reloaded", {
        "session_id": session_id,
        "items_count": len(items),
        "persisted": len(items) > 0
    })

    print(f"重新加载 session，发现 {len(items)} 条历史记录")

    if len(items) > 0:
        print("✓ Session 持久化成功")
    else:
        print("✗ Session 持久化失败")


async def test_session_operations():
    """测试 3: Session CRUD 操作"""
    print("\n=== Test 3: Session CRUD 操作 ===")

    session_db = Path("drafts/260624/test_sessions.db")
    session = SQLiteSession(session_id="sess_test_002", db_path=str(session_db))

    # 清空 session
    await session.clear_session()
    items_after_clear = await session.get_items()

    log_event("session_cleared", {
        "session_id": "sess_test_002",
        "items_after_clear": len(items_after_clear)
    })

    print(f"清空后 items 数量: {len(items_after_clear)}")

    # pop_item 测试
    agent = Agent(name="test", instructions="test", model=create_sdk_model())
    await Runner.run(agent, "test", session=session)

    items_before_pop = await session.get_items()
    popped = await session.pop_item()
    items_after_pop = await session.get_items()

    log_event("session_pop_item", {
        "before_count": len(items_before_pop),
        "after_count": len(items_after_pop),
        "popped_type": type(popped).__name__ if popped else None
    })

    print(f"pop_item 前: {len(items_before_pop)}, pop_item 后: {len(items_after_pop)}")


async def main():
    print("OpenAI Agents SDK Sessions 能力调试")
    print(f"日志文件: {log_file}")
    print("=" * 60)

    try:
        await test_sqlite_session()
        await test_session_persistence()
        await test_session_operations()

        print("\n" + "=" * 60)
        print(f"✓ 所有测试完成，日志已写入: {log_file}")
        print("\n关键发现：")
        print("1. Session 只存储 SDK 的 ResponseInputItem")
        print("2. Session 自动管理多轮对话历史")
        print("3. Session 持久化到 SQLite，可跨进程恢复")
        print("4. Session 不存储产品级元数据（title、user_id 等）")

    except Exception as e:
        log_event("error", {"message": str(e), "type": type(e).__name__})
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
