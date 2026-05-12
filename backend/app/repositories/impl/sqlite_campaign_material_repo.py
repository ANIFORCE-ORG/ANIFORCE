"""Campaign material binding repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign_material import CampaignMaterial
from app.models.material import Material
from app.repositories.impl.sqlite_material_repo import SqliteMaterialRepository


class SqliteCampaignMaterialRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_dict(self, binding: CampaignMaterial, material: Material | None = None) -> dict:
        material_payload = None
        if material:
            material_payload = SqliteMaterialRepository(self.session)._to_dict(material)
        return {
            "id": binding.id,
            "campaign_id": binding.campaign_id,
            "material_id": binding.material_id,
            "title": binding.title,
            "description": binding.description,
            "copy": binding.copy,
            "source": binding.source,
            "sort_order": binding.sort_order,
            "status": binding.status,
            "created_by": binding.created_by,
            "created_at": binding.created_at,
            "updated_at": binding.updated_at,
            "material": material_payload,
        }

    async def list_by_campaign(self, campaign_id: str) -> list[dict]:
        result = await self.session.execute(
            select(CampaignMaterial, Material)
            .join(Material, CampaignMaterial.material_id == Material.id)
            .where(CampaignMaterial.campaign_id == campaign_id)
            .order_by(CampaignMaterial.sort_order.asc(), CampaignMaterial.created_at.asc())
        )
        return [self._to_dict(binding, material) for binding, material in result.all()]

    async def create_or_update(
        self,
        campaign_id: str,
        material_id: str,
        created_by: str | None = None,
        **kwargs,
    ) -> dict:
        result = await self.session.execute(
            select(CampaignMaterial).where(
                CampaignMaterial.campaign_id == campaign_id,
                CampaignMaterial.material_id == material_id,
            )
        )
        binding = result.scalar_one_or_none()
        if not binding:
            binding = CampaignMaterial(
                campaign_id=campaign_id,
                material_id=material_id,
                created_by=created_by,
            )
            self.session.add(binding)

        for key, value in kwargs.items():
            if value is not None and hasattr(binding, key):
                setattr(binding, key, value)
        await self.session.flush()
        return self._to_dict(binding)

    async def update(self, binding_id: str, **kwargs) -> dict | None:
        result = await self.session.execute(
            select(CampaignMaterial).where(CampaignMaterial.id == binding_id)
        )
        binding = result.scalar_one_or_none()
        if not binding:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(binding, key):
                setattr(binding, key, value)
        await self.session.flush()
        return self._to_dict(binding)

    async def delete(self, binding_id: str) -> CampaignMaterial | None:
        result = await self.session.execute(
            select(CampaignMaterial).where(CampaignMaterial.id == binding_id)
        )
        binding = result.scalar_one_or_none()
        if not binding:
            return None
        await self.session.delete(binding)
        await self.session.flush()
        return binding

