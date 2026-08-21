import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.meta_dashboard_service import MetaDashboardService


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows
        self.query = None

    async def list_daily_facts(self, **kwargs):
        self.query = kwargs
        return self.rows


def test_overview_reads_adset_facts_and_exposes_metric_definition():
    repository = FakeRepository([
        SimpleNamespace(
            metric_date=date(2026, 8, 10), spend=Decimal("20"), impressions=1000,
            clicks=40, inline_link_clicks=20,
            actions_json=[{"action_type": "lead", "value": "4"}, {"action_type": "onsite_conversion.lead_grouped", "value": "9"}],
            action_values_json=None, status="accessible_with_rows", account_id="123",
            account_currency="USD", account_timezone="America/Los_Angeles",
        )
    ])

    view = asyncio.run(MetaDashboardService(repository).overview(
        connection_id="c1", account_id="act_123",
        since=date(2026, 8, 10), until=date(2026, 8, 16),
        result_action_type="lead", use_link_clicks=True,
    ))

    assert repository.query["level"] == "adset"
    assert repository.query["account_id"] == "123"
    assert view["kpis"]["conversions"] == 4
    assert view["kpis"]["clicks"] == 20
    assert view["kpis"]["result_cost"] == Decimal("5")
    assert view["metric_definition"]["result_cost_label"] == "CPL"
    assert view["window"]["currency"] == "USD"


def test_overview_marks_mixed_currency_instead_of_false_conversion():
    base = dict(
        metric_date=date(2026, 8, 10), spend=Decimal("10"), impressions=100,
        clicks=10, inline_link_clicks=5, actions_json=[], action_values_json=None,
        status="accessible_with_rows", account_timezone="UTC",
    )
    repository = FakeRepository([
        SimpleNamespace(**base, account_id="1", account_currency="USD"),
        SimpleNamespace(**base, account_id="2", account_currency="EUR"),
    ])

    view = asyncio.run(MetaDashboardService(repository).overview(
        connection_id="c1", since=date(2026, 8, 10), until=date(2026, 8, 10),
        result_action_type="lead",
    ))

    assert view["window"]["currency"] is None
    assert view["window"]["mixed_currency"] is True
