"""
最小化 Claude SDK 验证：API Key 是否能正常输出
目的：对照学习手册已验证的配置，确认 aniforce-agent 的 .env 能跑通 query()
输出：消息类型、字段结构、文本内容
"""
import asyncio
import os
import sys
from pathlib import Path

# 项目根
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANIFORCE_AGENT = PROJECT_ROOT / "aniforce-agent"
sys.path.insert(0, str(ANIFORCE_AGENT))

from app.config.settings import get_settings
from claude_agent_sdk import query, ClaudeAgentOptions


async def test_minimal():
    settings = get_settings()

    print("=" * 60)
    print("环境配置（脱敏）")
    print("=" * 60)
    print(f"ANTHROPIC_API_KEY:     {settings.ANTHROPIC_API_KEY[:12]}...{settings.ANTHROPIC_API_KEY[-4:]}")
    print(f"ANTHROPIC_AUTH_TOKEN:  {settings.ANTHROPIC_AUTH_TOKEN[:12]}...{settings.ANTHROPIC_AUTH_TOKEN[-4:]}")
    print(f"ANTHROPIC_BASE_URL:    {settings.ANTHROPIC_BASE_URL}")
    print(f"CLAUDE_AGENT_MODEL:    {settings.CLAUDE_AGENT_MODEL}")
    print()

    # 注入进程环境（与学习手册一致：直接覆盖，不用 setdefault）
    os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
    os.environ["ANTHROPIC_AUTH_TOKEN"] = settings.ANTHROPIC_AUTH_TOKEN
    if settings.ANTHROPIC_BASE_URL:
        os.environ["ANTHROPIC_BASE_URL"] = settings.ANTHROPIC_BASE_URL

    # 工作目录（临时沙箱）
    cwd = Path(__file__).parent / "01_query_probe_sandbox"
    cwd.mkdir(exist_ok=True)

    print("=" * 60)
    print("调用 query()")
    print("=" * 60)
    print(f"CWD:    {cwd}")
    print(f"Prompt: 你好，请回复'收到'")
    print()

    options = ClaudeAgentOptions(
        cwd=str(cwd),
        model=settings.CLAUDE_AGENT_MODEL,
        thinking={"type": "disabled"},
        effort="low",
        tools=[],
        max_turns=2,
    )

    print("=" * 60)
    print("SDK 消息流（逐条）")
    print("=" * 60)

    count = 0
    text_collected = ""
    result_msg = None
    error = None

    try:
        async for message in query(prompt="你好，请回复'收到'", options=options):
            count += 1
            msg_type = type(message).__name__
            print(f"\n[{count}] {msg_type}")

            # 关键字段
            if hasattr(message, "subtype"):
                print(f"    subtype: {message.subtype}")
            if hasattr(message, "session_id"):
                print(f"    session_id: {message.session_id}")
            if hasattr(message, "data") and isinstance(message.data, dict):
                print(f"    data keys: {list(message.data.keys())}")

            # content blocks
            if hasattr(message, "content"):
                if isinstance(message.content, list):
                    print(f"    content blocks: {len(message.content)}")
                    for i, block in enumerate(message.content):
                        block_type = type(block).__name__
                        block_type_field = getattr(block, "type", None)
                        print(f"      [{i}] class={block_type} type={block_type_field}")
                        if hasattr(block, "text"):
                            text = getattr(block, "text", "") or ""
                            text_collected += text
                            print(f"          text: {text[:80]}")
                else:
                    print(f"    content: {str(message.content)[:80]}")

            # ResultMessage 终态
            if msg_type == "ResultMessage":
                result_msg = message
                print(f"    is_error: {message.is_error}")
                print(f"    num_turns: {message.num_turns}")
                print(f"    duration_ms: {message.duration_ms}")
                if hasattr(message, "total_cost_usd"):
                    print(f"    total_cost_usd: ${message.total_cost_usd}")

    except Exception as e:
        error = e
        print(f"\n❌ 异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("汇总")
    print("=" * 60)
    print(f"总消息数: {count}")
    print(f"收集文本: {text_collected!r}")
    print(f"ResultMessage: {'有' if result_msg else '无'}")
    if result_msg:
        print(f"  subtype: {result_msg.subtype}")
        print(f"  is_error: {result_msg.is_error}")
    print(f"异常: {type(error).__name__ if error else '无'}")

    # 判定
    success = (
        error is None
        and result_msg is not None
        and result_msg.is_error is False
        and len(text_collected) > 0
    )
    print()
    print(f"结论: {'✅ API Key 正常，能输出文本' if success else '❌ 异常或无输出'}")
    return success


if __name__ == "__main__":
    success = asyncio.run(test_minimal())
    sys.exit(0 if success else 1)
