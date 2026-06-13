"""
MCP 上下文工具

在 MCP 工具中获取当前用户信息

使用 ContextVar 保证线程安全和异步安全
"""

from contextvars import ContextVar
from typing import Optional
from starlette.requests import Request


# MCP 请求上下文变量
_mcp_request_context: ContextVar[Optional[Request]] = ContextVar(
    "_mcp_request_context", 
    default=None
)


def set_mcp_request_context(request: Request) -> None:
    """
    设置 MCP 请求上下文
    
    通常由中间件或 MCP 服务启动时调用
    """
    _mcp_request_context.set(request)


def get_current_user_id() -> str:
    """
    从上下文获取当前用户 ID
    
    用于 MCP 工具中获取当前请求的用户身份
    
    Raises:
        RuntimeError: 上下文未设置或用户未认证
        
    Example:
        @mcp.tool()
        def get_campaigns() -> str:
            user_id = get_current_user_id()
            campaigns = db.query(Campaign).filter_by(user_id=user_id).all()
            return f"Found {len(campaigns)} campaigns"
    """
    request = _mcp_request_context.get()
    
    if request is None:
        raise RuntimeError("MCP request context not set")
    
    if not hasattr(request.state, "user_id"):
        raise RuntimeError("User not authenticated in MCP request")
    
    return request.state.user_id


def get_current_user_type() -> str:
    """
    获取当前用户类型
    
    Returns:
        str: "user" | "admin"
    """
    request = _mcp_request_context.get()
    
    if request is None:
        raise RuntimeError("MCP request context not set")
    
    return getattr(request.state, "user_type", "user")


def get_current_user_email() -> str:
    """
    获取当前用户邮箱
    """
    request = _mcp_request_context.get()
    
    if request is None:
        raise RuntimeError("MCP request context not set")
    
    return getattr(request.state, "user_email", "")


def get_current_user_info() -> dict:
    """
    获取当前用户完整信息
    
    Returns:
        dict: {"id": str, "type": str, "email": str}
    """
    return {
        "id": get_current_user_id(),
        "type": get_current_user_type(),
        "email": get_current_user_email(),
    }


# 便捷别名
get_user_id = get_current_user_id
get_user_type = get_current_user_type
