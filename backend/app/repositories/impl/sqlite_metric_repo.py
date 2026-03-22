"""监控指标 Repository SQLite 实现"""
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Metric


class SqliteMetricRepository:
    """监控指标数据访问 SQLite 实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_dict(self, metric: Metric) -> dict:
        """将 ORM 对象转换为字典"""
        return {
            "id": metric.id,
            "campaign_id": metric.campaign_id,
            "timestamp": metric.timestamp.isoformat(),
            "platform": metric.platform,
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
    
    async def get_latest(self, campaign_id: str) -> dict | None:
        """获取广告投放的最新监控数据"""
        result = await self.session.execute(
            select(Metric)
            .where(Metric.campaign_id == campaign_id)
            .order_by(Metric.timestamp.desc())
            .limit(1)
        )
        metric = result.scalar_one_or_none()
        if not metric:
            return None
        
        return self._to_dict(metric)
    
    async def get_timeseries(self, campaign_id: str, hours: int = 24) -> list[dict]:
        """获取广告投放的时间序列监控数据"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        result = await self.session.execute(
            select(Metric)
            .where(Metric.campaign_id == campaign_id)
            .where(Metric.timestamp >= start_time)
            .order_by(Metric.timestamp.asc())
        )
        metrics = result.scalars().all()
        
        return [self._to_dict(m) for m in metrics]
