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


@mcp.tool()
async def list_meta_ad_accounts_with_spend(
    ctx: Context,
    since: str = "",
    until: str = "",
) -> dict:
    """列出当前用户 Meta 广告账号及本地已同步窗口内的消耗。

    数据来自 ANIFORCE backend 的 meta_facts，不直接请求 Meta。没有事实不等于消耗为 0，返回中会保留数据质量和同步状态。
    """
    token = _get_token(ctx)
    window_since, window_until = _window(since, until)
    accounts = await backend_client.list_meta_ad_accounts(token)
    grouped: dict[str, dict] = {}
    for account in accounts:
        connection_id = str(account.get("connection_id") or "")
        if not connection_id:
            continue
        row = grouped.setdefault(
            connection_id,
            {"connection_id": connection_id, "connection_name": account.get("connection_name"), "accounts": []},
        )
        account_id = str(account.get("account_id") or account.get("sub_account_id") or "")
        if not account_id:
            continue
        try:
            overview = await backend_client.get_meta_dashboard_overview(
                token,
                connection_id=connection_id,
                since=window_since,
                until=window_until,
                account_id=account_id.removeprefix("act_"),
            )
            kpis = overview.get("kpis") or {}
            quality = overview.get("data_quality") or {}
            spend = kpis.get("spend")
        except Exception as exc:
            row["accounts"].append({
                "account_id": account_id,
                "account_name": account.get("account_name") or account.get("name") or account_id,
                "status": "query_failed",
                "error": str(exc),
            })
            continue
        row["accounts"].append({
            "account_id": account_id,
            "account_name": account.get("account_name") or account.get("name") or account_id,
            "spend": spend,
            "currency": (overview.get("window") or {}).get("currency"),
            "status": (quality.get("status") or "unknown"),
            "data_quality": quality,
        })
    return {"window": {"since": window_since, "until": window_until}, "connections": list(grouped.values())}


@mcp.tool()
async def get_meta_account_performance(
    ctx: Context,
    connection_id: str,
    account_id: str,
    since: str = "",
    until: str = "",
    objective: str = "",
) -> dict:
    """查询指定 Meta 广告账号的本地事实表现，可按 Sales 或 Leads Objective 隔离。"""
    token = _get_token(ctx)
    window_since, window_until = _window(since, until)
    return await backend_client.get_meta_dashboard_overview(
        token,
        connection_id=connection_id,
        account_id=account_id.removeprefix("act_"),
        since=window_since,
        until=window_until,
        objective=objective or None,
    )


@mcp.tool()
async def get_meta_campaign_performance(
    ctx: Context,
    connection_id: str,
    since: str = "",
    until: str = "",
    account_id: str = "",
    objective: str = "",
) -> dict:
    """查询 Meta Campaign 和 AdSet 三级表现，来源为本地 meta_facts 聚合结果。"""
    token = _get_token(ctx)
    window_since, window_until = _window(since, until)
    overview = await backend_client.get_meta_dashboard_overview(
        token,
        connection_id=connection_id,
        account_id=account_id.removeprefix("act_") or None,
        since=window_since,
        until=window_until,
        objective=objective or None,
    )
    return {
        "window": overview.get("window"),
        "scope": overview.get("scope"),
        "objectives": overview.get("objectives", []),
        "campaigns": overview.get("campaigns", []),
        "adsets": overview.get("adsets", []),
        "data_quality": overview.get("data_quality"),
    }


@mcp.tool()
async def get_meta_performance_trend(
    ctx: Context,
    connection_id: str,
    since: str = "",
    until: str = "",
    account_id: str = "",
    objective: str = "",
) -> dict:
    """查询 Meta 本地事实的逐日花费与结果趋势。"""
    token = _get_token(ctx)
    window_since, window_until = _window(since, until)
    overview = await backend_client.get_meta_dashboard_overview(
        token,
        connection_id=connection_id,
        account_id=account_id.removeprefix("act_") or None,
        since=window_since,
        until=window_until,
        objective=objective or None,
    )
    return {
        "window": overview.get("window"),
        "scope": overview.get("scope"),
        "trend": overview.get("trend", []),
        "kpis": overview.get("kpis"),
        "previous": overview.get("previous"),
        "data_quality": overview.get("data_quality"),
    }
