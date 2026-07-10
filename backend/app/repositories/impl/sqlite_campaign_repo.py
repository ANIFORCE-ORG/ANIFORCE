"""广告投放 Repository SQLite 实现"""
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Campaign, Material
from app.models.campaign import CampaignStatus, Platform


class SqliteCampaignRepository:
    """广告投放数据访问 SQLite 实现"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_dict(self, campaign: Campaign) -> dict:
        """将 ORM 对象转换为字典"""
        return {
            "id": campaign.id,
            "project_id": campaign.project_id,
            "name": campaign.name,
            "description": campaign.description,
            "platform": campaign.platform.value,
            "connection_id": campaign.connection_id,
            "account_id": campaign.account_id,
            "budget": campaign.budget,
            "spent": campaign.spent,
            "status": campaign.status.value,
            "material_ids": campaign.get_material_ids(),
            "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
            "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
            # Meta Campaign 特定字段
            "objective": campaign.objective,
            "buying_type": campaign.buying_type,
            "special_ad_categories": campaign.special_ad_categories,
            "special_ad_category_country": campaign.special_ad_category_country,
            "promoted_object": campaign.promoted_object,
            "ab_test": campaign.ab_test,
            "campaign_budget_optimization": campaign.campaign_budget_optimization,
            "budget_type": campaign.budget_type,
            "budget_schedule_specs": campaign.budget_schedule_specs,
            "pacing_type": campaign.pacing_type,
            "bid_strategy": campaign.bid_strategy,
            "spend_limit": campaign.spend_limit,
            "config": json.loads(campaign.config) if campaign.config else {},
            "created_at": campaign.created_at.isoformat(),
            "updated_at": campaign.updated_at.isoformat(),
        }

    async def create(
        self, project_id: str, name: str, platform: str, budget: float, **kwargs
    ) -> dict:
        """创建广告投放"""
        from datetime import datetime

        # 处理 material_ids
        material_ids = kwargs.pop("material_ids", None)
        if material_ids and isinstance(material_ids, list):
            kwargs["material_ids"] = json.dumps(material_ids)

        # 处理 config
        config = kwargs.pop("config", None)
        if config and isinstance(config, dict):
            kwargs["config"] = json.dumps(config)

        # 处理 status
        status = kwargs.pop("status", None)
        if status and isinstance(status, str):
            kwargs["status"] = CampaignStatus(status)

        # 处理 platform
        if isinstance(platform, str):
            platform = Platform(platform)

        # 处理日期字段：将字符串转换为 date 对象
        start_date = kwargs.pop("start_date", None)
        if start_date and isinstance(start_date, str):
            try:
                kwargs["start_date"] = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
            except (ValueError, AttributeError):
                pass  # 如果转换失败，忽略该字段

        end_date = kwargs.pop("end_date", None)
        if end_date and isinstance(end_date, str):
            try:
                kwargs["end_date"] = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
            except (ValueError, AttributeError):
                pass  # 如果转换失败，忽略该字段

        campaign = Campaign(
            project_id=project_id,
            name=name,
            platform=platform,
            budget=budget,
            **kwargs
        )
        self.session.add(campaign)
        await self.session.flush()

        return self._to_dict(campaign)

    async def get_by_id(self, campaign_id: str) -> dict | None:
        """根据 ID 获取广告投放"""
        result = await self.session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            return None

        return self._to_dict(campaign)

    async def list_by_project(
        self, project_id: str, status: str | None = None, limit: int = 20
    ) -> list[dict]:
        """查询项目的广告投放列表"""
        query = select(Campaign).where(Campaign.project_id == project_id)

        if status:
            query = query.where(Campaign.status == CampaignStatus(status))

        query = query.order_by(Campaign.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        campaigns = result.scalars().all()

        return [self._to_dict(c) for c in campaigns]

    async def update(self, campaign_id: str, **kwargs) -> dict:
        """更新广告投放"""
        from datetime import datetime

        result = await self.session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # 处理 material_ids
        material_ids = kwargs.pop("material_ids", None)
        if material_ids is not None and isinstance(material_ids, list):
            kwargs["material_ids"] = json.dumps(material_ids)

        # 处理 config
        config = kwargs.pop("config", None)
        if config is not None and isinstance(config, dict):
            kwargs["config"] = json.dumps(config)

        # 处理 status
        status = kwargs.pop("status", None)
        if status is not None and isinstance(status, str):
            kwargs["status"] = CampaignStatus(status)

        # 处理 platform
        platform = kwargs.pop("platform", None)
        if platform is not None and isinstance(platform, str):
            kwargs["platform"] = Platform(platform)

        # 处理日期字段：将字符串转换为 date 对象
        start_date = kwargs.pop("start_date", None)
        if start_date is not None and isinstance(start_date, str):
            try:
                kwargs["start_date"] = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
            except (ValueError, AttributeError):
                pass  # 如果转换失败，忽略该字段

        end_date = kwargs.pop("end_date", None)
        if end_date is not None and isinstance(end_date, str):
            try:
                kwargs["end_date"] = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
            except (ValueError, AttributeError):
                pass  # 如果转换失败，忽略该字段

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)

        await self.session.flush()
        return self._to_dict(campaign)

    async def update_status(self, campaign_id: str, status: str) -> None:
        """更新广告投放状态"""
        result = await self.session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        campaign.status = CampaignStatus(status)
        await self.session.flush()

    async def update_spent(self, campaign_id: str, amount: float) -> None:
        """更新广告投放已消耗金额"""
        result = await self.session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        campaign.spent += amount
        await self.session.flush()

    async def add_material(self, campaign_id: str, material_id: str) -> None:
        """添加素材到广告投放"""
        result = await self.session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        campaign.add_material(material_id)
        await self.session.flush()

    async def remove_material(self, campaign_id: str, material_id: str) -> None:
        """从广告投放移除素材"""
        result = await self.session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        campaign.remove_material(material_id)
        await self.session.flush()

    async def get_materials(self, campaign_id: str) -> list[dict]:
        """获取广告投放的所有素材"""
        result = await self.session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            return []

        material_ids = campaign.get_material_ids()
        if not material_ids:
            return []

        result = await self.session.execute(
            select(Material).where(Material.id.in_(material_ids))
        )
        materials = result.scalars().all()

        from app.repositories.impl.sqlite_material_repo import SqliteMaterialRepository
        material_repo = SqliteMaterialRepository(self.session)
        return [material_repo._to_dict(m) for m in materials]

    async def delete(self, campaign_id: str) -> None:
        """删除广告投放"""
        result = await self.session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        await self.session.delete(campaign)
        await self.session.flush()
