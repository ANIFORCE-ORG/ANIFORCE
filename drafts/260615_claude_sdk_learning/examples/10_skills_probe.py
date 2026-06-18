#!/usr/bin/env python
"""第 10 章：Skills（领域知识注入）验证

验证 Claude Agent SDK 的 Skills 系统：
1. Skills 是什么：预定义的领域知识和工作流
2. 如何配置 Skills（ClaudeAgentOptions.skills）
3. Skills 的触发机制（Skill tool）
4. Skills 与 Hooks 的集成
5. Skills 与 MCP 的关系

Skills 架构：
- SKILL.md frontmatter 定义元信息（name、description）
- SKILL.md body 包含领域知识、工作流、可用工具
- Skill tool 调用时，SDK 将 SKILL.md 注入到 context
- 模型根据 Skills 内容调用相应的 MCP 工具
- Skills 是"知识层"，MCP 是"能力层"

ANIFORCE 场景：
- 广告计划管理 Skill（campaign-management）
- 项目管理 Skill（project-management）
- 数据分析 Skill（data-analysis）
- HITL 操作 Skill（hitl-operations）
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# 添加 SDK 到 sys.path
sdk_path = Path(__file__).resolve().parents[3] / "resources" / "claude-agent-sdk-python" / "src"
if str(sdk_path) not in sys.path:
    sys.path.insert(0, str(sdk_path))

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk.types import (
    AssistantMessage,
    HookContext,
    HookInput,
    HookJSONOutput,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

# 全局统计
skill_stats = {
    "skill_tool_called": 0,
    "mcp_tools_called": 0,
    "campaigns_created": 0,
    "campaigns_listed": 0,
}

hook_stats = {
    "PreToolUse_triggered": 0,
    "skill_tool_intercepted": 0,
}

# 模拟广告计划数据
campaigns_db = {
    "proj_001": [
        {
            "id": "camp_001",
            "name": "Facebook 广告",
            "platform": "facebook",
            "budget": 20000,
            "status": "active",
        },
        {
            "id": "camp_002",
            "name": "Google Ads",
            "platform": "google",
            "budget": 15000,
            "status": "active",
        },
    ],
}


# ========== MCP 工具：广告计划管理 ==========
@tool(
    "list_campaigns",
    "查询广告计划列表",
    {"project_id": str},
)
async def list_campaigns(args: dict[str, Any]) -> dict[str, Any]:
    """查询广告计划列表"""
    skill_stats["mcp_tools_called"] += 1
    skill_stats["campaigns_listed"] += 1

    project_id = args.get("project_id", "")
    print(f"[MCP Tool] list_campaigns: project_id={project_id}")

    if project_id not in campaigns_db:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Project {project_id} has no campaigns",
                }
            ]
        }

    campaigns = campaigns_db[project_id]
    result = json.dumps(campaigns, indent=2, ensure_ascii=False)
    return {
        "content": [
            {
                "type": "text",
                "text": f"Found {len(campaigns)} campaigns:\n{result}",
            }
        ]
    }


@tool(
    "create_campaign",
    "创建新广告计划",
    {
        "project_id": str,
        "name": str,
        "platform": str,
        "budget": float,
    },
)
async def create_campaign(args: dict[str, Any]) -> dict[str, Any]:
    """创建新广告计划"""
    skill_stats["mcp_tools_called"] += 1
    skill_stats["campaigns_created"] += 1

    project_id = args.get("project_id", "")
    name = args.get("name", "")
    platform = args.get("platform", "")
    budget = args.get("budget", 0)

    print(f"[MCP Tool] create_campaign: project_id={project_id}, name={name}")

    # 验证预算
    if budget <= 0:
        return {
            "content": [
                {"type": "text", "text": "Error: Budget must be > 0"}
            ],
            "is_error": True,
        }

    # 创建广告计划
    campaign_id = f"camp_{len(campaigns_db.get(project_id, [])) + 1:03d}"
    new_campaign = {
        "id": campaign_id,
        "name": name,
        "platform": platform,
        "budget": budget,
        "status": "active",
    }

    if project_id not in campaigns_db:
        campaigns_db[project_id] = []
    campaigns_db[project_id].append(new_campaign)

    result = json.dumps(new_campaign, indent=2, ensure_ascii=False)
    return {
        "content": [
            {
                "type": "text",
                "text": f"✅ Created campaign:\n{result}",
            }
        ]
    }


# ========== PreToolUse Hook 审计 Skill 调用 ==========
async def audit_skill_tool(
    input_data: HookInput, tool_use_id: str | None, context: HookContext
) -> HookJSONOutput:
    """审计 Skill 工具调用"""
    hook_stats["PreToolUse_triggered"] += 1

    tool_name = input_data.get("tool_name", "")

    # 只审计 Skill 工具
    if tool_name == "Skill":
        hook_stats["skill_tool_intercepted"] += 1
        tool_input = input_data.get("tool_input", {})
        skill_name = tool_input.get("skill", "unknown")
        print(f"[PreToolUse Hook] Skill工具调用={skill_name}")

    return {}


# ========== 测试场景 ==========
async def test_skills_basic(test_name: str, prompt: str, options: ClaudeAgentOptions):
    """测试基本 Skills 功能"""
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"Prompt: {prompt}")
    print(f"{'='*60}\n")

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text[:500]}...")
                    elif isinstance(block, ToolUseBlock):
                        print(f"[Tool Call] {block.name}")
                        if block.input:
                            print(f"  Input: {json.dumps(block.input, ensure_ascii=False)[:200]}")
            elif isinstance(msg, ResultMessage):
                print(f"Result: stop_reason={msg.stop_reason}, is_error={msg.is_error}")


async def main():
    """主测试流程"""

    print("第 10 章：Skills（领域知识注入）验证")
    print("=" * 80)

    # 创建 MCP server（广告计划管理工具）
    campaign_server = create_sdk_mcp_server(
        name="campaign_tools",
        version="1.0.0",
        tools=[list_campaigns, create_campaign],
    )

    # Skills 路径：ANIFORCE 的 backend/runtime/skills/
    project_root = Path(__file__).resolve().parents[3]
    skills_dir = project_root / "backend" / "runtime" / "skills"

    print(f"\nSkills 目录: {skills_dir}")
    print(f"可用 Skills:")
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            print(f"  - {skill_dir.name}")

    # ========== 测试 A：启用单个 Skill ==========
    print("\n" + "=" * 80)
    print("测试 A: 启用 campaign-management Skill")
    print("=" * 80)

    options_a = ClaudeAgentOptions(
        mcp_servers={"campaign": campaign_server},
        allowed_tools=[
            "Skill",  # 必须允许 Skill 工具
            "mcp__campaign__list_campaigns",
            "mcp__campaign__create_campaign",
        ],
        skills=["campaign-management"],  # 启用广告计划管理 Skill
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Skill", hooks=[audit_skill_tool]),
            ],
        },
        # 必须包含 "project" 才能加载 SKILL.md 文件
        setting_sources=["project"],
        cwd=str(project_root),  # 设置工作目录到项目根
    )

    await test_skills_basic(
        "测试 A: 使用 Skill 查询广告计划",
        "Use the campaign-management skill to list campaigns for project proj_001",
        options_a,
    )

    # ========== 测试 B：使用 Skill 创建广告计划 ==========
    await test_skills_basic(
        "测试 B: 使用 Skill 创建广告计划",
        "Use the campaign-management skill to create a TikTok campaign for project proj_001 with budget 10000",
        options_a,
    )

    # ========== 测试 C：启用所有 Skills ==========
    print("\n" + "=" * 80)
    print("测试 C: 启用所有 Skills")
    print("=" * 80)

    options_c = ClaudeAgentOptions(
        mcp_servers={"campaign": campaign_server},
        allowed_tools=[
            "Skill",
            "mcp__campaign__list_campaigns",
            "mcp__campaign__create_campaign",
        ],
        skills="all",  # 启用所有 Skills
        setting_sources=["project"],
        cwd=str(project_root),
    )

    await test_skills_basic(
        "测试 C: 查看可用 Skills",
        "What skills are available?",
        options_c,
    )

    # ========== 测试 D：不启用 Skills ==========
    print("\n" + "=" * 80)
    print("测试 D: 不启用 Skills（对比）")
    print("=" * 80)

    options_d = ClaudeAgentOptions(
        mcp_servers={"campaign": campaign_server},
        allowed_tools=[
            "mcp__campaign__list_campaigns",
            "mcp__campaign__create_campaign",
        ],
        skills=[],  # 禁用所有 Skills
        setting_sources=["project"],
        cwd=str(project_root),
    )

    await test_skills_basic(
        "测试 D: 不使用 Skill 直接调用 MCP 工具",
        "List campaigns for project proj_001 using the list_campaigns tool directly",
        options_d,
    )

    # ========== 输出统计 ==========
    print("\n" + "=" * 80)
    print("Skills 统计:")
    print(json.dumps(skill_stats, indent=2, ensure_ascii=False))
    print("\nHook 统计:")
    print(json.dumps(hook_stats, indent=2, ensure_ascii=False))

    # ========== 输出当前数据库状态 ==========
    print("\n" + "=" * 80)
    print("广告计划数据库:")
    print(json.dumps(campaigns_db, indent=2, ensure_ascii=False))

    # ========== 保存结果 ==========
    output_dir = Path("drafts/260615_claude_sdk_learning/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "skill_stats": skill_stats,
        "hook_stats": hook_stats,
        "campaigns_db": campaigns_db,
        "conclusions": {
            "skills_system_works": skill_stats["skill_tool_called"] > 0,
            "skills_trigger_mcp": skill_stats["mcp_tools_called"] > 0,
            "hooks_intercept_skill": hook_stats["skill_tool_intercepted"] > 0,
        },
        "skills_architecture": {
            "skill_definition": "SKILL.md frontmatter + body",
            "skill_activation": "ClaudeAgentOptions.skills parameter",
            "skill_invocation": "Skill tool (must be in allowed_tools)",
            "skill_mcp_relation": "Skill describes workflows, MCP provides capabilities",
            "skill_context_injection": "SKILL.md content injected when Skill tool called",
        },
    }

    output_file = output_dir / "10_skills_probe_summary.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")

    # ========== Skills 使用建议 ==========
    print("\n" + "=" * 80)
    print("Skills 使用建议（ANIFORCE）:")
    print("=" * 80)
    print(
        """
1. Skills 定义（SKILL.md）
   - frontmatter: name, description（触发场景）
   - body: 领域知识、工作流、可用 MCP 工具、硬约束
   - 示例：backend/runtime/skills/campaign-management/SKILL.md

2. Skills 配置（ClaudeAgentOptions）
   - skills=["campaign-management"]：启用特定 Skill
   - skills="all"：启用所有 Skills
   - skills=[]：禁用所有 Skills
   - setting_sources=["project"]：必须包含才能加载 SKILL.md

3. Skills 触发
   - 模型判断任务是否匹配 Skill 描述
   - 调用 Skill 工具：Skill(skill="campaign-management")
   - SDK 注入 SKILL.md 内容到 context
   - 模型根据 Skill 内容调用 MCP 工具

4. Skills 与 MCP 的关系
   - Skills = 知识层（how to use）
   - MCP = 能力层（what you can do）
   - Skills 描述工作流，MCP 提供能力
   - Skills 不直接执行，而是指导模型调用 MCP 工具

5. ANIFORCE 迁移
   - 保留现有 Skills 目录结构
   - 配置 setting_sources=["project"]
   - 配置 cwd 到项目根目录
   - 在 allowed_tools 中添加 "Skill"
   - 在 skills 参数中指定启用哪些 Skills

6. Skills vs Hooks
   - Skills: 声明式知识注入（模型决策）
   - Hooks: 命令式拦截器（强制执行）
   - Skills 引导模型行为，Hooks 控制执行流程
"""
    )


if __name__ == "__main__":
    asyncio.run(main())
