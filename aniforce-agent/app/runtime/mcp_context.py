"""Build the scoped MCP connection used by Agent Runtime executions."""

from contextlib import asynccontextmanager
from time import perf_counter

from agents.mcp import MCPServerStreamableHttp, MCPToolMetaContext
from loguru import logger

from app.agent.business_skills.tool_filter import business_skill_tool_filter
from app.config.settings import get_settings

APPROVAL_REQUIRED_TOOL_NAMES = [
    "create_project", "update_project", "delete_project",
    "create_campaign", "update_campaign", "update_campaign_status", "delete_campaign",
    "create_material", "update_material", "delete_material",
    "add_material_to_campaign", "remove_material_from_campaign",
    "add_material_to_project", "remove_material_from_project",
]


@asynccontextmanager
async def mcp_connection(
    *,
    auth_token: str,
    session_id: str,
    run_id: str,
    user_id: str,
    checkpoint_id: str = "",
    tool_call_ids_by_name: dict[str, str] | None = None,
):
    """Connect to the local MCP server with per-run authorization metadata."""
    settings = get_settings()
    mcp_url = f"http://127.0.0.1:{settings.PORT}/mcp"

    def resolve_meta(ctx: MCPToolMetaContext) -> dict[str, str] | None:
        meta = {
            key: value
            for key, value in {
                "jwt_token": auth_token,
                "session_id": session_id,
                "run_id": run_id,
                "user_id": user_id,
                "checkpoint_id": checkpoint_id,
            }.items()
            if value
        }
        if tool_call_ids_by_name:
            tool_call_id = tool_call_ids_by_name.get(ctx.tool_name)
            if tool_call_id:
                meta["tool_call_id"] = tool_call_id
        return meta or None

    server = MCPServerStreamableHttp(
        name="ANIFORCE Tools",
        params={"url": mcp_url, "timeout": 30},
        cache_tools_list=True,
        max_retry_attempts=2,
        require_approval={"always": {"tool_names": APPROVAL_REQUIRED_TOOL_NAMES}},
        tool_meta_resolver=resolve_meta,
        tool_filter=business_skill_tool_filter,
    )
    started = perf_counter()
    perf_log = logger.bind(session_id=session_id, user_id=user_id, run_id=run_id)
    try:
        await server.__aenter__()
        perf_log.debug(
            "[PERF][agent_first_token] runtime.mcp_connected mcp_connect_ms={}",
            int((perf_counter() - started) * 1000),
        )
        yield [server]
    finally:
        try:
            await server.__aexit__(None, None, None)
        except Exception as exc:
            logger.warning("[RUNTIME] MCP cleanup error: {}", exc)
