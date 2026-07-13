import asyncio

from app.services.agent_evidence_service import AgentEvidenceService


class CampaignRepo:
    def __init__(self, campaigns):
        self.campaigns = campaigns

    async def list_by_project(self, project_id, status=None, limit=20):
        return [item for item in self.campaigns if item["project_id"] == project_id][:limit]


class AdSetEvidenceRepo:
    def __init__(self, payload):
        self.payload = payload
        self.requests = []

    async def get_campaign_breakdown(self, campaign_id, hours=168):
        self.requests.append((campaign_id, hours))
        return self.payload


class MetricRepo:
    def __init__(self, series):
        self.series = series
        self.requested_hours = []

    async def get_timeseries(self, campaign_id, hours=24):
        self.requested_hours.append((campaign_id, hours))
        return self.series.get(campaign_id, [])

    async def get_latest(self, campaign_id):
        raise AssertionError("evidence must not use an out-of-window latest snapshot")


def campaign(campaign_id="c1", project_id="p1"):
    return {
        "id": campaign_id,
        "project_id": project_id,
        "name": campaign_id,
        "platform": "Meta",
        "status": "running",
        "budget": 100,
    }


def metric(timestamp, impressions, clicks, conversions, installs, spend, revenue):
    return {
        "timestamp": timestamp,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "installs": installs,
        "spend": spend,
        "revenue": revenue,
        "ctr": clicks / impressions if impressions else 0,
        "cvr": conversions / clicks if clicks else 0,
        "cpa": spend / conversions if conversions else 0,
        "cpi": spend / installs if installs else 0,
        "roi": (revenue - spend) / spend if spend else 0,
    }


def test_campaign_evidence_exposes_latest_change_and_window():
    repo = MetricRepo({
        "c1": [
            metric("2026-07-12T00:00:00", 100, 10, 2, 1, 20, 30),
            metric("2026-07-13T00:00:00", 180, 18, 5, 3, 50, 90),
        ]
    })
    result = asyncio.run(AgentEvidenceService(CampaignRepo([]), repo).campaign_performance(campaign(), 168))

    assert result["data_available"] is True
    assert result["sample_count"] == 2
    assert result["latest"]["revenue"] == 90
    assert result["change"]["conversions"] == 3
    assert result["window"]["timezone"] == "UTC"
    assert repo.requested_hours == [("c1", 168)]


def test_campaign_evidence_includes_ad_set_and_material_breakdown():
    metric_repo = MetricRepo({
        "c1": [metric("2026-07-13T00:00:00", 100, 10, 2, 1, 20, 30)]
    })
    breakdown_repo = AdSetEvidenceRepo({
        "ad_sets": [{"id": "a1", "name": "Broad", "data_available": True}],
        "materials": [{"material_id": "m1", "roi": -0.2, "frequency": 5.1}],
    })
    result = asyncio.run(
        AgentEvidenceService(CampaignRepo([]), metric_repo, breakdown_repo).campaign_performance(
            campaign(), 168
        )
    )

    assert result["ad_set_breakdown"][0]["name"] == "Broad"
    assert result["material_breakdown"][0]["frequency"] == 5.1
    assert breakdown_repo.requests == [("c1", 168)]


def test_no_data_is_not_reported_as_zero_performance():
    result = asyncio.run(
        AgentEvidenceService(CampaignRepo([]), MetricRepo({})).campaign_performance(campaign(), 168)
    )

    assert result["data_available"] is False
    assert result["latest"] is None
    assert result["change"] is None
    assert result["ad_set_breakdown"] == []
    assert "zero performance must not be inferred" in result["limitations"][0]


def test_campaign_without_metrics_still_exposes_existing_ad_sets():
    breakdown_repo = AdSetEvidenceRepo({
        "ad_sets": [{"id": "a1", "name": "Pre-launch", "data_available": False}],
        "materials": [],
    })
    result = asyncio.run(
        AgentEvidenceService(CampaignRepo([]), MetricRepo({}), breakdown_repo).campaign_performance(
            campaign(), 168
        )
    )

    assert result["data_available"] is False
    assert result["ad_set_breakdown"] == [
        {"id": "a1", "name": "Pre-launch", "data_available": False}
    ]
    assert breakdown_repo.requests == [("c1", 168)]


def test_project_aggregation_recalculates_rates_from_totals():
    campaigns = [campaign("c1"), campaign("c2"), campaign("c3")]
    repo = MetricRepo({
        "c1": [metric("2026-07-13T00:00:00", 100, 10, 2, 1, 20, 40)],
        "c2": [metric("2026-07-13T00:00:00", 300, 60, 3, 9, 80, 120)],
    })
    result = asyncio.run(
        AgentEvidenceService(CampaignRepo(campaigns), repo).project_performance(
            {"id": "p1", "name": "项目"}, 72
        )
    )

    assert result["campaign_count"] == 3
    assert result["campaigns_with_data"] == 2
    assert result["campaigns_without_data"] == 1
    assert result["totals"]["impressions"] == 400
    assert result["totals"]["ctr"] == 70 / 400
    assert result["totals"]["cpa"] == 100 / 5
    assert result["totals"]["roi"] == 0.6
    assert result["ranking_by_roi"] == ["c1", "c2"]
    assert repo.requested_hours == [("c1", 72), ("c2", 72), ("c3", 72)]


def test_requested_window_is_clamped_to_ninety_days():
    repo = MetricRepo({})
    result = asyncio.run(
        AgentEvidenceService(CampaignRepo([]), repo).campaign_performance(campaign(), 999999)
    )

    assert result["window"]["hours"] == 2160
    assert repo.requested_hours == [("c1", 2160)]
