"""Read MCP request metadata and build backend audit headers."""

import hashlib
import json

from loguru import logger


def get_meta(ctx) -> dict:
    try:
        meta = ctx.request_context.meta
        if isinstance(meta, dict):
            return meta
        if hasattr(meta, "model_dump"):
            return meta.model_dump() or {}
        if meta is not None:
            return {
                "jwt_token": getattr(meta, "jwt_token", "") or "",
                "session_id": getattr(meta, "session_id", "") or "",
                "run_id": getattr(meta, "run_id", "") or "",
                "user_id": getattr(meta, "user_id", "") or "",
                "checkpoint_id": getattr(meta, "checkpoint_id", "") or "",
                "tool_call_id": getattr(meta, "tool_call_id", "") or "",
            }
    except Exception as exc:
        logger.warning("[MCP] 读取 meta 失败: {}", exc)
    return {}


def get_token(ctx) -> str:
    token = get_meta(ctx).get("jwt_token", "")
    if not token:
        logger.warning("[MCP] request_context.meta 无 jwt_token")
    return token


def make_tool_call_id(ctx, tool_name: str, arguments: dict) -> str | None:
    meta = get_meta(ctx)
    session_id = meta.get("session_id")
    run_id = meta.get("run_id")
    if not session_id or not run_id:
        return None
    raw = json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{session_id}:{run_id}:{tool_name}:{digest}"


def backend_headers(
    ctx,
    tool_name: str | None = None,
    arguments: dict | None = None,
) -> dict[str, str]:
    meta = get_meta(ctx)
    headers: dict[str, str] = {}
    if meta.get("session_id"):
        headers["X-Agent-Session-Id"] = str(meta["session_id"])
    if meta.get("run_id"):
        headers["X-Agent-Run-Id"] = str(meta["run_id"])
    if meta.get("tool_call_id"):
        headers["X-Agent-Tool-Call-Id"] = str(meta["tool_call_id"])
    if tool_name and arguments is not None:
        idempotency_key = make_tool_call_id(ctx, tool_name, arguments)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
    return headers


def compact_payload(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def compact_update_payload(data: dict, *identity_fields: str) -> dict:
    """Remove SDK defaults and object identity from partial-update bodies."""
    identities = set(identity_fields)
    return {
        key: value
        for key, value in data.items()
        if key not in identities and value is not None and value != ""
    }
