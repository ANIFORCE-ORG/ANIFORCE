"""素材 Repository SQLite 实现"""
import json
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Material
from app.models.material import MaterialStatus, MaterialType


MATERIAL_METADATA_COLUMNS = {
    "original_filename": "VARCHAR(255)",
    "lifecycle_status": "VARCHAR(20) DEFAULT 'active' NOT NULL",
    "processing_status": "VARCHAR(20) DEFAULT 'ready' NOT NULL",
    "archived_at": "DATETIME",
    "updated_at": "DATETIME",
    "storage_object_key": "TEXT",
    "mime_type": "VARCHAR(100)",
    "checksum_sha256": "VARCHAR(64)",
    "poster_url": "TEXT",
    "preview_url": "TEXT",
    "media_kind": "VARCHAR(20)",
    "format": "VARCHAR(20)",
    "width": "INTEGER",
    "height": "INTEGER",
    "ratio": "VARCHAR(20)",
    "source": "VARCHAR(50)",
    "creator": "VARCHAR(100)",
    "rights": "VARCHAR(100)",
    "platforms": "TEXT",
    "review_status": "VARCHAR(50)",
    "source_account": "VARCHAR(100)",
    "placements": "TEXT",
    "score": "INTEGER",
    "fatigue": "INTEGER",
}


class SqliteMaterialRepository:
    """素材数据访问 SQLite 实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._schema_ready = False

    async def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        dialect = self.session.bind.dialect.name if self.session.bind else ""
        if dialect != "sqlite":
            self._schema_ready = True
            return

        result = await self.session.execute(text("PRAGMA table_info(materials)"))
        existing = {row[1] for row in result.fetchall()}
        for name, column_type in MATERIAL_METADATA_COLUMNS.items():
            if name not in existing:
                await self.session.execute(text(f"ALTER TABLE materials ADD COLUMN {name} {column_type}"))
        self._schema_ready = True
    
    def _to_dict(self, material: Material) -> dict:
        """将 ORM 对象转换为字典"""
        return {
            "id": material.id,
            "user_id": material.user_id,
            "project_ids": material.get_project_ids(),
            "campaign_ids": material.get_campaign_ids(),
            "name": material.name,
            "original_filename": material.original_filename,
            "type": material.type.value,
            "status": material.status.value,
            "lifecycle_status": material.lifecycle_status,
            "processing_status": material.processing_status,
            "archived_at": material.archived_at.isoformat() if material.archived_at else None,
            "url": material.url,
            "storage_object_key": material.storage_object_key,
            "mime_type": material.mime_type,
            "checksum_sha256": material.checksum_sha256,
            "thumbnail_url": material.thumbnail_url,
            "poster_url": material.poster_url,
            "preview_url": material.preview_url,
            "ctr_estimate": material.ctr_estimate,
            "tags": json.loads(material.tags) if material.tags else [],
            "media_kind": material.media_kind,
            "format": material.format,
            "width": material.width,
            "height": material.height,
            "ratio": material.ratio,
            "source": material.source,
            "creator": material.creator,
            "rights": material.rights,
            "platforms": json.loads(material.platforms) if material.platforms else [],
            "review_status": material.review_status,
            "source_account": material.source_account,
            "placements": json.loads(material.placements) if material.placements else [],
            "score": material.score,
            "fatigue": material.fatigue,
            "duration": material.duration,
            "file_size": material.file_size,
            "created_at": material.created_at.isoformat(),
            "updated_at": material.updated_at.isoformat() if material.updated_at else None,
        }
    
    async def create(
        self, user_id: str, name: str, type: str, url: str, **kwargs
    ) -> dict:
        """创建素材"""
        await self._ensure_schema()
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

        for json_field in ("platforms", "placements"):
            value = kwargs.pop(json_field, None)
            if value and isinstance(value, list):
                kwargs[json_field] = json.dumps(value, ensure_ascii=False)
        
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
        await self._ensure_schema()
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
        await self._ensure_schema()
        query = select(Material).where(Material.user_id == user_id)

        if type:
            query = query.where(Material.type == MaterialType(type))
        
        query = query.order_by(Material.created_at.desc()).limit(limit)
        
        result = await self.session.execute(query)
        materials = result.scalars().all()
        
        return [self._to_dict(m) for m in materials]
    
    async def list_by_project(self, project_id: str, limit: int = 50) -> list[dict]:
        """查询项目的素材列表"""
        await self._ensure_schema()
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
        await self._ensure_schema()
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

    async def update(self, material_id: str, **kwargs) -> dict:
        """更新素材基础信息"""
        await self._ensure_schema()
        result = await self.session.execute(
            select(Material).where(Material.id == material_id)
        )
        material = result.scalar_one_or_none()
        if not material:
            raise ValueError(f"Material {material_id} not found")

        allowed_fields = {
            "name",
            "url",
            "original_filename",
            "storage_object_key",
            "mime_type",
            "checksum_sha256",
            "status",
            "lifecycle_status",
            "processing_status",
            "archived_at",
            "thumbnail_url",
            "poster_url",
            "preview_url",
            "ctr_estimate",
            "tags",
            "media_kind",
            "format",
            "width",
            "height",
            "ratio",
            "source",
            "creator",
            "rights",
            "platforms",
            "review_status",
            "source_account",
            "placements",
            "score",
            "fatigue",
            "duration",
            "file_size",
        }
        for key, value in kwargs.items():
            if key not in allowed_fields:
                continue
            if value is None:
                continue
            if key == "status":
                setattr(material, key, MaterialStatus(value))
            elif key in {"tags", "platforms", "placements"} and isinstance(value, list):
                setattr(material, key, json.dumps(value, ensure_ascii=False))
            else:
                setattr(material, key, value)

        await self.session.flush()
        return self._to_dict(material)
    
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
