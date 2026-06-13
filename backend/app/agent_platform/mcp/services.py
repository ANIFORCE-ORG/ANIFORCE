"""
MCP 服务注册

将所有 MCP 服务注册到主应用

在这里集中管理所有 MCP 服务的创建和配置
"""

from mcp.server.fastmcp import FastMCP
from loguru import logger

from app.agent_platform.mcp.manager import get_mcp_manager
from app.agent_platform.mcp.middleware import MCPAuthMiddleware
from app.agent_platform.mcp.context import (
    get_current_user_id,
    get_current_user_type,
    set_mcp_request_context,
)
from app.repositories.factory import get_project_repo, get_campaign_repo
from app.config.database import get_db


def create_project_campaign_service() -> FastMCP:
    """
    创建项目和广告投放管理 MCP 服务
    
    提供工具：
    - 项目管理：list_projects, get_project_detail, create_project, delete_project
    - 广告投放：list_campaigns, get_campaign_detail, create_campaign, update_campaign_status, delete_campaign
    """
    
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
        set_mcp_request_context(request)
        response = await call_next(request)
        return response
    
    # ==================== 项目管理工具 ====================
    
    @mcp.tool()
    async def list_projects(status: str = None, limit: int = 20) -> str:
        """获取用户的项目列表"""
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
        """获取项目详情"""
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
        
        return result
    
    @mcp.tool()
    async def create_project(
        name: str,
        total_budget: float,
        description: str = None,
        game_type: str = None,
        target_market: str = None
    ) -> str:
        """创建新项目"""
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
        """删除项目"""
        user_id = get_current_user_id()
        
        async for session in get_db():
            project_repo = await get_project_repo(session)
            project = await project_repo.get_by_id(project_id)
            
            if not project:
                return f"错误：项目 {project_id} 不存在。"
            
            if project["user_id"] != user_id:
                return f"错误：无权删除项目 {project_id}。"
            
            project_name = project['name']
            await project_repo.delete(project_id)
            await session.commit()
        
        return f"✅ 项目 '{project_name}' 已删除。"
    
    # ==================== 广告投放工具 ====================
    
    @mcp.tool()
    async def list_campaigns(
        project_id: str = None,
        status: str = None,
        limit: int = 50
    ) -> str:
        """获取广告投放计划列表"""
        user_id = get_current_user_id()
        
        async for session in get_db():
            campaign_repo = await get_campaign_repo(session)
            project_repo = await get_project_repo(session)
            
            if project_id:
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
                projects = await project_repo.list_by_user(user_id, limit=100)
                campaigns = []
                for project in projects:
                    project_campaigns = await campaign_repo.list_by_project(
                        project_id=project["id"],
                        status=status,
                        limit=limit
                    )
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
    async def create_campaign(
        project_id: str,
        name: str,
        platform: str,
        budget: float,
        status: str = "draft"
    ) -> str:
        """创建广告投放计划"""
        user_id = get_current_user_id()
        
        async for session in get_db():
            campaign_repo = await get_campaign_repo(session)
            project_repo = await get_project_repo(session)
            
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
"""
    
    @mcp.tool()
    async def update_campaign_status(campaign_id: str, status: str) -> str:
        """更新广告投放状态"""
        user_id = get_current_user_id()
        
        async for session in get_db():
            campaign_repo = await get_campaign_repo(session)
            project_repo = await get_project_repo(session)
            
            campaign = await campaign_repo.get_by_id(campaign_id)
            if not campaign:
                return f"错误：广告投放 {campaign_id} 不存在。"
            
            project = await project_repo.get_by_id(campaign["project_id"])
            if not project or project["user_id"] != user_id:
                return f"错误：无权修改广告投放 {campaign_id}。"
            
            await campaign_repo.update_status(campaign_id, status)
            await session.commit()
        
        return f"✅ 广告投放 '{campaign['name']}' 状态已更新为：{status}"
    
    @mcp.tool()
    async def delete_campaign(campaign_id: str) -> str:
        """删除广告投放"""
        user_id = get_current_user_id()
        
        async for session in get_db():
            campaign_repo = await get_campaign_repo(session)
            project_repo = await get_project_repo(session)
            
            campaign = await campaign_repo.get_by_id(campaign_id)
            if not campaign:
                return f"错误：广告投放 {campaign_id} 不存在。"
            
            project = await project_repo.get_by_id(campaign["project_id"])
            if not project or project["user_id"] != user_id:
                return f"错误：无权删除广告投放 {campaign_id}。"
            
            campaign_name = campaign['name']
            await campaign_repo.delete(campaign_id)
            await session.commit()
        
        return f"✅ 广告投放 '{campaign_name}' 已删除。"
    
    return mcp


def register_all_services():
    """
    注册所有 MCP 服务
    
    在应用启动时调用
    """
    manager = get_mcp_manager()
    
    # 注册项目和广告投放服务
    project_campaign_service = create_project_campaign_service()
    manager.register_service(
        name="project_campaign",
        service=project_campaign_service,
        port=8001
    )
    
    # TODO: 注册更多服务
    # material_service = create_material_service()
    # manager.register_service("material", material_service, port=8002)
    
    logger.info("All MCP services registered")
