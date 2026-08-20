"""Dashboard metric aggregation over normalized Meta daily facts."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable


@dataclass(frozen=True)
class DailyFact:
    metric_date: str
    spend: Decimal | None = None
    impressions: int | None = None
    clicks: int | None = None
    inline_link_clicks: int | None = None
    actions: dict[str, int] | None = None
    action_values: dict[str, Decimal] | None = None
    status: str = "accessible_with_rows"
    account_id: str | None = None
    platform: str = "Meta"


def _sum_optional(values: Iterable[int | Decimal | None]) -> int | Decimal | None:
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def _decimal(value: int | Decimal | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _ratio(numerator: int | Decimal | None, denominator: int | Decimal | None) -> Decimal | None:
    if numerator is None or denominator in (None, 0):
        return None
    return _decimal(numerator) / _decimal(denominator)


def _result_type(action_type: str | None) -> str | None:
    if action_type == "lead":
        return "lead"
    if action_type == "mobile_app_install":
        return "install"
    if action_type == "purchase":
        return "purchase"
    return action_type


def aggregate_dashboard_facts(
    facts: Iterable[DailyFact],
    *,
    result_action_type: str,
    use_link_clicks: bool = False,
) -> dict[str, Any]:
    """Aggregate daily facts without treating missing values as zero."""
    rows = list(facts)
    grouped: dict[str, list[DailyFact]] = defaultdict(list)
    for fact in rows:
        grouped[fact.metric_date].append(fact)

    def aggregate(items: Iterable[DailyFact]) -> dict[str, Any]:
        items = list(items)
        spend = _sum_optional(f.spend for f in items)
        impressions = _sum_optional(f.impressions for f in items)
        clicks = _sum_optional(
            (f.inline_link_clicks if use_link_clicks else f.clicks) for f in items
        )
        conversions = _sum_optional(
            (f.actions or {}).get(result_action_type) for f in items
        )
        value = _sum_optional(
            (f.action_values or {}).get(result_action_type) for f in items
        )
        return {
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "conversion_value": value,
            "ctr": _ratio(clicks, impressions),
            "result_cost": _ratio(spend, conversions),
            "roas": _ratio(value, spend),
        }

    total = aggregate(rows)
    trend = [
        {"date": date, **aggregate(grouped[date])}
        for date in sorted(grouped)
    ]
    statuses = {fact.status for fact in rows}
    if not rows:
        data_status = "accessible_with_no_rows"
    elif statuses == {"accessible_with_zero_delivery"}:
        data_status = "accessible_with_zero_delivery"
    elif any(status in {"permission_denied", "token_expired", "api_error"} for status in statuses):
        data_status = "partial_error"
    else:
        data_status = "accessible_with_rows"

    return {
        "metric_definition": {
            "result_type": _result_type(result_action_type),
            "result_action_type": result_action_type,
            "result_cost_label": {
                "lead": "CPL",
                "install": "CPI",
                "purchase": "CPA",
            }.get(_result_type(result_action_type), "Result cost"),
            "roas_available": total["roas"] is not None,
        },
        "kpis": total,
        "trend": trend,
        "data_quality": {"status": data_status, "row_count": len(rows)},
    }
