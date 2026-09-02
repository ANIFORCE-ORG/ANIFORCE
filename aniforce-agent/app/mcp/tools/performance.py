"""Read-only Meta performance MCP tools backed by local meta_facts."""

from datetime import date, timedelta

from mcp.server.fastmcp import Context

from app.backend_client import backend_client
from app.mcp.context import get_token as _get_token
from app.mcp.server import mcp


def _window(since: str, until: str) -> tuple[str, str]:
    if since and until:
        start = date.fromisoformat(since)
        end = date.fromisoformat(until)
    else:
        end = date.today()
        start = end - timedelta(days=6)
    if start > end:
        raise ValueError("since must be before or equal to until")
    if (end - start).days > 89:
        raise ValueError("performance window cannot exceed 90 days")
    return start.isoformat(), end.isoformat()


def _objective(value: str) -> str | None:
    normalized = value.strip().upper()
    aliases = {
        "SALES": "OUTCOME_SALES",
        "SALE": "OUTCOME_SALES",
        "PURCHASE": "OUTCOME_SALES",
        "LEADS": "OUTCOME_LEADS",
        "LEAD": "OUTCOME_LEADS",
    }
    return aliases.get(normalized, normalized or None)


async def _overview(
    ctx: Context,
    *,
    connection_id: str = "",
    account_id: str = "",
    since: str = "",
    until: str = "",
    objective: str = "",
) -> dict:
    window_since, window_until = _window(since, until)
    return await backend_client.get_meta_dashboard_overview(
        _get_token(ctx),
        connection_id=connection_id or None,
        account_id=account_id.removeprefix("act_") or None,
        since=window_since,
        until=window_until,
        objective=_objective(objective),
    )


@mcp.tool()
async def list_meta_ad_accounts_with_spend(
    ctx: Context,
    since: str = "",
    until: str = "",
    objective: str = "",
) -> dict:
    """一次查询当前用户全部 Meta 连接的账号消耗与完整 Dashboard 数据。

    数据来自本地 meta_facts。宽泛的账号、Sales 或 Leads 表现查询只需调用本工具一次；
    不要再逐账号调用其他 performance 工具。没有事实不等于消耗为 0。
    """
    return await _overview(ctx, since=since, until=until, objective=objective)


@mcp.tool()
async def get_meta_account_performance(
    ctx: Context,
    account_id: str,
    connection_id: str = "",
    since: str = "",
    until: str = "",
    objective: str = "",
) -> dict:
    """一次查询指定 Meta 广告账号的完整 Dashboard 数据，可按 Objective 隔离。"""
    return await _overview(
        ctx,
        connection_id=connection_id,
        account_id=account_id,
        since=since,
        until=until,
        objective=objective,
    )


@mcp.tool()
async def get_meta_campaign_performance(
    ctx: Context,
    connection_id: str = "",
    since: str = "",
    until: str = "",
    account_id: str = "",
    objective: str = "",
) -> dict:
    """一次查询 Meta Campaign、AdSet 与完整 Dashboard 数据，来源为本地 meta_facts。"""
    return await _overview(
        ctx,
        connection_id=connection_id,
        account_id=account_id,
        since=since,
        until=until,
        objective=objective,
    )


@mcp.tool()
async def get_meta_performance_trend(
    ctx: Context,
    connection_id: str = "",
    since: str = "",
    until: str = "",
    account_id: str = "",
    objective: str = "",
) -> dict:
    """一次查询 Meta 逐日趋势与完整 Dashboard 数据，来源为本地 meta_facts。"""
    return await _overview(
        ctx,
        connection_id=connection_id,
        account_id=account_id,
        since=since,
        until=until,
        objective=objective,
    )
