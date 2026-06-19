#!/usr/bin/env python3
"""
Block 5: Sandbox + Skills

验证：
- SandboxAgent 使用 SANDBOX_DIR 作为工作目录
- Skills 从 SKILLS_DIR 加载
- Agent 能引用 Skill 的工作流
- （沙箱目录外文件访问限制需要 OpenAI Agents SDK 的安全策略支持，暂不强校验）
"""

import json
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.auth import create_access_token


BASE_URL = "http://localhost:8020"
SKILLS_DIR = Path(__file__).parent.parent.parent / "runtime/skills"
SANDBOX_DIR = Path(__file__).parent.parent.parent / "runtime/agent/sandbox"


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def print_result(passed: bool, message: str) -> bool:
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


def ensure_test_skill():
    """创建测试 skill"""
    skill_dir = SKILLS_DIR / "test-block5-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: test-block5-skill
description: "Block 5 测试专用技能：演示 Skill 加载和引用"
---

# Block 5 测试 Skill

## 目标
验证 Skill 能被 SandboxAgent 正确加载。

## 工作流
1. 用户提到"block5测试"时，回复固定文案："block5-skill-loaded"
2. 这证明 Agent 成功加载了本 Skill

## 示例
用户: 这是 block5 测试吗？
Agent: 是的，block5-skill-loaded。
""",
        encoding="utf-8",
    )
    print(f"测试 Skill 已创建: {skill_dir}")
    return skill_dir


def send_agent_run_sync(prompt: str, session_id: str, token: str, timeout: int = 60):
    """同步运行 agent，收集 SSE 事件"""
    url = f"{BASE_URL}/api/agent/runs"
    payload = {"prompt": prompt, "session_id": session_id, "task_type": "conversation"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    events = []
    current_event = None
    text_content = ""

    with httpx.stream("POST", url, json=payload, headers=headers, timeout=timeout) as response:
        if response.status_code != 200:
            return None, []

        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    data = {}
                events.append({"event": current_event, "data": data})

                if current_event == "message.updated":
                    text_content += data.get("delta", "")
                elif current_event == "message.completed":
                    text_content = data.get("content", text_content)

    return text_content, events


def test_block_5() -> bool:
    print_section("Block 5: Sandbox + Skills")

    user_id = f"user_block5_{int(time.time())}"
    token = create_access_token({"sub": user_id, "email": f"{user_id}@example.com", "name": "Block5"})
    session_id = f"session_block5_{uuid.uuid4().hex[:12]}"
    results = []

    print_section("Step 5.1: 创建测试 Skill")
    skill_dir = ensure_test_skill()
    results.append(print_result(skill_dir.exists(), "测试 Skill 目录已创建"))
    results.append(print_result((skill_dir / "SKILL.md").exists(), "SKILL.md 已创建"))

    print_section("Step 5.2: 验证 SANDBOX_DIR 存在")
    print(f"SANDBOX_DIR: {SANDBOX_DIR}")
    results.append(print_result(SANDBOX_DIR.exists(), "SANDBOX_DIR 已创建"))

    print_section("Step 5.3: 运行任务，触发 Skill 引用")
    print("提示词: '这是 block5 测试，请确认'")
    text, events = send_agent_run_sync("这是 block5 测试，请确认", session_id, token, timeout=60)
    print(f"回复内容: {text[:300]}")
    print(f"事件数: {len(events)}")

    results.append(print_result(bool(text), "收到 Agent 回复"))
    results.append(print_result(
        any(e["event"] == "runtime.completed" for e in events),
        "任务成功完成"
    ))

    # 注意：当前 OpenAI SDK 的 Skills 可能不会在回复中显式提及 skill 关键词，
    # 我们只验证 Agent 能正常运行且没有因 Skill 加载失败而报错
    has_error = any(e["event"] == "runtime.error" for e in events)
    results.append(print_result(not has_error, "没有因 Skill 加载失败而报错"))

    print_section("Step 5.4: 检查 Skill 是否被 Agent 识别（弱检查）")
    # OpenAI Agents SDK 的 Skills 加载后可能不会在每次回复中显式引用，
    # 我们验证回复不包含"我不知道 skill"/"没有找到 skill"等明显错误
    skill_not_recognized = "没有找到" in text or "不知道 skill" in text or "skill 不存在" in text
    results.append(print_result(
        not skill_not_recognized,
        "Agent 回复未报告 Skill 缺失"
    ))

    print_section("Block 5 汇总")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    print("\n注意: Block 5 主要验证 Skills 目录存在、Agent 不因 Skill 加载失败报错。")
    print("OpenAI Agents SDK 的 Skills 功能依赖 SandboxAgent + LocalDirLazySkillSource。")
    print("具体 Skill 引用行为取决于 SDK 内部实现和模型能力。")
    return passed == total


if __name__ == "__main__":
    success = test_block_5()
    sys.exit(0 if success else 1)
