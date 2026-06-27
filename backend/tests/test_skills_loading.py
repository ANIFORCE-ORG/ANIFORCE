"""
测试 Skills 加载机制
"""

from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agent_platform.adapters.openai_adapter import OpenAISDKAdapter
from agents import Agent
from agents.sandbox import SandboxAgent


def test_skills_directory_exists():
    """测试 Skills 目录存在"""
    # 从测试文件目录找到 backend 根目录
    backend_root = Path(__file__).parent.parent
    skills_dir = backend_root / "runtime" / "skills"
    assert skills_dir.exists(), f"Skills 目录不存在: {skills_dir}"
    
    # 检查子目录
    expected_skills = [
        "project-management",
        "campaign-management",
        "data-analysis",
        "hitl-operations",
    ]
    
    for skill_name in expected_skills:
        skill_path = skills_dir / skill_name
        assert skill_path.exists(), f"Skill 目录不存在: {skill_path}"
        
        skill_md = skill_path / "SKILL.md"
        assert skill_md.exists(), f"SKILL.md 不存在: {skill_md}"


def test_adapter_with_skills():
    """测试 Adapter 启用 Skills"""
    backend_root = Path(__file__).parent.parent
    skills_dir = str(backend_root / "runtime" / "skills")
    
    adapter = OpenAISDKAdapter(
        model="gpt-4o-mini",
        skills_dir=skills_dir
    )
    
    # 创建 Agent（启用 Skills）
    agent = adapter.create_agent(
        name="Test Agent",
        instructions="你是测试 Agent",
        enable_skills=True
    )
    
    # 验证 Agent 是 SandboxAgent
    assert isinstance(agent, SandboxAgent), f"预期 SandboxAgent，实际: {type(agent)}"
    print(f"✅ Agent 类型正确: {type(agent).__name__}")


def test_adapter_without_skills():
    """测试 Adapter 不启用 Skills"""
    backend_root = Path(__file__).parent.parent
    skills_dir = str(backend_root / "runtime" / "skills")
    
    adapter = OpenAISDKAdapter(
        model="gpt-4o-mini",
        skills_dir=skills_dir
    )
    
    # 创建 Agent（不启用 Skills）
    agent = adapter.create_agent(
        name="Test Agent",
        instructions="你是测试 Agent",
        enable_skills=False
    )
    
    # 验证是普通 Agent
    assert isinstance(agent, Agent), f"预期 Agent，实际: {type(agent)}"
    assert not isinstance(agent, SandboxAgent), "不应该是 SandboxAgent"
    print(f"✅ Agent 类型正确: {type(agent).__name__}")


def test_adapter_with_nonexistent_skills_dir():
    """测试 Adapter 使用不存在的 Skills 目录"""
    adapter = OpenAISDKAdapter(
        model="gpt-4o-mini",
        skills_dir="nonexistent/skills/dir"
    )
    
    # 创建 Agent（Skills 目录不存在，应降级为普通 Agent）
    agent = adapter.create_agent(
        name="Test Agent",
        instructions="你是测试 Agent",
        enable_skills=True  # 虽然启用，但目录不存在
    )
    
    # 验证降级为普通 Agent
    assert isinstance(agent, Agent), f"预期 Agent，实际: {type(agent)}"
    assert not isinstance(agent, SandboxAgent), "Skills 目录不存在时应降级为普通 Agent"
    print(f"✅ Skills 目录不存在时正确降级: {type(agent).__name__}")


if __name__ == "__main__":
    print("=== 测试 Skills 加载机制 ===\n")
    
    print("测试 1: Skills 目录存在")
    test_skills_directory_exists()
    print("✅ 通过\n")
    
    print("测试 2: Adapter 启用 Skills")
    test_adapter_with_skills()
    print("✅ 通过\n")
    
    print("测试 3: Adapter 不启用 Skills")
    test_adapter_without_skills()
    print("✅ 通过\n")
    
    print("测试 4: Adapter 使用不存在的 Skills 目录")
    test_adapter_with_nonexistent_skills_dir()
    print("✅ 通过\n")
    
    print("=== 所有测试通过 ✅ ===")
