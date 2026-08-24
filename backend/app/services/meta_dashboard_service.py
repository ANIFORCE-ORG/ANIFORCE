"""Build the Dashboard view model from AdSet-level meta_facts."""

from __future__ import annotations

from datetime import date, timedelta
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
        expected_accounts: list[dict[str, str]] | None = None,
        sync_accounts: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if since > until:
            raise ValueError("since must not be after until")
        normalized_account_id = normalize_account_id(account_id) if account_id else None
        rows = await self.repository.list_daily_facts(
            connection_id=connection_id,
            account_id=normalized_account_id,
            since=since,
            until=until,
            level="adset",
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
        grouped_adsets: dict[tuple[str, str], list[DailyFact]] = {}
        adset_meta: dict[tuple[str, str], dict[str, Any]] = {}
        for fact, row in zip(facts, rows):
            if not fact.account_id:
                continue
            key = (fact.account_id, getattr(row, "entity_id", "") or "")
            grouped_adsets.setdefault(key, []).append(fact)
            adset_meta[key] = {
                "account_id": fact.account_id,
                "account_name": getattr(row, "account_name", None) or fact.account_id,
                "adset_id": key[1],
                "adset_name": getattr(row, "entity_name", None) or key[1],
                "campaign_name": getattr(row, "parent_entity_name", None),
            }
        adset_views = [
            {
                **adset_meta[key],
                **aggregate_dashboard_facts(
                    items,
                    result_action_type=result_action_type,
                    use_link_clicks=use_link_clicks,
                )["kpis"],
            }
            for key, items in grouped_adsets.items()
        ]
        adset_views.sort(key=lambda item: (item["spend"] is None, -(item["spend"] or 0)))
        view["adsets"] = adset_views
        days = (until - since).days + 1
        previous_until = since - timedelta(days=1)
        previous_since = previous_until - timedelta(days=days - 1)
        previous_rows = await self.repository.list_daily_facts(
            connection_id=connection_id,
            account_id=normalized_account_id,
            since=previous_since,
            until=previous_until,
            level="adset",
        )
        previous_facts = [
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
            for row in previous_rows
        ]
        previous_view = aggregate_dashboard_facts(
            previous_facts,
            result_action_type=result_action_type,
            use_link_clicks=use_link_clicks,
        )
        view["previous"] = {
            "window": {"since": previous_since.isoformat(), "until": previous_until.isoformat()},
            "kpis": previous_view["kpis"],
        }
        grouped_accounts: dict[str, list[DailyFact]] = {}
        account_names: dict[str, str] = {}
        for fact, row in zip(facts, rows):
            if fact.account_id:
                grouped_accounts.setdefault(fact.account_id, []).append(fact)
                account_names[fact.account_id] = getattr(row, "account_name", None) or fact.account_id
        expected = expected_accounts or [
            {"account_id": account_id, "account_name": account_names.get(account_id, account_id)}
            for account_id in sorted(grouped_accounts)
        ]
        account_views = []
        for account in expected:
            current_id = normalize_account_id(account["account_id"])
            account_facts = grouped_accounts.get(current_id, [])
            account_view = aggregate_dashboard_facts(
                account_facts,
                result_action_type=result_action_type,
                use_link_clicks=use_link_clicks,
            )
            sync = (sync_accounts or {}).get(current_id, {})
            data_status = "with_delivery" if account_facts and any(fact.spend not in (None, 0) for fact in account_facts) else "no_delivery" if account_facts else "no_facts"
            account_views.append({
                "account_id": current_id,
                "account_name": account.get("account_name") or current_id,
                "sync_status": sync.get("status", "never_synced"),
                "data_status": data_status,
                "last_synced_at": sync.get("finished_at"),
                "error_code": sync.get("error_code"),
                "error_message": sync.get("error_message"),
                **account_view["kpis"],
            })
        currencies = sorted({row.account_currency for row in rows if row.account_currency})
        timezones = sorted({row.account_timezone for row in rows if row.account_timezone})
        present_accounts = {fact.account_id for fact in facts if fact.account_id}
        daily_accounts: dict[str, set[str]] = {}
        for fact in facts:
            if fact.account_id:
                daily_accounts.setdefault(fact.metric_date, set()).add(fact.account_id)
        for trend_row in view["trend"]:
            trend_row["accounts_with_facts"] = len(daily_accounts.get(trend_row["date"], set()))
            trend_row["accounts_expected"] = len(expected)
        view["accounts"] = account_views
        view["data_quality"].update({
            "accounts_with_rows": len(present_accounts),
            "accounts_expected": len(expected),
            "coverage_percent": round(len(present_accounts) / len(expected) * 100, 2) if expected else 0,
            "facts_scope": "AdSet × 日期",
        })
        view["window"] = {
            "since": since.isoformat(),
            "until": until.isoformat(),
            "currency": currencies[0] if len(currencies) == 1 else None,
            "timezone": timezones[0] if len(timezones) == 1 else None,
            "mixed_currency": len(currencies) > 1,
            "mixed_timezone": len(timezones) > 1,
        }
        return view
