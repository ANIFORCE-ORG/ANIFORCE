from app.repositories.protocols import CampaignRepository


class CampaignService:
    """投放业务逻辑"""

    def __init__(self, campaign_repo: CampaignRepository):
        self._repo = campaign_repo

    async def create_plan(self, user_id: str, config: dict) -> dict:
        campaign_id = await self._repo.create(user_id, config)
        campaign = await self._repo.get(campaign_id)
        return {
            "campaign_id": campaign_id,
            "plan": campaign.get("plan", {}) if campaign else {},
        }

    async def get_campaign(self, campaign_id: str) -> dict:
        campaign = await self._repo.get(campaign_id)
        if not campaign:
            return {"id": campaign_id, "status": "not_found", "config": {}}
        return {
            "id": campaign["id"],
            "status": campaign["status"],
            "config": campaign.get("config", {}),
        }
