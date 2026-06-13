"""
MCP 路由 - 集成到主应用

不使用独立端口,而是作为主应用的路由:
- POST /api/v1/mcp - MCP 工具调用入口

复用主应用的鉴权中间件和上下文系统
"""

from fastapi import APIRouter, Request, HTTPException
from loguru import logger

from app.core.context import get_current_user
from app.repositories.factory import get_project_repo, get_campaign_repo
from app.config.database import get_db

router = APIRouter(prefix="/mcp", tags=["MCP"])


# ==================== MCP 工具定义 ====================

async def list_projects_tool(status: str = None, limit: int = 20) -> str:
    """获取用户的项目列表"""
    user = get_current_user()
    user_id = user["id"]
    
    logger.info(f"[MCP] list_projects for user_id={user_id}, status={status}, limit={limit}")
    
    async for session in get_db():
        project_repo = get_project_repo(session)
        projects = await project_repo.list_by_user(
            user_id=user_id,
            status=status,
            limit=limit
        )
    
    logger.info(f"[MCP] Found {len(projects)} projects for user {user_id}")

    if not projects:
        return "你还没有创建任何项目。"

    result = f"找到 {len(projects)} 个项目:\n\n"
    for i, project in enumerate(projects, 1):
        result += f"{i}. **{project['name']}**\n"
        result += f"   - ID: {project['id']}\n"
        result += f"   - 预算: ¥{project.get('total_budget', 0):,.0f}\n"
        result += f"   - 状态: {project.get('status', 'active')}\n"
        if project.get('description'):
            result += f"   - 描述: {project['description']}\n"
        result += "\n"

    return result


async def create_project_tool(
    name: str,
    total_budget: float,
    description: str = None,
    game_type: str = None,
) -> str:
    """创建新项目"""
    user = get_current_user()
    user_id = user["id"]

    async for session in get_db():
        project_repo = get_project_repo(session)  # 不需要 await
        project = await project_repo.create(
            user_id=user_id,
            name=name,
            total_budget=total_budget,
            description=description,
            game_type=game_type,
        )
        await session.commit()

    return f"""✅ 项目创建成功

项目 ID: {project['id']}
名称: {name}
预算: ¥{total_budget:,.0f}

你现在可以为这个项目创建广告投放计划了。
"""


async def list_campaigns_tool(
    project_id: str = None,
    status: str = None,
    limit: int = 50
) -> str:
    """获取广告投放计划列表"""
    user = get_current_user()
    user_id = user["id"]

    async for session in get_db():
        campaign_repo = get_campaign_repo(session)  # 不需要 await
        project_repo = get_project_repo(session)  # 不需要 await

        if project_id:
            project = await project_repo.get_by_id(project_id)
            if not project:
                return f"错误:项目 {project_id} 不存在。"
            if project["user_id"] != user_id:
                return f"错误:无权访问项目 {project_id}。"

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

    result = f"找到 {len(campaigns)} 个广告投放计划:\n\n"
    for i, campaign in enumerate(campaigns, 1):
        result += f"{i}. **{campaign['name']}**\n"
        result += f"   - ID: {campaign['id']}\n"
        result += f"   - 项目: {campaign.get('project_name', 'N/A')}\n"
        result += f"   - 平台: {campaign['platform']}\n"
        result += f"   - 预算: ¥{campaign.get('budget', 0):,.0f}\n"
        result += f"   - 状态: {campaign.get('status', 'draft')}\n"
        result += "\n"

    return result


async def create_campaign_tool(
    project_id: str,
    name: str,
    platform: str,
    budget: float,
    status: str = "draft"
) -> str:
    """创建广告投放计划"""
    user = get_current_user()
    user_id = user["id"]

    async for session in get_db():
        campaign_repo = get_campaign_repo(session)
        project_repo = get_project_repo(session)

        project = await project_repo.get_by_id(project_id)
        if not project:
            return f"错误:项目 {project_id} 不存在。"
        if project["user_id"] != user_id:
            return f"错误:无权在项目 {project_id} 下创建广告投放。"

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


async def get_project_detail_tool(project_id: str) -> str:
    """获取项目详情"""
    user = get_current_user()
    user_id = user["id"]

    async for session in get_db():
        project_repo = get_project_repo(session)
        project = await project_repo.get_by_id(project_id)

        if not project:
            return f"错误:项目 {project_id} 不存在。"
        if project["user_id"] != user_id:
            return f"错误:无权访问项目 {project_id}。"

        campaign_repo = get_campaign_repo(session)
        campaigns = await campaign_repo.list_by_project(project_id)

    result = f"""📁 项目详情

名称: {project['name']}
ID: {project['id']}
预算: ¥{project.get('total_budget', 0):,.0f}
状态: {project.get('status', 'active')}
"""

    if project.get('description'):
        result += f"描述: {project['description']}\n"
    if project.get('game_type'):
        result += f"游戏类型: {project['game_type']}\n"

    if campaigns:
        result += f"\n📊 广告投放计划 ({len(campaigns)} 个):\n"
        for camp in campaigns:
            result += f"  - {camp['name']} ({camp['platform']}) - ¥{camp['budget']:,.0f}\n"
    else:
        result += "\n还没有创建广告投放计划。\n"

    return result


async def update_project_tool(
    project_id: str,
    name: str = None,
    total_budget: float = None,
    description: str = None,
    status: str = None
) -> str:
    """更新项目信息"""
    user = get_current_user()
    user_id = user["id"]

    async for session in get_db():
        project_repo = get_project_repo(session)
        project = await project_repo.get_by_id(project_id)

        if not project:
            return f"错误:项目 {project_id} 不存在。"
        if project["user_id"] != user_id:
            return f"错误:无权修改项目 {project_id}。"

        updates = {}
        if name is not None:
            updates["name"] = name
        if total_budget is not None:
            updates["total_budget"] = total_budget
        if description is not None:
            updates["description"] = description
        if status is not None:
            updates["status"] = status

        updated_project = await project_repo.update(project_id, updates)
        await session.commit()

    return f"✅ 项目更新成功\n\n项目: {updated_project['name']}\nID: {project_id}"


async def delete_project_tool(project_id: str) -> str:
    """删除项目"""
    user = get_current_user()
    user_id = user["id"]

    async for session in get_db():
        project_repo = get_project_repo(session)
        project = await project_repo.get_by_id(project_id)

        if not project:
            return f"错误:项目 {project_id} 不存在。"
        if project["user_id"] != user_id:
            return f"错误:无权删除项目 {project_id}。"

        await project_repo.delete(project_id)
        await session.commit()

    return f"✅ 项目已删除: {project['name']}"


async def get_campaign_detail_tool(campaign_id: str) -> str:
    """获取广告投放计划详情"""
    user = get_current_user()
    user_id = user["id"]

    async for session in get_db():
        campaign_repo = get_campaign_repo(session)
        project_repo = get_project_repo(session)

        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            return f"错误:广告投放计划 {campaign_id} 不存在。"

        project = await project_repo.get_by_id(campaign["project_id"])
        if not project or project["user_id"] != user_id:
            return f"错误:无权访问该广告投放计划。"

    result = f"""📊 广告投放计划详情

名称: {campaign['name']}
ID: {campaign['id']}
平台: {campaign['platform']}
预算: ¥{campaign['budget']:,.0f}
状态: {campaign['status']}
所属项目: {project['name']}
"""

    return result


async def update_campaign_tool(
    campaign_id: str,
    name: str = None,
    budget: float = None,
    status: str = None
) -> str:
    """更新广告投放计划"""
    user = get_current_user()
    user_id = user["id"]

    async for session in get_db():
        campaign_repo = get_campaign_repo(session)
        project_repo = get_project_repo(session)

        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            return f"错误:广告投放计划 {campaign_id} 不存在。"

        project = await project_repo.get_by_id(campaign["project_id"])
        if not project or project["user_id"] != user_id:
            return f"错误:无权修改该广告投放计划。"

        updates = {}
        if name is not None:
            updates["name"] = name
        if budget is not None:
            updates["budget"] = budget
        if status is not None:
            updates["status"] = status

        updated = await campaign_repo.update(campaign_id, updates)
        await session.commit()

    return f"✅ 广告投放计划更新成功\n\n计划: {updated['name']}\nID: {campaign_id}"


async def delete_campaign_tool(campaign_id: str) -> str:
    """删除广告投放计划"""
    user = get_current_user()
    user_id = user["id"]

    async for session in get_db():
        campaign_repo = get_campaign_repo(session)
        project_repo = get_project_repo(session)

        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            return f"错误:广告投放计划 {campaign_id} 不存在。"

        project = await project_repo.get_by_id(campaign["project_id"])
        if not project or project["user_id"] != user_id:
            return f"错误:无权删除该广告投放计划。"

        await campaign_repo.delete(campaign_id)
        await session.commit()

    return f"✅ 广告投放计划已删除: {campaign['name']}"


# ==================== 工具注册表 ====================

TOOLS = {
    "list_projects": {
        "function": list_projects_tool,
        "description": "获取用户的项目列表",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "项目状态过滤(可选)"},
                "limit": {"type": "integer", "description": "返回数量限制,默认 20"}
            }
        }
    },
    "get_project_detail": {
        "function": get_project_detail_tool,
        "description": "获取项目详情",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID"}
            },
            "required": ["project_id"]
        }
    },
    "create_project": {
        "function": create_project_tool,
        "description": "创建新项目",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "项目名称"},
                "total_budget": {"type": "number", "description": "总预算(人民币)"},
                "description": {"type": "string", "description": "项目描述(可选)"},
                "game_type": {"type": "string", "description": "游戏类型(可选)"}
            },
            "required": ["name", "total_budget"]
        }
    },
    "update_project": {
        "function": update_project_tool,
        "description": "更新项目信息",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID"},
                "name": {"type": "string", "description": "项目名称(可选)"},
                "total_budget": {"type": "number", "description": "总预算(可选)"},
                "description": {"type": "string", "description": "项目描述(可选)"},
                "status": {"type": "string", "description": "项目状态(可选)"}
            },
            "required": ["project_id"]
        }
    },
    "delete_project": {
        "function": delete_project_tool,
        "description": "删除项目",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID"}
            },
            "required": ["project_id"]
        }
    },
    "list_campaigns": {
        "function": list_campaigns_tool,
        "description": "获取广告投放计划列表",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID(可选)"},
                "status": {"type": "string", "description": "状态过滤(可选)"},
                "limit": {"type": "integer", "description": "返回数量限制,默认 50"}
            }
        }
    },
    "get_campaign_detail": {
        "function": get_campaign_detail_tool,
        "description": "获取广告投放计划详情",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "广告投放计划 ID"}
            },
            "required": ["campaign_id"]
        }
    },
    "create_campaign": {
        "function": create_campaign_tool,
        "description": "创建广告投放计划",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "所属项目 ID"},
                "name": {"type": "string", "description": "投放计划名称"},
                "platform": {"type": "string", "description": "投放平台(meta | google | tiktok)"},
                "budget": {"type": "number", "description": "预算(人民币)"},
                "status": {"type": "string", "description": "初始状态,默认 draft"}
            },
            "required": ["project_id", "name", "platform", "budget"]
        }
    },
    "update_campaign": {
        "function": update_campaign_tool,
        "description": "更新广告投放计划",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "广告投放计划 ID"},
                "name": {"type": "string", "description": "投放计划名称(可选)"},
                "budget": {"type": "number", "description": "预算(可选)"},
                "status": {"type": "string", "description": "状态(可选)"}
            },
            "required": ["campaign_id"]
        }
    },
    "delete_campaign": {
        "function": delete_campaign_tool,
        "description": "删除广告投放计划",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "广告投放计划 ID"}
            },
            "required": ["campaign_id"]
        }
    }
}


# ==================== MCP 端点 ====================

@router.post("")
async def mcp_endpoint(request: Request):
    """
    MCP 工具调用入口

    接收 MCP 协议的工具调用请求,执行对应工具

    自动使用当前请求上下文中的用户信息(无需传递 user_id)
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    # 解析 MCP 请求
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    logger.debug(f"MCP request: method={method}, params={params}")

    # 处理 initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",  # MCP 协议版本
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "ANIFORCE MCP Server",
                    "version": "1.0.0"
                }
            }
        }

    # 处理 tools/list
    if method == "tools/list":
        tools_list = []
        for tool_name, tool_info in TOOLS.items():
            tools_list.append({
                "name": tool_name,
                "description": tool_info["description"],
                "inputSchema": tool_info["parameters"]
            })

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools_list
            }
        }

    # 处理 tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            }

        tool_info = TOOLS[tool_name]
        tool_func = tool_info["function"]

        try:
            # 执行工具(自动使用上下文中的用户信息)
            result_text = await tool_func(**arguments)

            logger.info(f"MCP tool executed: {tool_name}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
            }
        except Exception as e:
            logger.error(f"MCP tool error: {tool_name} - {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"错误:{str(e)}"
                        }
                    ],
                    "isError": True
                }
            }

    # 未知方法
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }


@router.get("/tools")
async def list_tools():
    """
    列出所有可用的 MCP 工具

    用于调试和查看
    """
    tools_list = []
    for tool_name, tool_info in TOOLS.items():
        tools_list.append({
            "name": tool_name,
            "description": tool_info["description"],
            "parameters": tool_info["parameters"]
        })

    return {
        "tools": tools_list,
        "count": len(tools_list)
    }
