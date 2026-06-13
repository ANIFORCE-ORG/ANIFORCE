"""
Project & Campaign Management MCP Server

将现有的项目和广告管理 API MCP 化，供 Agent 调用

核心理念：
- 复用现有的 Repository 和业务逻辑
- 自动从上下文获取 user_id（鉴权）
- 将 API 端点转换为 MCP 工具
"""

import os
import sys
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from mcp.server.fastmcp import FastMCP
from app.agent_platform.mcp import (
    MCPAuthMiddleware,
    get_current_user_id,
    set_mcp_request_context,
)
from app.repositories.factory import get_project_repo, get_campaign_repo
from app.config.database import get_db

# 创建 MCP 服务
mcp = FastMCP(
    "Project & Campaign Management",
    host="127.0.0.1",
    port=8001,
)

# 添加鉴权中间件
mcp.app.add_middleware(MCPAuthMiddleware)


# 添加上下文设置中间件
@mcp.app.middleware("http")
async def set_context_middleware(request, call_next):
    """设置 MCP 请求上下文"""
    set_mcp_request_context(request)
    response = await call_next(request)
    return response


# ==================== 项目管理工具 ====================

@mcp.tool()
async def list_projects(
    status: str = None,
    limit: int = 20
) -> str:
    """
    获取用户的项目列表
    
    Args:
        status: 项目状态过滤（可选）：active | completed | archived
        limit: 返回数量限制，默认 20
    
    Returns:
        项目列表的文本描述
    """
    user_id = get_current_user_id()
    
    async for session in get_db():
        project_repo = await get_project_repo(session)
        projects = await project_repo.list_by_user(
            user_id=user_id,
            status=status,
            limit=limit
        )
    
    if not projects:
        return "你还没有创建任何项目。"
    
    result = f"找到 {len(projects)} 个项目：\n\n"
    for i, project in enumerate(projects, 1):
        result += f"{i}. **{project['name']}**\n"
        result += f"   - ID: {project['id']}\n"
        result += f"   - 预算: ¥{project.get('total_budget', 0):,.0f}\n"
        result += f"   - 状态: {project.get('status', 'active')}\n"
        if project.get('description'):
            result += f"   - 描述: {project['description']}\n"
        result += "\n"
    
    return result


@mcp.tool()
async def get_project_detail(project_id: str) -> str:
    """
    获取项目详情
    
    Args:
        project_id: 项目 ID
    
    Returns:
        项目详细信息
    """
    user_id = get_current_user_id()
    
    async for session in get_db():
        project_repo = await get_project_repo(session)
        project = await project_repo.get_by_id(project_id)
    
    if not project:
        return f"错误：项目 {project_id} 不存在。"
    
    if project["user_id"] != user_id:
        return f"错误：无权访问项目 {project_id}。"
    
    result = f"# {project['name']}\n\n"
    result += f"**基本信息**\n"
    result += f"- ID: {project['id']}\n"
    result += f"- 总预算: ¥{project.get('total_budget', 0):,.0f}\n"
    result += f"- 状态: {project.get('status', 'active')}\n"
    result += f"- 创建时间: {project.get('created_at', 'N/A')}\n"
    
    if project.get('description'):
        result += f"\n**项目描述**\n{project['description']}\n"
    
    if project.get('game_type'):
        result += f"\n**游戏类型**: {project['game_type']}\n"
    
    if project.get('target_market'):
        result += f"**目标市场**: {project['target_market']}\n"
    
    if project.get('tags'):
        result += f"**标签**: {', '.join(project['tags'])}\n"
    
    return result


@mcp.tool()
async def create_project(
    name: str,
    total_budget: float,
    description: str = None,
    game_type: str = None,
    target_market: str = None
) -> str:
    """
    创建新项目
    
    Args:
        name: 项目名称
        total_budget: 总预算（人民币）
        description: 项目描述（可选）
        game_type: 游戏类型（可选）
        target_market: 目标市场（可选）
    
    Returns:
        创建结果
    """
    user_id = get_current_user_id()
    
    async for session in get_db():
        project_repo = await get_project_repo(session)
        project = await project_repo.create(
            user_id=user_id,
            name=name,
            total_budget=total_budget,
            description=description,
            game_type=game_type,
            target_market=target_market,
        )
        await session.commit()
    
    return f"""✅ 项目创建成功

项目 ID: {project['id']}
名称: {name}
预算: ¥{total_budget:,.0f}
状态: {project.get('status', 'active')}

你现在可以为这个项目创建广告投放计划了。
"""


@mcp.tool()
async def delete_project(project_id: str) -> str:
    """
    删除项目
    
    Args:
        project_id: 项目 ID
    
    Returns:
        删除结果
    """
    user_id = get_current_user_id()
    
    async for session in get_db():
        project_repo = await get_project_repo(session)
        project = await project_repo.get_by_id(project_id)
        
        if not project:
            return f"错误：项目 {project_id} 不存在。"
        
        if project["user_id"] != user_id:
            return f"错误：无权删除项目 {project_id}。"
        
        await project_repo.delete(project_id)
        await session.commit()
    
    return f"✅ 项目 '{project['name']}' 已删除。"


# ==================== 广告投放管理工具 ====================

@mcp.tool()
async def list_campaigns(
    project_id: str = None,
    status: str = None,
    limit: int = 50
) -> str:
    """
    获取广告投放计划列表
    
    Args:
        project_id: 项目 ID（可选，不提供则返回所有项目的投放）
        status: 状态过滤（可选）：draft | active | paused | completed
        limit: 返回数量限制，默认 50
    
    Returns:
        广告投放列表的文本描述
    """
    user_id = get_current_user_id()
    
    async for session in get_db():
        campaign_repo = await get_campaign_repo(session)
        project_repo = await get_project_repo(session)
        
        if project_id:
            # 验证项目权限
            project = await project_repo.get_by_id(project_id)
            if not project:
                return f"错误：项目 {project_id} 不存在。"
            if project["user_id"] != user_id:
                return f"错误：无权访问项目 {project_id}。"
            
            campaigns = await campaign_repo.list_by_project(
                project_id=project_id,
                status=status,
                limit=limit
            )
        else:
            # 获取用户所有项目的广告投放
            projects = await project_repo.list_by_user(user_id, limit=100)
            campaigns = []
            for project in projects:
                project_campaigns = await campaign_repo.list_by_project(
                    project_id=project["id"],
                    status=status,
                    limit=limit
                )
                # 添加项目名称
                for campaign in project_campaigns:
                    campaign["project_name"] = project["name"]
                campaigns.extend(project_campaigns)
    
    if not campaigns:
        return "没有找到广告投放计划。"
    
    result = f"找到 {len(campaigns)} 个广告投放计划：\n\n"
    for i, campaign in enumerate(campaigns, 1):
        result += f"{i}. **{campaign['name']}**\n"
        result += f"   - ID: {campaign['id']}\n"
        result += f"   - 项目: {campaign.get('project_name', 'N/A')}\n"
        result += f"   - 平台: {campaign['platform']}\n"
        result += f"   - 预算: ¥{campaign.get('budget', 0):,.0f}\n"
        result += f"   - 状态: {campaign.get('status', 'draft')}\n"
        result += "\n"
    
    return result


@mcp.tool()
async def get_campaign_detail(campaign_id: str) -> str:
    """
    获取广告投放详情
    
    Args:
        campaign_id: 广告投放 ID
    
    Returns:
        广告投放详细信息
    """
    user_id = get_current_user_id()
    
    async for session in get_db():
        campaign_repo = await get_campaign_repo(session)
        project_repo = await get_project_repo(session)
        
        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            return f"错误：广告投放 {campaign_id} 不存在。"
        
        # 验证权限
        project = await project_repo.get_by_id(campaign["project_id"])
        if not project or project["user_id"] != user_id:
            return f"错误：无权访问广告投放 {campaign_id}。"
    
    result = f"# {campaign['name']}\n\n"
    result += f"**基本信息**\n"
    result += f"- ID: {campaign['id']}\n"
    result += f"- 所属项目: {project['name']} ({project['id']})\n"
    result += f"- 投放平台: {campaign['platform']}\n"
    result += f"- 预算: ¥{campaign.get('budget', 0):,.0f}\n"
    result += f"- 状态: {campaign.get('status', 'draft')}\n"
    result += f"- 创建时间: {campaign.get('created_at', 'N/A')}\n"
    
    if campaign.get('material_ids'):
        result += f"\n**关联素材**: {len(campaign['material_ids'])} 个\n"
    
    return result


@mcp.tool()
async def create_campaign(
    project_id: str,
    name: str,
    platform: str,
    budget: float,
    status: str = "draft"
) -> str:
    """
    创建广告投放计划
    
    Args:
        project_id: 所属项目 ID
        name: 投放计划名称
        platform: 投放平台（meta | google | tiktok）
        budget: 预算（人民币）
        status: 初始状态，默认 draft
    
    Returns:
        创建结果
    """
    user_id = get_current_user_id()
    
    async for session in get_db():
        campaign_repo = await get_campaign_repo(session)
        project_repo = await get_project_repo(session)
        
        # 验证项目权限
        project = await project_repo.get_by_id(project_id)
        if not project:
            return f"错误：项目 {project_id} 不存在。"
        if project["user_id"] != user_id:
            return f"错误：无权在项目 {project_id} 下创建广告投放。"
        
        campaign = await campaign_repo.create(
            project_id=project_id,
            name=name,
            platform=platform,
            budget=budget,
            status=status,
            material_ids=[],
        )
        await session.commit()
    
    return f"""✅ 广告投放计划创建成功

投放 ID: {campaign['id']}
名称: {name}
平台: {platform}
预算: ¥{budget:,.0f}
状态: {status}
所属项目: {project['name']}

提示：计划已创建为"{status}"状态，你可以继续配置素材和详细设置。
"""


@mcp.tool()
async def update_campaign_status(
    campaign_id: str,
    status: str
) -> str:
    """
    更新广告投放状态
    
    Args:
        campaign_id: 广告投放 ID
        status: 新状态（draft | active | paused | completed）
    
    Returns:
        更新结果
    """
    user_id = get_current_user_id()
    
    async for session in get_db():
        campaign_repo = await get_campaign_repo(session)
        project_repo = await get_project_repo(session)
        
        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            return f"错误：广告投放 {campaign_id} 不存在。"
        
        # 验证权限
        project = await project_repo.get_by_id(campaign["project_id"])
        if not project or project["user_id"] != user_id:
            return f"错误：无权修改广告投放 {campaign_id}。"
        
        await campaign_repo.update_status(campaign_id, status)
        await session.commit()
    
    status_desc = {
        "draft": "草稿",
        "active": "运行中",
        "paused": "已暂停",
        "completed": "已完成"
    }.get(status, status)
    
    return f"✅ 广告投放 '{campaign['name']}' 状态已更新为：{status_desc}"


@mcp.tool()
async def delete_campaign(campaign_id: str) -> str:
    """
    删除广告投放
    
    Args:
        campaign_id: 广告投放 ID
    
    Returns:
        删除结果
    """
    user_id = get_current_user_id()
    
    async for session in get_db():
        campaign_repo = await get_campaign_repo(session)
        project_repo = await get_project_repo(session)
        
        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            return f"错误：广告投放 {campaign_id} 不存在。"
        
        # 验证权限
        project = await project_repo.get_by_id(campaign["project_id"])
        if not project or project["user_id"] != user_id:
            return f"错误：无权删除广告投放 {campaign_id}。"
        
        campaign_name = campaign['name']
        await campaign_repo.delete(campaign_id)
        await session.commit()
    
    return f"✅ 广告投放 '{campaign_name}' 已删除。"


if __name__ == "__main__":
    print("🚀 Starting Project & Campaign Management MCP Server...")
    print("📍 Listening on: http://127.0.0.1:8001/mcp")
    print("🔐 Authentication: Required (JWT Bearer Token)")
    print()
    print("Available Tools:")
    print("  Projects:")
    print("    - list_projects")
    print("    - get_project_detail")
    print("    - create_project")
    print("    - delete_project")
    print("  Campaigns:")
    print("    - list_campaigns")
    print("    - get_campaign_detail")
    print("    - create_campaign")
    print("    - update_campaign_status")
    print("    - delete_campaign")
    print()
    mcp.run(transport="streamable-http")
