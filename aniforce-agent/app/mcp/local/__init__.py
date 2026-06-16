"""
本地 MCP 工具模块

包含直接在 Agent 服务内执行的工具，无需 HTTP 调用
"""

from app.mcp.local.task_tools import create_task_tools_mcp_config

__all__ = ["create_task_tools_mcp_config"]
