"""Compatibility facade for the domain-organized MCP server."""

from app.mcp.approval import get_approved_arguments as _get_approved_arguments
from app.mcp.context import (
    backend_headers as _get_backend_headers,
    compact_payload as _compact_payload,
    get_token as _get_token,
)
from app.mcp.server import get_mcp_starlette_app, mcp

__all__ = [
    "_get_approved_arguments",
    "_get_backend_headers",
    "_compact_payload",
    "_get_token",
    "get_mcp_starlette_app",
    "mcp",
]
