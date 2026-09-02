"""Build the Dashboard view model from AdSet-level meta_facts.

The Dashboard is organized by Meta campaign objective because "success" is a
different metric per objective. Sales spend must never be divided by leads, and
lead spend must never be reported as revenue. Every objective view therefore
declares its own canonical result action and funnel.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Iterable

from app.services.dashboard_metrics import DailyFact, aggregate_dashboard_facts
from app.services.meta_fact_normalizer import normalize_account_id

OBJECTIVE_SALES = "OUTCOME_SALES"
OBJECTIVE_LEADS = "OUTCOME_LEADS"

# Only these two objectives have a verified canonical result action in the
# current facts. Other objectives stay visible as spend context but are not
# presented as analyzable result views.
SUPPORTED_OBJECTIVES = (OBJECTIVE_SALES, OBJECTIVE_LEADS)

OBJECTIVE_RESULT_ACTION = {
    OBJECTIVE_SALES: "purchase",
    OBJECTIVE_LEADS: "lead",
}

OBJECTIVE_LABELS = {
    OBJECTIVE_SALES: "销售",
    OBJECTIVE_LEADS: "线索",
    "OUTCOME_ENGAGEMENT": "互动",
    "OUTCOME_AWARENESS": "认知",
    "OUTCOME_TRAFFIC": "流量",
    "OUTCOME_APP_PROMOTION": "应用推广",
}

# Meta reports many aliases with identical values (view_content,
# onsite_web_view_content, omni_view_content, offsite_conversion.fb_pixel_...).
# Each funnel step locks a single canonical action so steps are never summed twice.
SALES_FUNNEL_STEPS = (
    ("view_content", "浏览商品"),
    ("add_to_cart", "加购"),
    ("initiate_checkout", "发起结账"),
    ("purchase", "购买"),
)


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


def _sum_optional(values: Iterable[int | Decimal | None]) -> int | Decimal | None:
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def _ratio(numerator: int | Decimal | None, denominator: int | Decimal | None) -> Decimal | None:
    if numerator is None or denominator in (None, 0):
        return None
    return Decimal(str(numerator)) / Decimal(str(denominator))


def _row_objective(row: Any) -> str | None:
    return getattr(row, "objective", None) or None


def _fact_of(row: Any) -> DailyFact:
    return DailyFact(
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


class MetaDashboardService:
    def __init__(self, repository: Any):
        self.repository = repository

    async def overview(
        self,
        *,
        connection_id: str | list[str],
        since: date,
        until: date,
        result_action_type: str,
        account_id: str | None = None,
        use_link_clicks: bool = False,
        expected_accounts: list[dict[str, str]] | None = None,
        sync_accounts: dict[str, dict[str, Any]] | None = None,
        objective: str | None = None,
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
        all_pairs = [(_fact_of(row), row) for row in rows]

        # The objective switcher always describes the whole window so the user can
        # see where the money actually is before choosing a result view.
        objectives_summary = self._objectives_summary(all_pairs)

        if objective:
            result_action_type = OBJECTIVE_RESULT_ACTION.get(objective, result_action_type)
            pairs = [pair for pair in all_pairs if _row_objective(pair[1]) == objective]
        else:
            pairs = all_pairs
        facts = [fact for fact, _ in pairs]

        view = aggregate_dashboard_facts(
            facts,
            result_action_type=result_action_type,
            use_link_clicks=use_link_clicks,
        )

        previous_days = (until - since).days + 1
        previous_until = since - timedelta(days=1)
        previous_since = previous_until - timedelta(days=previous_days - 1)
        previous_rows = await self.repository.list_daily_facts(
            connection_id=connection_id,
            account_id=normalized_account_id,
            since=previous_since,
            until=previous_until,
            level="adset",
        )
        previous_pairs = [(_fact_of(row), row) for row in previous_rows]
        if objective:
            previous_pairs = [
                pair for pair in previous_pairs if _row_objective(pair[1]) == objective
            ]
        previous_facts = [fact for fact, _ in previous_pairs]
        previous_view = aggregate_dashboard_facts(
            previous_facts,
            result_action_type=result_action_type,
            use_link_clicks=use_link_clicks,
        )

        def kpis_of(items: list[DailyFact]) -> dict[str, Any]:
            return aggregate_dashboard_facts(
                items,
                result_action_type=result_action_type,
                use_link_clicks=use_link_clicks,
            )["kpis"]

        # Average order value only exists for a revenue objective.
        view["aov"] = _ratio(view["kpis"]["conversion_value"], view["kpis"]["conversions"])
        view["funnel"] = (
            self._funnel(facts) if objective == OBJECTIVE_SALES else []
        )
        view["scope"] = {
            "objective": objective,
            "objective_label": OBJECTIVE_LABELS.get(objective or "", "全部目标"),
            "result_action_type": result_action_type,
            "supported": objective in SUPPORTED_OBJECTIVES,
            "mixed_objectives": objective is None and len(objectives_summary) > 1,
            "funnel_available": objective == OBJECTIVE_SALES,
        }
        view["objectives"] = objectives_summary
        view["previous"] = {
            "window": {"since": previous_since.isoformat(), "until": previous_until.isoformat()},
            "kpis": previous_view["kpis"],
            "aov": _ratio(
                previous_view["kpis"]["conversion_value"], previous_view["kpis"]["conversions"]
            ),
        }

        previous_by_account = self._grouped_kpis(
            previous_pairs, lambda fact, row: fact.account_id, kpis_of
        )
        previous_by_campaign = self._grouped_kpis(
            previous_pairs, lambda fact, row: getattr(row, "parent_entity_id", None), kpis_of
        )
        previous_by_adset = self._grouped_kpis(
            previous_pairs, lambda fact, row: getattr(row, "entity_id", None), kpis_of
        )

        grouped_accounts: dict[str, list[DailyFact]] = {}
        account_names: dict[str, str] = {}
        for fact, row in pairs:
            if fact.account_id:
                grouped_accounts.setdefault(fact.account_id, []).append(fact)
                account_names[fact.account_id] = getattr(row, "account_name", None) or fact.account_id
        expected = expected_accounts or [
            {"account_id": current_id, "account_name": account_names.get(current_id, current_id)}
            for current_id in sorted(grouped_accounts)
        ]
        account_views = []
        for account in expected:
            current_id = normalize_account_id(account["account_id"])
            account_facts = grouped_accounts.get(current_id, [])
            sync = (sync_accounts or {}).get(current_id, {})
            data_status = (
                "with_delivery"
                if account_facts and any(fact.spend not in (None, 0) for fact in account_facts)
                else "no_delivery" if account_facts else "no_facts"
            )
            account_views.append({
                "account_id": current_id,
                "account_name": account.get("account_name") or current_id,
                "sync_status": sync.get("status", "never_synced"),
                "data_status": data_status,
                "last_synced_at": sync.get("finished_at"),
                "error_code": sync.get("error_code"),
                "error_message": sync.get("error_message"),
                **kpis_of(account_facts),
                "previous": previous_by_account.get(current_id),
            })
        view["accounts"] = account_views

        view["campaigns"] = self._entity_views(
            pairs,
            key=lambda fact, row: getattr(row, "parent_entity_id", None),
            meta=lambda fact, row: {
                "campaign_id": getattr(row, "parent_entity_id", None) or "",
                "campaign_name": getattr(row, "parent_entity_name", None)
                or getattr(row, "parent_entity_id", None)
                or "",
                "account_id": fact.account_id,
                "account_name": getattr(row, "account_name", None) or fact.account_id,
                "objective": _row_objective(row),
            },
            kpis_of=kpis_of,
            previous_map=previous_by_campaign,
        )
        view["adsets"] = self._entity_views(
            pairs,
            key=lambda fact, row: getattr(row, "entity_id", None),
            meta=lambda fact, row: {
                "adset_id": getattr(row, "entity_id", None) or "",
                "adset_name": getattr(row, "entity_name", None)
                or getattr(row, "entity_id", None)
                or "",
                "campaign_id": getattr(row, "parent_entity_id", None),
                "campaign_name": getattr(row, "parent_entity_name", None),
                "account_id": fact.account_id,
                "account_name": getattr(row, "account_name", None) or fact.account_id,
                "objective": _row_objective(row),
                "optimization_goal": getattr(row, "optimization_goal", None),
            },
            kpis_of=kpis_of,
            previous_map=previous_by_adset,
        )

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

    def _objectives_summary(
        self, pairs: list[tuple[DailyFact, Any]]
    ) -> list[dict[str, Any]]:
        """Describe spend distribution per objective for the view switcher."""
        buckets: dict[str | None, dict[str, Any]] = {}
        total_spend = _sum_optional(fact.spend for fact, _ in pairs) or Decimal("0")
        for fact, row in pairs:
            key = _row_objective(row)
            bucket = buckets.setdefault(
                key,
                {"spend": None, "accounts": set(), "adsets": set()},
            )
            bucket["spend"] = _sum_optional([bucket["spend"], fact.spend])
            if fact.account_id:
                bucket["accounts"].add(fact.account_id)
            entity_id = getattr(row, "entity_id", None)
            if entity_id:
                bucket["adsets"].add(entity_id)
        summary = [
            {
                "objective": key,
                "label": OBJECTIVE_LABELS.get(key or "", key or "未标注目标"),
                "spend": bucket["spend"],
                "spend_share": _ratio(bucket["spend"], total_spend),
                "accounts": len(bucket["accounts"]),
                "adsets": len(bucket["adsets"]),
                "supported": key in SUPPORTED_OBJECTIVES,
                "result_action_type": OBJECTIVE_RESULT_ACTION.get(key or ""),
            }
            for key, bucket in buckets.items()
        ]
        summary.sort(key=lambda item: (item["spend"] is None, -(item["spend"] or 0)))
        return summary

    def _funnel(self, facts: list[DailyFact]) -> list[dict[str, Any]]:
        """Sales funnel using one canonical action per step."""
        values = [
            _sum_optional((fact.actions or {}).get(action) for fact in facts)
            for action, _ in SALES_FUNNEL_STEPS
        ]
        top = values[0] if values else None
        steps = []
        for index, (action, label) in enumerate(SALES_FUNNEL_STEPS):
            value = values[index]
            previous_value = values[index - 1] if index else None
            steps.append({
                "key": action,
                "label": label,
                "value": value,
                "rate_from_previous": _ratio(value, previous_value) if index else None,
                "rate_from_top": _ratio(value, top),
            })
        return steps

    def _grouped_kpis(
        self,
        pairs: list[tuple[DailyFact, Any]],
        key: Callable[[DailyFact, Any], str | None],
        kpis_of: Callable[[list[DailyFact]], dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        grouped: dict[str, list[DailyFact]] = {}
        for fact, row in pairs:
            current_key = key(fact, row)
            if current_key:
                grouped.setdefault(current_key, []).append(fact)
        return {current_key: kpis_of(items) for current_key, items in grouped.items()}

    def _entity_views(
        self,
        pairs: list[tuple[DailyFact, Any]],
        *,
        key: Callable[[DailyFact, Any], str | None],
        meta: Callable[[DailyFact, Any], dict[str, Any]],
        kpis_of: Callable[[list[DailyFact]], dict[str, Any]],
        previous_map: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[DailyFact]] = {}
        entity_meta: dict[str, dict[str, Any]] = {}
        for fact, row in pairs:
            current_key = key(fact, row)
            if not current_key:
                continue
            grouped.setdefault(current_key, []).append(fact)
            entity_meta[current_key] = meta(fact, row)
        views = [
            {
                **entity_meta[current_key],
                **kpis_of(items),
                "previous": previous_map.get(current_key),
            }
            for current_key, items in grouped.items()
        ]
        views.sort(key=lambda item: (item["spend"] is None, -(item["spend"] or 0)))
        return views
