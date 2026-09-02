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


def _row(**overrides):
    base = dict(
        metric_date=date(2026, 8, 10), spend=Decimal("10"), impressions=100,
        clicks=10, inline_link_clicks=8, actions_json=[], action_values_json=None,
        status="accessible_with_rows", account_id="1", account_name="Acc 1",
        account_currency="USD", account_timezone="UTC", objective="OUTCOME_SALES",
        optimization_goal="OFFSITE_CONVERSIONS", entity_id="as1", entity_name="AdSet 1",
        parent_entity_id="c1", parent_entity_name="Campaign 1",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_objective_scope_isolates_sales_spend_from_lead_results():
    """Lead CPL must never consume sales spend."""
    repository = FakeRepository([
        _row(spend=Decimal("900"), objective="OUTCOME_SALES", entity_id="as-sales",
             actions_json=[{"action_type": "purchase", "value": "9"}],
             action_values_json=[{"action_type": "purchase", "value": "1800"}]),
        _row(spend=Decimal("100"), objective="OUTCOME_LEADS", entity_id="as-leads",
             actions_json=[{"action_type": "lead", "value": "50"}]),
    ])

    leads = asyncio.run(MetaDashboardService(repository).overview(
        connection_id="c1", since=date(2026, 8, 10), until=date(2026, 8, 10),
        result_action_type="lead", objective="OUTCOME_LEADS",
    ))

    assert leads["kpis"]["spend"] == Decimal("100")
    assert leads["kpis"]["conversions"] == 50
    assert leads["kpis"]["result_cost"] == Decimal("2")
    assert leads["scope"]["objective"] == "OUTCOME_LEADS"
    assert leads["scope"]["funnel_available"] is False
    assert leads["funnel"] == []


def test_sales_objective_exposes_revenue_roas_aov_and_deduplicated_funnel():
    repository = FakeRepository([
        _row(
            spend=Decimal("500"),
            actions_json=[
                {"action_type": "view_content", "value": "1000"},
                {"action_type": "omni_view_content", "value": "1000"},
                {"action_type": "offsite_conversion.fb_pixel_view_content", "value": "1000"},
                {"action_type": "add_to_cart", "value": "200"},
                {"action_type": "initiate_checkout", "value": "100"},
                {"action_type": "purchase", "value": "25"},
            ],
            action_values_json=[{"action_type": "purchase", "value": "1500"}],
        ),
    ])

    view = asyncio.run(MetaDashboardService(repository).overview(
        connection_id="c1", since=date(2026, 8, 10), until=date(2026, 8, 10),
        result_action_type="lead", objective="OUTCOME_SALES",
    ))

    assert view["scope"]["result_action_type"] == "purchase"
    assert view["kpis"]["conversions"] == 25
    assert view["kpis"]["conversion_value"] == Decimal("1500")
    assert view["kpis"]["roas"] == Decimal("3")
    assert view["aov"] == Decimal("60")
    steps = {step["key"]: step["value"] for step in view["funnel"]}
    assert steps == {"view_content": 1000, "add_to_cart": 200, "initiate_checkout": 100, "purchase": 25}
    add_to_cart = next(step for step in view["funnel"] if step["key"] == "add_to_cart")
    assert add_to_cart["rate_from_previous"] == Decimal("0.2")


def test_objectives_summary_reports_spend_share_for_the_switcher():
    repository = FakeRepository([
        _row(spend=Decimal("960"), objective="OUTCOME_SALES", entity_id="as-sales"),
        _row(spend=Decimal("40"), objective="OUTCOME_ENGAGEMENT", entity_id="as-eng"),
    ])

    view = asyncio.run(MetaDashboardService(repository).overview(
        connection_id="c1", since=date(2026, 8, 10), until=date(2026, 8, 10),
        result_action_type="lead",
    ))

    summary = {item["objective"]: item for item in view["objectives"]}
    assert summary["OUTCOME_SALES"]["spend"] == Decimal("960")
    assert summary["OUTCOME_SALES"]["spend_share"] == Decimal("0.96")
    assert summary["OUTCOME_SALES"]["supported"] is True
    assert summary["OUTCOME_ENGAGEMENT"]["supported"] is False
    assert view["objectives"][0]["objective"] == "OUTCOME_SALES"


def test_campaign_layer_groups_adsets_and_carries_previous_window():
    repository = FakeRepository([
        _row(entity_id="as1", parent_entity_id="c1", parent_entity_name="Campaign 1", spend=Decimal("30")),
        _row(entity_id="as2", parent_entity_id="c1", parent_entity_name="Campaign 1", spend=Decimal("20")),
        _row(entity_id="as3", parent_entity_id="c2", parent_entity_name="Campaign 2", spend=Decimal("5")),
    ])

    view = asyncio.run(MetaDashboardService(repository).overview(
        connection_id="c1", since=date(2026, 8, 10), until=date(2026, 8, 10),
        result_action_type="lead", objective="OUTCOME_SALES",
    ))

    campaigns = {item["campaign_id"]: item for item in view["campaigns"]}
    assert campaigns["c1"]["spend"] == Decimal("50")
    assert campaigns["c1"]["campaign_name"] == "Campaign 1"
    assert view["campaigns"][0]["campaign_id"] == "c1"
    assert len(view["adsets"]) == 3
    assert view["adsets"][0]["campaign_name"] == "Campaign 1"
    assert campaigns["c1"]["previous"] is not None
