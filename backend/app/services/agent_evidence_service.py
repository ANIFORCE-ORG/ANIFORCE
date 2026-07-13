"""Build evidence payloads for Agent campaign diagnosis and project review."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.repositories.protocols import CampaignRepository, MetricRepository


_METRIC_FIELDS = (
    "impressions",
    "clicks",
    "conversions",
    "installs",
    "spend",
    "revenue",
    "ctr",
    "cvr",
    "cpa",
    "cpi",
    "roi",
)


class AgentEvidenceService:
    def __init__(self, campaign_repo: CampaignRepository, metric_repo: MetricRepository) -> None:
        self.campaign_repo = campaign_repo
        self.metric_repo = metric_repo

    async def campaign_performance(self, campaign: dict, hours: int) -> dict:
        window_hours = self._window(hours)
        series = await self.metric_repo.get_timeseries(campaign["id"], window_hours)
        latest = series[-1] if series else None
        if not latest:
            return self._empty_payload("campaign", campaign, window_hours)
        first = series[0] if series else latest
        return {
            "scope": "campaign",
            "campaign": self._campaign_identity(campaign),
            "window": self._window_payload(window_hours),
            "data_available": True,
            "sample_count": len(series) or 1,
            "latest": self._metrics(latest),
            "change": {
                field: self._number(latest.get(field)) - self._number(first.get(field))
                for field in _METRIC_FIELDS
            },
            "series": [self._metrics(item, include_timestamp=True) for item in series],
            "data_freshness": {"last_updated_at": latest.get("timestamp")},
        }

    async def project_performance(self, project: dict, hours: int, limit: int = 100) -> dict:
        window_hours = self._window(hours)
        campaigns = await self.campaign_repo.list_by_project(project["id"], limit=limit)
        rows = []
        for campaign in campaigns:
            series = await self.metric_repo.get_timeseries(campaign["id"], window_hours)
            latest = series[-1] if series else None
            row = {
                "campaign": self._campaign_identity(campaign),
                "data_available": latest is not None,
                "latest": self._metrics(latest) if latest else None,
                "last_updated_at": latest.get("timestamp") if latest else None,
            }
            rows.append(row)
        available = [row for row in rows if row["data_available"]]
        totals = self._aggregate([row["latest"] for row in available]) if available else None
        ranked = sorted(
            available,
            key=lambda row: self._number((row["latest"] or {}).get("roi")),
            reverse=True,
        )
        return {
            "scope": "project",
            "project": {"id": project["id"], "name": project.get("name")},
            "window": self._window_payload(window_hours),
            "data_available": bool(available),
            "campaign_count": len(campaigns),
            "campaigns_with_data": len(available),
            "campaigns_without_data": len(campaigns) - len(available),
            "totals": totals,
            "campaigns": rows,
            "ranking_by_roi": [row["campaign"]["id"] for row in ranked],
        }

    @staticmethod
    def _window(hours: int) -> int:
        return max(1, min(int(hours), 24 * 90))

    @staticmethod
    def _window_payload(hours: int) -> dict:
        return {
            "hours": hours,
            "timezone": "UTC",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "semantics": "snapshots recorded within the requested UTC lookback window; latest is the last snapshot in that window",
        }

    def _empty_payload(self, scope: str, campaign: dict, hours: int) -> dict:
        return {
            "scope": scope,
            "campaign": self._campaign_identity(campaign),
            "window": self._window_payload(hours),
            "data_available": False,
            "sample_count": 0,
            "latest": None,
            "change": None,
            "series": [],
            "data_freshness": {"last_updated_at": None},
            "limitations": ["No campaign metrics are available; zero performance must not be inferred."],
        }

    @staticmethod
    def _campaign_identity(campaign: dict) -> dict:
        return {
            "id": campaign["id"],
            "name": campaign.get("name"),
            "project_id": campaign.get("project_id"),
            "platform": campaign.get("platform"),
            "status": campaign.get("status"),
            "budget": campaign.get("budget"),
        }

    def _metrics(self, metric: dict[str, Any], include_timestamp: bool = False) -> dict:
        result = {field: self._number(metric.get(field)) for field in _METRIC_FIELDS}
        if include_timestamp:
            result["timestamp"] = metric.get("timestamp")
        return result

    def _aggregate(self, metrics: list[dict]) -> dict:
        totals = {
            field: sum(self._number(metric.get(field)) for metric in metrics)
            for field in ("impressions", "clicks", "conversions", "installs", "spend", "revenue")
        }
        totals.update({
            "ctr": self._ratio(totals["clicks"], totals["impressions"]),
            "cvr": self._ratio(totals["conversions"], totals["clicks"]),
            "cpa": self._ratio(totals["spend"], totals["conversions"]),
            "cpi": self._ratio(totals["spend"], totals["installs"]),
            "roi": self._ratio(totals["revenue"] - totals["spend"], totals["spend"]),
        })
        return totals

    @staticmethod
    def _number(value: Any) -> float:
        return float(value or 0)

    @staticmethod
    def _ratio(numerator: float, denominator: float) -> float | None:
        return numerator / denominator if denominator else None
