import asyncio
import uuid
from app.config.settings import get_settings


class MockCampaignRepository:
    def __init__(self):
        self._campaigns: dict[str, dict] = {}

    async def create(self, user_id: str, config: dict) -> str:
        settings = get_settings()
        await asyncio.sleep(settings.DEMO_DELAY_CAMPAIGN)
        campaign_id = str(uuid.uuid4())
        self._campaigns[campaign_id] = {
            "id": campaign_id, "user_id": user_id,
            "config": config, "status": "active",
            "plan": {
                "platforms": [
                    {"name": "Meta Ads", "budget": config.get("budget", 10000) * 0.6, "strategy": "Nobid + AEO"},
                    {"name": "Google Ads", "budget": config.get("budget", 10000) * 0.4, "strategy": "tCPA"},
                ],
                "estimated_roi": 2.5,
            },
        }
        return campaign_id

    async def get(self, campaign_id: str) -> dict | None:
        return self._campaigns.get(campaign_id)

    async def update_status(self, campaign_id: str, status: str) -> None:
        if campaign_id in self._campaigns:
            self._campaigns[campaign_id]["status"] = status

    async def list_by_user(self, user_id: str, limit: int = 20) -> list[dict]:
        return [c for c in self._campaigns.values() if c["user_id"] == user_id][:limit]
