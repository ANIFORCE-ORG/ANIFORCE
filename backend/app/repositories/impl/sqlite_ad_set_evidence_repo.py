"""Read-only ad set and material evidence queries."""

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdSet, AdSetMetric, Material, MaterialPerformance


class SqliteAdSetEvidenceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_campaign_breakdown(self, campaign_id: str, hours: int = 168) -> dict:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        ad_set_result = await self.session.execute(
            select(AdSet).where(AdSet.campaign_id == campaign_id).order_by(AdSet.name.asc())
        )
        ad_sets = list(ad_set_result.scalars().all())
        if not ad_sets:
            return {"ad_sets": [], "materials": []}

        ad_set_ids = [item.id for item in ad_sets]
        metric_result = await self.session.execute(
            select(AdSetMetric)
            .where(AdSetMetric.ad_set_id.in_(ad_set_ids), AdSetMetric.timestamp >= start_time)
            .order_by(AdSetMetric.ad_set_id.asc(), AdSetMetric.timestamp.asc())
        )
        metric_groups: dict[str, list[AdSetMetric]] = defaultdict(list)
        for metric in metric_result.scalars().all():
            metric_groups[metric.ad_set_id].append(metric)

        material_result = await self.session.execute(
            select(MaterialPerformance, Material.name)
            .join(Material, Material.id == MaterialPerformance.material_id)
            .where(
                MaterialPerformance.ad_set_id.in_(ad_set_ids),
                MaterialPerformance.timestamp >= start_time,
            )
            .order_by(
                MaterialPerformance.ad_set_id.asc(),
                MaterialPerformance.material_id.asc(),
                MaterialPerformance.timestamp.asc(),
            )
        )
        latest_materials: dict[tuple[str, str], tuple[MaterialPerformance, str | None]] = {}
        for metric, material_name in material_result.all():
            latest_materials[(metric.ad_set_id, metric.material_id)] = (metric, material_name)

        return {
            "ad_sets": [self._ad_set(item, metric_groups.get(item.id, [])) for item in ad_sets],
            "materials": [
                self._material(metric, material_name)
                for metric, material_name in latest_materials.values()
            ],
        }

    def _ad_set(self, ad_set: AdSet, series: list[AdSetMetric]) -> dict:
        latest = series[-1] if series else None
        first = series[0] if series else None
        return {
            "id": ad_set.id,
            "name": ad_set.name,
            "status": ad_set.status.value if hasattr(ad_set.status, "value") else str(ad_set.status),
            "daily_budget": ad_set.daily_budget,
            "spent": ad_set.spent,
            "audience": ad_set.audience,
            "placements": ad_set.placements,
            "optimization_goal": ad_set.optimization_goal,
            "bid_strategy": ad_set.bid_strategy,
            "data_available": latest is not None,
            "sample_count": len(series),
            "latest": self._metrics(latest) if latest else None,
            "change": self._change(first, latest) if first and latest else None,
        }

    @staticmethod
    def _material(metric: MaterialPerformance, material_name: str | None) -> dict:
        return {
            "material_id": metric.material_id,
            "material_name": material_name,
            "ad_set_id": metric.ad_set_id,
            "timestamp": metric.timestamp.isoformat(),
            "impressions": metric.impressions,
            "clicks": metric.clicks,
            "conversions": metric.conversions,
            "installs": metric.installs,
            "spend": metric.spend,
            "revenue": metric.revenue,
            "ctr": metric.ctr,
            "cvr": metric.cvr,
            "cpi": metric.cpi,
            "roi": metric.roi,
            "frequency": metric.frequency,
        }

    @staticmethod
    def _metrics(metric: AdSetMetric) -> dict:
        return {
            "timestamp": metric.timestamp.isoformat(),
            "impressions": metric.impressions,
            "clicks": metric.clicks,
            "conversions": metric.conversions,
            "installs": metric.installs,
            "spend": metric.spend,
            "revenue": metric.revenue,
            "ctr": metric.ctr,
            "cvr": metric.cvr,
            "cpa": metric.cpa,
            "cpi": metric.cpi,
            "roi": metric.roi,
        }

    def _change(self, first: AdSetMetric, latest: AdSetMetric) -> dict:
        first_metrics = self._metrics(first)
        latest_metrics = self._metrics(latest)
        return {
            key: latest_metrics[key] - first_metrics[key]
            for key in latest_metrics
            if key != "timestamp"
        }
