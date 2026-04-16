"""素材 Repository SQLite 实现"""
import json
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Material
from app.models.material import MaterialType


class SqliteMaterialRepository:
    """素材数据访问 SQLite 实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_dict(self, material: Material) -> dict:
        """将 ORM 对象转换为字典"""
        return {
            "id": material.id,
            "user_id": material.user_id,
            "project_ids": material.get_project_ids(),
            "campaign_ids": material.get_campaign_ids(),
            "name": material.name,
            "type": material.type.value,
            "media_type": material.media_type,
            "status": material.status.value,
            "url": material.url,
            "thumbnail_url": material.thumbnail_url,
            "ctr_estimate": material.ctr_estimate,
            "fatigue": material.fatigue,
            "is_hero": material.is_hero,
            "tags": material.get_tags(),
            "duration": material.duration,
            "file_size": material.file_size,
            "created_at": material.created_at.isoformat(),
        }
    
    async def create(
        self, user_id: str, name: str, type: str, url: str, **kwargs
    ) -> dict:
        """创建素材"""
        # 处理 project_ids
        project_ids = kwargs.pop("project_ids", None)
        if project_ids and isinstance(project_ids, list):
            kwargs["project_ids"] = json.dumps(project_ids)
        
        # 处理 campaign_ids
        campaign_ids = kwargs.pop("campaign_ids", None)
        if campaign_ids and isinstance(campaign_ids, list):
            kwargs["campaign_ids"] = json.dumps(campaign_ids)
        
        # 处理 tags
        tags = kwargs.pop("tags", None)
        if tags and isinstance(tags, list):
            kwargs["tags"] = json.dumps(tags)
        
        # 处理 type
        material_type = MaterialType(type)
        
        material = Material(
            user_id=user_id,
            name=name,
            type=material_type,
            url=url,
            **kwargs
        )
        self.session.add(material)
        await self.session.flush()
        
        return self._to_dict(material)
    
    async def get_by_id(self, material_id: str) -> dict | None:
        """根据 ID 获取素材"""
        result = await self.session.execute(
            select(Material).where(Material.id == material_id)
        )
        material = result.scalar_one_or_none()
        if not material:
            return None
        
        return self._to_dict(material)
    
    async def list_by_user(
        self, user_id: str, type: str | None = None, limit: int = 50
    ) -> list[dict]:
        """查询用户的素材列表"""
        query = select(Material).where(Material.user_id == user_id)

        if type:
            query = query.where(Material.type == MaterialType(type))

        query = query.order_by(Material.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        materials = result.scalars().all()

        return [self._to_dict(m) for m in materials]

    async def list_by_fatigue(
        self, user_id: str, min_fatigue: float = 0.0, limit: int = 50
    ) -> list[dict]:
        """按疲劳度查询素材列表"""
        query = select(Material).where(
            Material.user_id == user_id,
            Material.fatigue >= min_fatigue
        ).order_by(Material.fatigue.desc()).limit(limit)

        result = await self.session.execute(query)
        materials = result.scalars().all()

        return [self._to_dict(m) for m in materials]

    async def list_hero_materials(
        self, user_id: str, limit: int = 50
    ) -> list[dict]:
        """查询英雄素材列表"""
        query = select(Material).where(
            Material.user_id == user_id,
            Material.is_hero == True
        ).order_by(Material.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        materials = result.scalars().all()

        return [self._to_dict(m) for m in materials]

    async def update(self, material_id: str, **kwargs) -> None:
        """更新素材"""
        result = await self.session.execute(
            select(Material).where(Material.id == material_id)
        )
        material = result.scalar_one_or_none()
        if not material:
            raise ValueError(f"Material {material_id} not found")

        # 处理 project_ids
        if "project_ids" in kwargs and isinstance(kwargs["project_ids"], list):
            kwargs["project_ids"] = json.dumps(kwargs["project_ids"])

        # 处理 campaign_ids
        if "campaign_ids" in kwargs and isinstance(kwargs["campaign_ids"], list):
            kwargs["campaign_ids"] = json.dumps(kwargs["campaign_ids"])

        # 处理 tags
        if "tags" in kwargs and isinstance(kwargs["tags"], list):
            kwargs["tags"] = json.dumps(kwargs["tags"])

        # 处理 type
        if "type" in kwargs and isinstance(kwargs["type"], str):
            kwargs["type"] = MaterialType(kwargs["type"])

        for key, value in kwargs.items():
            if hasattr(material, key):
                setattr(material, key, value)

        await self.session.flush()
    
    async def list_by_project(self, project_id: str, limit: int = 50) -> list[dict]:
        """查询项目的素材列表"""
        # SQLite JSON 查询
        result = await self.session.execute(
            select(Material)
            .where(Material.project_ids.like(f'%"{project_id}"%'))
            .order_by(Material.created_at.desc())
            .limit(limit)
        )
        materials = result.scalars().all()
        
        # 过滤确保精确匹配
        filtered = [m for m in materials if project_id in m.get_project_ids()]
        return [self._to_dict(m) for m in filtered]
    
    async def list_by_campaign(self, campaign_id: str, limit: int = 50) -> list[dict]:
        """查询广告计划的素材列表"""
        # SQLite JSON 查询
        result = await self.session.execute(
            select(Material)
            .where(Material.campaign_ids.like(f'%"{campaign_id}"%'))
            .order_by(Material.created_at.desc())
            .limit(limit)
        )
        materials = result.scalars().all()
        
        # 过滤确保精确匹配
        filtered = [m for m in materials if campaign_id in m.get_campaign_ids()]
        return [self._to_dict(m) for m in filtered]
    
    async def add_to_project(self, material_id: str, project_id: str) -> None:
        """添加素材到项目"""
        result = await self.session.execute(
            select(Material).where(Material.id == material_id)
        )
        material = result.scalar_one_or_none()
        if not material:
            raise ValueError(f"Material {material_id} not found")
        
        material.add_project(project_id)
        await self.session.flush()
    
    async def remove_from_project(self, material_id: str, project_id: str) -> None:
        """从项目移除素材"""
        result = await self.session.execute(
            select(Material).where(Material.id == material_id)
        )
        material = result.scalar_one_or_none()
        if not material:
            raise ValueError(f"Material {material_id} not found")
        
        material.remove_project(project_id)
        await self.session.flush()
    
    async def add_to_campaign(self, material_id: str, campaign_id: str) -> None:
        """添加素材到广告计划"""
        result = await self.session.execute(
            select(Material).where(Material.id == material_id)
        )
        material = result.scalar_one_or_none()
        if not material:
            raise ValueError(f"Material {material_id} not found")
        
        material.add_campaign(campaign_id)
        await self.session.flush()
    
    async def remove_from_campaign(self, material_id: str, campaign_id: str) -> None:
        """从广告计划移除素材"""
        result = await self.session.execute(
            select(Material).where(Material.id == material_id)
        )
        material = result.scalar_one_or_none()
        if not material:
            raise ValueError(f"Material {material_id} not found")
        
        material.remove_campaign(campaign_id)
        await self.session.flush()
    
    async def delete(self, material_id: str) -> None:
        """删除素材"""
        result = await self.session.execute(
            select(Material).where(Material.id == material_id)
        )
        material = result.scalar_one_or_none()
        if not material:
            raise ValueError(f"Material {material_id} not found")
        
        await self.session.delete(material)
        await self.session.flush()
