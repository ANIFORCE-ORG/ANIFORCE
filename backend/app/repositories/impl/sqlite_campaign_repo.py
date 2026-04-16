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
            "budget": campaign.budget,
            "spent": campaign.spent,
            "target_cpa": campaign.target_cpa,
            "status": campaign.status.value,
            "pipeline_step": campaign.pipeline_step,
            "learning_phase": campaign.learning_phase,
            "auto_optimize_enabled": campaign.auto_optimize_enabled,
            "optimization_rules": campaign.get_optimization_rules(),
            "material_ids": campaign.get_material_ids(),
            "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
            "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
            "config": json.loads(campaign.config) if campaign.config else {},
            "created_at": campaign.created_at.isoformat(),
            "updated_at": campaign.updated_at.isoformat(),
        }
    
    async def create(
        self, project_id: str, name: str, platform: str, budget: float, **kwargs
    ) -> dict:
        """创建广告投放"""
        # 处理 material_ids
        material_ids = kwargs.pop("material_ids", None)
        if material_ids and isinstance(material_ids, list):
            kwargs["material_ids"] = json.dumps(material_ids)

        # 处理 optimization_rules
        optimization_rules = kwargs.pop("optimization_rules", None)
        if optimization_rules and isinstance(optimization_rules, list):
            kwargs["optimization_rules"] = json.dumps(optimization_rules)

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

    async def list_by_pipeline_step(
        self, project_id: str, pipeline_step: str, limit: int = 20
    ) -> list[dict]:
        """按 Pipeline 阶段查询广告投放列表"""
        query = select(Campaign).where(
            Campaign.project_id == project_id,
            Campaign.pipeline_step == pipeline_step
        ).order_by(Campaign.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        campaigns = result.scalars().all()

        return [self._to_dict(c) for c in campaigns]

    async def update(self, campaign_id: str, **kwargs) -> None:
        """更新广告投放"""
        result = await self.session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # 处理 material_ids
        if "material_ids" in kwargs and isinstance(kwargs["material_ids"], list):
            kwargs["material_ids"] = json.dumps(kwargs["material_ids"])

        # 处理 optimization_rules
        if "optimization_rules" in kwargs and isinstance(kwargs["optimization_rules"], list):
            kwargs["optimization_rules"] = json.dumps(kwargs["optimization_rules"])

        # 处理 config
        if "config" in kwargs and isinstance(kwargs["config"], dict):
            kwargs["config"] = json.dumps(kwargs["config"])

        # 处理 status
        if "status" in kwargs and isinstance(kwargs["status"], str):
            kwargs["status"] = CampaignStatus(kwargs["status"])

        # 处理 platform
        if "platform" in kwargs and isinstance(kwargs["platform"], str):
            kwargs["platform"] = Platform(kwargs["platform"])

        for key, value in kwargs.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)

        await self.session.flush()
    
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
