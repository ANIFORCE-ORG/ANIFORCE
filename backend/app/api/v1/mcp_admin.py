"""
MCP 调试和管理 API

提供 MCP 服务的状态查询和调试能力
"""

from fastapi import APIRouter, HTTPException
from app.agent_platform.mcp.manager import get_mcp_manager
from app.schemas.base import ResponseBase

router = APIRouter(prefix="/mcp", tags=["MCP管理"])


@router.get("/status")
async def get_mcp_status():
    """
    获取 MCP 服务状态
    
    返回所有已注册、运行中、活跃的 MCP 服务信息
    """
    manager = get_mcp_manager()
    status = manager.get_service_status()
    
    return ResponseBase(data={
        "status": "ok",
        "services": status,
        "summary": {
            "registered": len(status.get("registered", [])),
            "running": len(status.get("running", [])),
            "active": len(status.get("active_servers", [])),
            "failed": len(status.get("failed_servers", [])),
        }
    })


@router.get("/servers")
async def list_mcp_servers():
    """
    列出所有活跃的 MCP 服务器
    
    返回可供 Agent 使用的 MCP 服务器列表
    """
    manager = get_mcp_manager()
    active_servers = manager.get_active_servers()
    
    servers_info = []
    for server in active_servers:
        info = {
            "name": server.name,
            "type": "streamable_http",
            "url": server.params.get("url") if hasattr(server, "params") else None,
        }
        servers_info.append(info)
    
    return ResponseBase(data={
        "servers": servers_info,
        "count": len(servers_info),
    })


@router.get("/servers/{service_name}/tools")
async def list_service_tools(service_name: str):
    """
    列出指定 MCP 服务的所有工具
    
    用于调试和查看可用工具列表
    """
    manager = get_mcp_manager()
    service = manager.get_service(service_name)
    
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    # 从 FastMCP 获取工具列表
    tools = []
    if hasattr(service, '_tools'):
        for tool_name, tool_func in service._tools.items():
            tool_info = {
                "name": tool_name,
                "description": tool_func.__doc__ or "No description",
            }
            
            # 尝试获取参数信息
            if hasattr(tool_func, '__annotations__'):
                tool_info["parameters"] = tool_func.__annotations__
            
            tools.append(tool_info)
    
    return ResponseBase(data={
        "service_name": service_name,
        "tools": tools,
        "count": len(tools),
    })


@router.post("/reload")
async def reload_mcp_services():
    """
    重新加载 MCP 服务（开发调试用）
    
    ⚠️ 生产环境慎用！
    """
    # TODO: 实现热重载逻辑
    # 1. 停止所有服务
    # 2. 重新注册
    # 3. 启动所有服务
    
    return ResponseBase(data={
        "message": "MCP services reload requested",
        "status": "not_implemented",
        "note": "需要实现热重载逻辑"
    })
