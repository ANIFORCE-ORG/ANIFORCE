"""Read user-approved MCP arguments from the claimed Runtime checkpoint."""

import json

from loguru import logger

from app.mcp.context import get_meta


async def get_approved_arguments(ctx, tool_name: str) -> dict | None:
    meta = get_meta(ctx)
    run_id = meta.get("run_id")
    user_id = meta.get("user_id")
    checkpoint_id = meta.get("checkpoint_id")
    if not run_id or not user_id or not checkpoint_id:
        return None
    try:
        import aiosqlite

        from app.config.settings import get_settings

        db_url = get_settings().AGENT_RUNTIME_DB_URL
        if "sqlite" not in db_url:
            return None
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT approved_arguments_json, interruptions_json FROM runtime_checkpoints "
                "WHERE id = ? AND run_id = ? AND user_id = ? AND status = 'resuming' "
                "AND approved_arguments_json IS NOT NULL",
                (checkpoint_id, run_id, user_id),
            )
            row = await cursor.fetchone()
            if row:
                interruptions = json.loads(row["interruptions_json"] or "[]")
                matches_tool = any(
                    item.get("tool_name") == tool_name
                    for item in interruptions
                    if isinstance(item, dict)
                )
                if matches_tool and row["approved_arguments_json"]:
                    return json.loads(row["approved_arguments_json"])
    except Exception as exc:
        logger.warning("[MCP] 读取 approved_arguments 失败: {}", exc)
    return None
