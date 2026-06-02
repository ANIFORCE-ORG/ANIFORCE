"""联系信息 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db
from app.repositories.impl.sqlite_contact_info_repo import SqliteContactInfoRepository

router = APIRouter(prefix="/contact", tags=["contact"])


class CreateContactRequest(BaseModel):
    """创建联系信息请求模型"""
    name: str
    company: str
    contact: str  # 邮箱或电话
    message: str | None = None


class ContactResponse(BaseModel):
    """联系信息响应模型"""
    id: str
    name: str
    company: str
    contact: str
    message: str | None
    source: str
    status: str
    created_at: str


@router.post("", response_model=ContactResponse)
async def create_contact(
    request: CreateContactRequest,
    db: AsyncSession = Depends(get_db),
):
    """创建联系信息（无需认证）"""
    repo = SqliteContactInfoRepository(db)
    
    try:
        contact = await repo.create(
            name=request.name,
            company=request.company,
            contact=request.contact,
            message=request.message,
            source="website"
        )
        
        # 提交事务
        await db.commit()
        
        return contact
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    status: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """获取联系信息列表（需要管理员权限）"""
    repo = SqliteContactInfoRepository(db)
    
    try:
        contacts = await repo.list_all(status=status, limit=limit)
        return contacts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取联系信息详情"""
    repo = SqliteContactInfoRepository(db)
    
    contact = await repo.get_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return contact


@router.put("/{contact_id}/status")
async def update_contact_status(
    contact_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
):
    """更新联系信息状态"""
    repo = SqliteContactInfoRepository(db)
    
    try:
        await repo.update_status(contact_id, status)
        await db.commit()
        return {"message": "Status updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除联系信息"""
    repo = SqliteContactInfoRepository(db)
    
    try:
        await repo.delete(contact_id)
        await db.commit()
        return {"message": "Contact deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
