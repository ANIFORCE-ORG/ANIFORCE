"""
MCP 工具模块

包含：
- local: 本地 SDK MCP 工具（直接在 Agent 服务内执行）
- remote: HTTP MCP 桥接（调用后端服务）
"""

from app.mcp.local import create_task_tools_mcp_config
from app.mcp.remote import (
    create_http_mcp_config,
    create_backend_mcp_servers,
    BackendToolName,
    get_backend_tool_names,
)

__all__ = [
    "create_task_tools_mcp_config",
    "create_http_mcp_config",
    "create_backend_mcp_servers",
    "BackendToolName",
    "get_backend_tool_names",
]
