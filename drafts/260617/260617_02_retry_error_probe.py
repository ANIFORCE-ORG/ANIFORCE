"""单点排查：api_retry 的真实错误信息"""
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANIFORCE_AGENT = PROJECT_ROOT / "aniforce-agent"
sys.path.insert(0, str(ANIFORCE_AGENT))

from app.config.settings import get_settings
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    s = get_settings()
    os.environ["ANTHROPIC_API_KEY"] = s.ANTHROPIC_API_KEY
    os.environ["ANTHROPIC_AUTH_TOKEN"] = s.ANTHROPIC_AUTH_TOKEN
    os.environ["ANTHROPIC_BASE_URL"] = s.ANTHROPIC_BASE_URL

    cwd = ANIFORCE_AGENT / "runtime" / "sessions" / "retry_probe"
    cwd.mkdir(parents=True, exist_ok=True)

    opts = ClaudeAgentOptions(
        cwd=str(cwd),
        model=s.CLAUDE_AGENT_MODEL,
        thinking={"type": "disabled"},
        effort="low",
        tools=[],
        max_turns=1,
    )

    async for m in query(prompt="hi", options=opts):
        tname = type(m).__name__
        if tname == "SystemMessage" and m.subtype == "api_retry":
            d = m.data
            print("RETRY: status=%s attempt=%s/%s" % (
                d.get("error_status"),
                d.get("attempt"),
                d.get("max_retries"),
            ))
            print("  error=%s" % (d.get("error"),))
        elif tname == "SystemMessage" and m.subtype == "init":
            d = m.data
            print("INIT: model=%s apiKeySource=%s cwd=%s" % (
                d.get("model"),
                d.get("apiKeySource"),
                d.get("cwd"),
            ))
        elif tname == "ResultMessage":
            print("RESULT: subtype=%s is_error=%s" % (m.subtype, m.is_error))
            r = getattr(m, "result", None)
            print("  result=%r" % (r,))[:500]
        else:
            print("%s: subtype=%s" % (tname, getattr(m, "subtype", None)))


asyncio.run(main())
