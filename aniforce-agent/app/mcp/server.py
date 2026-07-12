"""FastMCP registry and application factory."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ANIFORCE Tools", stateless_http=True)

# Importing domain modules registers their tools on the shared registry.
from app.mcp.tools import campaigns, materials, projects  # noqa: E402,F401


def get_mcp_starlette_app():
    """Return the streamable HTTP application mounted by FastAPI."""
    return mcp.streamable_http_app()
