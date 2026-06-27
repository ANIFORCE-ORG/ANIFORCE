#!/usr/bin/env python3
"""
测试 Skills 加载和 $ACTION_RUNNER 问题
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent_platform.adapters.openai_adapter import OpenAISDKAdapter
from app.config.settings import get_settings

async def test_skills_loading():
    """测试 Skills 是否正确加载"""
    settings = get_settings()
    
    adapter = OpenAISDKAdapter(
        model="claude-opus-4-6",
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        enable_tracing=False,
    )
    
    print(f"Skills 目录: {adapter.skills_dir}")
    print(f"Sandbox 目录: {adapter.sandbox_dir}")
    print(f"Skills 目录存在: {Path(adapter.skills_dir).exists()}")
    
    # 创建 Agent
    agent = adapter.create_agent(
        name="Test Agent",
        instructions="你是测试 Agent",
        mcp_servers=[],
        enable_skills=True,
    )
    
    print(f"\nAgent 类型: {type(agent).__name__}")
    print(f"Agent 名称: {agent.name}")
    
    # 检查 Agent 的 tools
    if hasattr(agent, 'tools'):
        print(f"\nAgent Tools: {agent.tools}")
    
    # 检查 capabilities
    if hasattr(agent, 'capabilities'):
        print(f"\nAgent Capabilities: {agent.capabilities}")
    
    # 尝试简单执行
    print("\n开始测试执行...")
    try:
        from agents import run
        session_id = "test_session"
        result = await run(
            agent,
            "测试消息",
            session_id=session_id,
        )
        print(f"执行成功!")
        print(f"结果: {result.final_output}")
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_skills_loading())
