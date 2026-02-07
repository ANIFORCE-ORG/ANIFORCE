import random
from datetime import datetime, timedelta


class MockMetricRepository:
    async def get_latest(self, _campaign_id: str) -> dict | None:
        return {
            "impressions": 125000, "clicks": 3750, "conversions": 450,
            "spend": 4500.0, "revenue": 11250.0,
            "ctr": 3.0, "cvr": 12.0, "cpa": 10.0, "roi": 2.5,
        }

    async def get_timeseries(self, _campaign_id: str, hours: int = 24) -> list[dict]:
        now = datetime.utcnow()
        return [
            {
                "timestamp": (now - timedelta(hours=hours - i)).isoformat(),
                "impressions": 5000 + random.randint(-500, 500),
                "clicks": 150 + random.randint(-20, 20),
                "conversions": 18 + random.randint(-3, 3),
                "spend": 180.0 + random.uniform(-20, 20),
                "revenue": 450.0 + random.uniform(-50, 50),
            }
            for i in range(hours)
        ]
