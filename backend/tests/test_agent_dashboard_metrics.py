from decimal import Decimal

from app.services.dashboard_metrics import DailyFact, aggregate_dashboard_facts


def test_lead_aggregation_recomputes_ratios_and_does_not_add_other_actions():
    result = aggregate_dashboard_facts(
        [
            DailyFact(
                metric_date="2026-08-10",
                spend=Decimal("10.00"),
                impressions=1000,
                clicks=100,
                actions={"lead": 2, "onsite_conversion.lead_grouped": 9},
            ),
            DailyFact(
                metric_date="2026-08-11",
                spend=Decimal("20.00"),
                impressions=1000,
                clicks=50,
                actions={"lead": 1},
            ),
        ],
        result_action_type="lead",
    )

    assert result["kpis"]["spend"] == Decimal("30.00")
    assert result["kpis"]["conversions"] == 3
    assert result["kpis"]["ctr"] == Decimal("0.075")
    assert result["kpis"]["result_cost"] == Decimal("10.00")
    assert result["metric_definition"]["result_cost_label"] == "CPL"


def test_install_uses_cpi_and_purchase_value_enables_roas():
    result = aggregate_dashboard_facts(
        [
            DailyFact(
                metric_date="2026-08-10",
                spend=Decimal("25"),
                impressions=500,
                clicks=10,
                actions={"mobile_app_install": 5},
            ),
            DailyFact(
                metric_date="2026-08-11",
                spend=Decimal("25"),
                impressions=500,
                clicks=10,
                actions={"mobile_app_install": 5},
            ),
        ],
        result_action_type="mobile_app_install",
    )

    assert result["metric_definition"]["result_type"] == "install"
    assert result["metric_definition"]["result_cost_label"] == "CPI"
    assert result["kpis"]["result_cost"] == Decimal("5")
    assert result["kpis"]["roas"] is None
    assert result["metric_definition"]["roas_available"] is False

    purchase = aggregate_dashboard_facts(
        [DailyFact(
            metric_date="2026-08-10",
            spend=Decimal("25"),
            actions={"purchase": 2},
            action_values={"purchase": Decimal("100")},
        )],
        result_action_type="purchase",
    )
    assert purchase["kpis"]["roas"] == Decimal("4")
    assert purchase["metric_definition"]["result_cost_label"] == "CPA"


def test_missing_values_are_not_converted_to_zero_and_zero_delivery_is_distinct():
    result = aggregate_dashboard_facts(
        [DailyFact(metric_date="2026-08-10", status="accessible_with_zero_delivery")],
        result_action_type="lead",
    )

    assert result["kpis"]["spend"] is None
    assert result["kpis"]["conversions"] is None
    assert result["kpis"]["ctr"] is None
    assert result["data_quality"]["status"] == "accessible_with_zero_delivery"


def test_trend_is_sorted_and_link_click_definition_is_explicit():
    result = aggregate_dashboard_facts(
        [
            DailyFact(metric_date="2026-08-11", impressions=100, clicks=10, inline_link_clicks=4),
            DailyFact(metric_date="2026-08-10", impressions=100, clicks=20, inline_link_clicks=6),
        ],
        result_action_type="lead",
        use_link_clicks=True,
    )

    assert [row["date"] for row in result["trend"]] == ["2026-08-10", "2026-08-11"]
    assert result["kpis"]["clicks"] == 10
    assert result["kpis"]["ctr"] == Decimal("0.05")
