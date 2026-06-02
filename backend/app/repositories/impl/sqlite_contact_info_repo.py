"""联系信息 Repository SQLite 实现"""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ContactInfo


class SqliteContactInfoRepository:
    """联系信息数据访问 SQLite 实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_dict(self, contact: ContactInfo) -> dict:
        """将 ORM 对象转换为字典"""
        return {
            "id": contact.id,
            "name": contact.name,
            "company": contact.company,
            "contact": contact.contact,
            "message": contact.message,
            "source": contact.source,
            "status": contact.status,
            "created_at": contact.created_at.isoformat(),
            "updated_at": contact.updated_at.isoformat(),
        }
    
    async def create(
        self,
        name: str,
        company: str,
        contact: str,
        message: str | None = None,
        source: str = "website"
    ) -> dict:
        """创建联系信息"""
        contact_info = ContactInfo(
            name=name,
            company=company,
            contact=contact,
            message=message,
            source=source,
            status="pending"
        )
        self.session.add(contact_info)
        await self.session.flush()
        
        return self._to_dict(contact_info)
    
    async def get_by_id(self, contact_id: str) -> dict | None:
        """根据 ID 获取联系信息"""
        result = await self.session.execute(
            select(ContactInfo).where(ContactInfo.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            return None
        
        return self._to_dict(contact)
    
    async def list_all(
        self, status: str | None = None, limit: int = 100
    ) -> list[dict]:
        """查询所有联系信息"""
        query = select(ContactInfo)
        
        if status:
            query = query.where(ContactInfo.status == status)
        
        query = query.order_by(ContactInfo.created_at.desc()).limit(limit)
        
        result = await self.session.execute(query)
        contacts = result.scalars().all()
        
        return [self._to_dict(c) for c in contacts]
    
    async def update_status(self, contact_id: str, status: str) -> None:
        """更新联系信息状态"""
        result = await self.session.execute(
            select(ContactInfo).where(ContactInfo.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise ValueError(f"ContactInfo {contact_id} not found")
        
        contact.status = status
        await self.session.flush()
    
    async def delete(self, contact_id: str) -> None:
        """删除联系信息"""
        result = await self.session.execute(
            select(ContactInfo).where(ContactInfo.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise ValueError(f"ContactInfo {contact_id} not found")
        
        await self.session.delete(contact)
        await self.session.flush()
