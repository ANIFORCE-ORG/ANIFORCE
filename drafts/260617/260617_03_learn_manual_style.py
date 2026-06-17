"""对照学习手册方式：用 profile + env 显式构造 + CLAUDE_CONFIG_DIR 隔离"""
import asyncio
import os
import sys
from pathlib import Path

# 复用学习手册的通用模块
LEARNING_DIR = Path(__file__).resolve().parents[1] / "260615_claude_sdk_learning"
sys.path.insert(0, str(LEARNING_DIR / "examples"))

from sdk_learning_common import load_profile_env, mask_secret, prepare_clean_dir, LEARNING_DIR, OUT_DIR  # noqa: E402
from claude_agent_sdk import query, ClaudeAgentOptions  # noqa: E402


async def main():
    # 用 copilot_sonnet（与 aniforce-agent/.env 一致）
    loaded = load_profile_env("copilot_sonnet")
    print("token 指纹:", mask_secret(loaded.get("ANTHROPIC_AUTH_TOKEN", "")))
    print("base_url:", loaded.get("ANTHROPIC_BASE_URL"))
    print("model:", loaded.get("CLAUDE_AGENT_MODEL"))
    print()

    # 显式 env：只带 ANTHROPIC_* / CLAUDE_* + client app 标识 + 配置隔离
    env = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_")
    }
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-e2e-probe/0.1"
    # 隔离：用学习手册已验证的空配置目录，避免本机 hooks/plugins/skills 注入
    env["CLAUDE_CONFIG_DIR"] = str(LEARNING_DIR / "examples" / "01_claude_config_sandbox")

    # 干净沙箱
    sandbox = Path(__file__).parent / "sandbox"
    prepare_clean_dir(sandbox)

    opts = ClaudeAgentOptions(
        cwd=str(sandbox),
        model=os.getenv("CLAUDE_AGENT_MODEL", "claude-sonnet-4-6"),
        max_turns=1,
        allowed_tools=[],
        disallowed_tools=["Write", "Edit", "Bash"],
        permission_mode="dontAsk",
        system_prompt="You are a minimal probe. Reply briefly.",
        env=env,
        thinking={"type": "disabled"},
        effort="low",
    )

    print("开始 query()...")
    print("=" * 60)

    count = 0
    async for m in query(prompt="你好，请回复'收到'", options=opts):
        count += 1
        tname = type(m).__name__
        if tname == "SystemMessage":
            print(f"[{count}] SystemMessage subtype={m.subtype}")
            if m.subtype == "init":
                d = m.data
                print(f"    model={d.get('model')} apiKeySource={d.get('apiKeySource')}")
            if m.subtype == "api_retry":
                d = m.data
                print(f"    status={d.get('error_status')} error={d.get('error')} attempt={d.get('attempt')}/{d.get('max_retries')}")
        elif tname == "AssistantMessage":
            print(f"[{count}] AssistantMessage model={m.model}")
            for b in m.content:
                if type(b).__name__ == "TextBlock":
                    print(f"    text: {b.text!r}")
        elif tname == "ResultMessage":
            print(f"[{count}] ResultMessage subtype={m.subtype} is_error={m.is_error} turns={m.num_turns}")
            print(f"    result={getattr(m, 'result', None)!r}"[:300])
        else:
            print(f"[{count}] {tname}")

    print("=" * 60)
    print(f"总消息数: {count}")


asyncio.run(main())
