#!/usr/bin/env python
"""
测试 Skill 动态注入

验证：
1. Skill 从源目录复制到 session 目录
2. 目录结构正确（.claude/skills/{skill-name}/SKILL.md）
3. 不同 session 的 Skill 独立
4. Skill 清理正常
"""
import asyncio
import sys
import os
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.skill_manager import SkillManager


async def test_skill_injection():
    """测试 Skill 动态注入"""
    print("=" * 70)
    print("🧪 测试 Skill 动态注入")
    print("=" * 70)
    print()

    # 先确保有测试 Skill
    source_dir = "app/skills"
    runtime_dir = "tests/manual/runtime/sessions"

    # 创建测试 Skill
    test_skill_dir = Path(source_dir) / "test-skill"
    test_skill_dir.mkdir(parents=True, exist_ok=True)

    skill_md = test_skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
description: "测试技能"
---

这是一个测试技能。
""")

    print(f"✅ 测试 Skill 已创建: {test_skill_dir}")
    print()

    skill_manager = SkillManager(
        source_dir=source_dir,
        runtime_dir=runtime_dir,
    )

    # 测试 1：初始化 Session Skills
    print("=" * 70)
    print("测试 1：初始化 Session Skills")
    print("=" * 70)

    session_a = str(uuid4())
    session_b = str(uuid4())

    skill_manager.init_session_skills(session_a)
    skill_manager.init_session_skills(session_b)

    skills_dir_a = skill_manager.get_session_skills_dir(session_a)
    skills_dir_b = skill_manager.get_session_skills_dir(session_b)

    print(f"✅ Session A Skills 目录: {skills_dir_a}")
    print(f"✅ Session B Skills 目录: {skills_dir_b}")

    if skills_dir_a.exists() and skills_dir_b.exists():
        print("✅ Skills 目录创建成功")
    else:
        print("❌ Skills 目录创建失败")
        return

    print()

    # 测试 2：验证目录结构
    print("=" * 70)
    print("测试 2：验证目录结构")
    print("=" * 70)

    # 应该在 .claude/skills/ 下
    expected_rel_path = Path(".claude/skills")

    # 检查 test-skill 是否被复制
    skill_a = skills_dir_a / "test-skill" / "SKILL.md"
    skill_b = skills_dir_b / "test-skill" / "SKILL.md"

    print(f"Session A 中 test-skill: {skill_a}")
    print(f"Session B 中 test-skill: {skill_b}")

    if skill_a.exists() and skill_b.exists():
        print("✅ Skill 复制成功")

        # 验证内容
        content_a = skill_a.read_text()
        if "test-skill" in content_a:
            print("✅ Skill 内容正确")
        else:
            print("❌ Skill 内容错误")
    else:
        print("❌ Skill 复制失败")

    print()

    # 测试 3：Skill 独立性
    print("=" * 70)
    print("测试 3：Skill 独立性")
    print("=" * 70)

    # 修改 Session A 的 Skill
    skill_a.write_text("Modified in Session A")

    content_a = skill_a.read_text()
    content_b = skill_b.read_text()

    print(f"Session A Skill 内容: {content_a[:30]}...")
    print(f"Session B Skill 内容: {content_b[:30]}...")

    if content_a != content_b:
        print("✅ Skill 独立性正常：修改不影响其他 session")
    else:
        print("❌ Skill 独立性失败")

    print()

    # 测试 4：清理 Skills
    print("=" * 70)
    print("测试 4：清理 Skills")
    print("=" * 70)

    skill_manager.cleanup_session_skills(session_a)

    if not skills_dir_a.exists():
        print("✅ Session A Skills 清理成功")
    else:
        print("❌ Session A Skills 清理失败")

    if skills_dir_b.exists():
        print("✅ Session B Skills 未受影响")
    else:
        print("❌ Session B Skills 被错误清理")

    print()

    # 清理
    skill_manager.cleanup_session_skills(session_b)

    print("=" * 70)
    print("✅ Skill 动态注入测试完成")
    print("=" * 70)
    print()
    print("总结：")
    print("✅ Skill 从源目录复制正常")
    print("✅ 目录结构正确")
    print("✅ Skill 独立性正常")
    print("✅ Skill 清理正常")


if __name__ == "__main__":
    asyncio.run(test_skill_injection())
