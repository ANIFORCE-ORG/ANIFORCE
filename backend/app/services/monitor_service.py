from app.repositories.protocols import MetricRepository


class MonitorService:
    """监控业务逻辑"""

    def __init__(self, metric_repo: MetricRepository):
        self._repo = metric_repo

    async def get_metrics(self, campaign_id: str) -> dict:
        metrics = await self._repo.get_latest(campaign_id)
        return metrics or {}

    async def get_timeseries(self, campaign_id: str, hours: int = 24) -> list[dict]:
        return await self._repo.get_timeseries(campaign_id, hours)
