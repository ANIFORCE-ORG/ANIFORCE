"""
MCP 模块
"""

from .middleware import MCPAuthMiddleware
from .context import (
    get_current_user_id,
    get_current_user_type,
    get_current_user_email,
    get_current_user_info,
    set_mcp_request_context,
)
from .manager import get_mcp_manager, MCPServiceManager
from .services import register_all_services

__all__ = [
    "MCPAuthMiddleware",
    "get_current_user_id",
    "get_current_user_type",
    "get_current_user_email",
    "get_current_user_info",
    "set_mcp_request_context",
    "get_mcp_manager",
    "MCPServiceManager",
    "register_all_services",
]
