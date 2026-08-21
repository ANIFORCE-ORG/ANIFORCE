"""Build the Dashboard view model from campaign-level meta_facts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.services.dashboard_metrics import DailyFact, aggregate_dashboard_facts
from app.services.meta_fact_normalizer import normalize_account_id


def _action_map(items: list[dict[str, Any]] | None, *, decimal: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in items or []:
        action_type = item.get("action_type")
        value = item.get("value")
        if not action_type or value in (None, ""):
            continue
        try:
            result[action_type] = Decimal(str(value)) if decimal else int(Decimal(str(value)))
        except (InvalidOperation, ValueError):
            continue
    return result


class MetaDashboardService:
    def __init__(self, repository: Any):
        self.repository = repository

    async def overview(
        self,
        *,
        connection_id: str,
        since: date,
        until: date,
        result_action_type: str,
        account_id: str | None = None,
        use_link_clicks: bool = False,
    ) -> dict[str, Any]:
        if since > until:
            raise ValueError("since must not be after until")
        normalized_account_id = normalize_account_id(account_id) if account_id else None
        rows = await self.repository.list_daily_facts(
            connection_id=connection_id,
            account_id=normalized_account_id,
            since=since,
            until=until,
            level="campaign",
        )
        facts = [
            DailyFact(
                metric_date=row.metric_date.isoformat(),
                spend=row.spend,
                impressions=row.impressions,
                clicks=row.clicks,
                inline_link_clicks=row.inline_link_clicks,
                actions=_action_map(row.actions_json),
                action_values=_action_map(row.action_values_json, decimal=True),
                status=row.status,
                account_id=row.account_id,
            )
            for row in rows
        ]
        view = aggregate_dashboard_facts(
            facts,
            result_action_type=result_action_type,
            use_link_clicks=use_link_clicks,
        )
        currencies = sorted({row.account_currency for row in rows if row.account_currency})
        timezones = sorted({row.account_timezone for row in rows if row.account_timezone})
        view["window"] = {
            "since": since.isoformat(),
            "until": until.isoformat(),
            "currency": currencies[0] if len(currencies) == 1 else None,
            "timezone": timezones[0] if len(timezones) == 1 else None,
            "mixed_currency": len(currencies) > 1,
            "mixed_timezone": len(timezones) > 1,
        }
        return view
