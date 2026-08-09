"""MCP tool visibility integration for business skills.

Skills describe workflows and evidence contracts. They do not restrict the
runtime tool catalog; authorization and approval remain enforced by MCP and the
backend.
"""


def allowed_mcp_tools(context) -> None:
    """Return no allowlist so every registered MCP tool is visible."""
    return None


def business_skill_tool_filter(filter_context, tool) -> bool:
    """Keep all registered MCP tools visible for every run."""
    return True
