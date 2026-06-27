"""
验证 Skills 是否正常注册并能被 Agent 识别
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agent_platform.adapters.openai_adapter import OpenAISDKAdapter
from agents.sandbox import SandboxAgent

def main():
    print("=" * 60)
    print("验证 Skills 注册情况")
    print("=" * 60)
    print()
    
    # 1. 创建 Adapter
    print("1️⃣ 创建 OpenAI SDK Adapter...")
    skills_dir = str(project_root / "runtime" / "skills")
    print(f"   Skills 目录: {skills_dir}")
    
    adapter = OpenAISDKAdapter(
        model="gpt-4o-mini",
        skills_dir=skills_dir
    )
    print("   ✅ Adapter 创建成功\n")
    
    # 2. 创建 Agent（启用 Skills）
    print("2️⃣ 创建 SandboxAgent（启用 Skills）...")
    agent = adapter.create_agent(
        name="ANIFORCE Assistant",
        instructions="你是 ANIFORCE AI 助手",
        enable_skills=True
    )
    print(f"   ✅ Agent 类型: {type(agent).__name__}")
    print(f"   ✅ 是否为 SandboxAgent: {isinstance(agent, SandboxAgent)}\n")
    
    # 3. 检查 Skills 是否被注入到 instructions
    print("3️⃣ 检查 Skills 是否注入到 System Prompt...")
    instructions = agent.instructions
    
    # 检查是否包含 Skills 索引
    if "skill" in instructions.lower():
        print("   ✅ Instructions 包含 'skill' 关键词")
    else:
        print("   ⚠️ Instructions 不包含 'skill' 关键词")
    
    # 尝试找到 Skills 索引部分
    print("\n4️⃣ 查找 Skills 索引...")
    lines = instructions.split('\n')
    
    found_skills = False
    skills_section = []
    in_skills_section = False
    
    for line in lines:
        if 'available skill' in line.lower():
            found_skills = True
            in_skills_section = True
            skills_section.append(line)
        elif in_skills_section:
            if line.strip().startswith('-') or line.strip().startswith('•'):
                skills_section.append(line)
            elif line.strip() == '':
                continue
            else:
                in_skills_section = False
    
    if found_skills:
        print("   ✅ 找到 Skills 索引！\n")
        print("   📋 Skills 列表：")
        for line in skills_section:
            print(f"      {line}")
        print()
    else:
        print("   ⚠️ 未找到 Skills 索引\n")
    
    # 4. 检查具体的 Skills
    print("5️⃣ 验证具体的 Skills...")
    expected_skills = [
        "project-management",
        "campaign-management", 
        "data-analysis",
        "hitl-operations"
    ]
    
    for skill_name in expected_skills:
        if skill_name in instructions:
            print(f"   ✅ {skill_name}")
        else:
            print(f"   ❌ {skill_name} 未找到")
    
    print()
    
    # 5. 显示完整的 instructions（截断版）
    print("6️⃣ System Prompt 预览（前 500 字符）...")
    print("-" * 60)
    print(instructions[:500] + "...\n")
    print("-" * 60)
    print()
    
    # 6. 检查 Skills 文件
    print("7️⃣ 检查 Skills 文件是否存在...")
    skills_path = Path(skills_dir)
    
    for skill_name in expected_skills:
        skill_file = skills_path / skill_name / "SKILL.md"
        if skill_file.exists():
            size = skill_file.stat().st_size
            print(f"   ✅ {skill_name}/SKILL.md ({size:,} 字节)")
        else:
            print(f"   ❌ {skill_name}/SKILL.md 不存在")
    
    print()
    
    # 总结
    print("=" * 60)
    print("验证总结")
    print("=" * 60)
    
    checks = [
        ("Adapter 创建", True),
        ("SandboxAgent 创建", isinstance(agent, SandboxAgent)),
        ("Skills 索引注入", found_skills),
        ("所有 Skills 文件存在", all((skills_path / s / "SKILL.md").exists() for s in expected_skills)),
    ]
    
    all_passed = all(check[1] for check in checks)
    
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
    
    print()
    if all_passed:
        print("🎉 所有检查通过！Skills 已正确注册并可用。")
    else:
        print("⚠️ 部分检查未通过，请检查上述失败项。")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
