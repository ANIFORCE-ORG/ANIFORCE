"""组织管理 API"""
import secrets
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.config.database import get_db
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.api.deps import get_current_user


router = APIRouter(prefix="/organizations", tags=["organizations"])


# ============ Pydantic 模型 ============

class OrganizationCreate(BaseModel):
    """创建组织请求"""
    name: str = Field(..., min_length=1, max_length=255, description="组织名称")
    org_code: str = Field(..., min_length=3, max_length=100, description="组织代码")
    description: str | None = Field(None, max_length=1000, description="组织描述")


class OrganizationJoin(BaseModel):
    """加入组织请求"""
    org_code: str = Field(..., description="组织代码")
    invite_code: str = Field(..., description="邀请码")


class OrganizationResponse(BaseModel):
    """组织响应"""
    id: str
    name: str
    org_code: str
    description: str | None
    owner_id: str
    status: str
    member_count: int
    role: str  # 当前用户在组织中的角色
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrganizationMemberResponse(BaseModel):
    """组织成员响应"""
    id: str
    user_id: str
    user_name: str | None
    user_email: str
    role: str
    status: str
    joined_at: datetime
    
    class Config:
        from_attributes = True


class InviteCodeResponse(BaseModel):
    """邀请码响应"""
    invite_code: str
    expires_at: datetime | None


# ============ API 端点 ============

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建组织"""
    # 检查 org_code 是否已存在
    stmt = select(Organization).where(Organization.org_code == data.org_code)
    result = await db.execute(stmt)
    existing_org = result.scalar_one_or_none()
    
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="组织 ID 已存在"
        )
    
    # 生成邀请码（8位随机字符串）
    invite_code = secrets.token_urlsafe(8)
    
    # 创建组织
    org = Organization(
        name=data.name,
        org_code=data.org_code,
        description=data.description,
        invite_code=invite_code,
        owner_id=current_user["id"],
        status="active"
    )
    db.add(org)
    await db.flush()  # 先 flush 以生成 org.id
    
    # 创建组织成员记录（创建者自动成为管理员）
    member = OrganizationMember(
        organization_id=org.id,
        user_id=current_user["id"],
        role="admin",
        status="active"
    )
    db.add(member)
    
    await db.commit()
    await db.refresh(org)
    
    # 获取成员数量
    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.status == "active"
    )
    result = await db.execute(stmt)
    member_count = len(result.scalars().all())
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        org_code=org.org_code,
        description=org.description,
        owner_id=org.owner_id,
        status=org.status,
        member_count=member_count,
        role="admin",
        created_at=org.created_at
    )


@router.post("/join", response_model=OrganizationResponse)
async def join_organization(
    data: OrganizationJoin,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """加入组织"""
    # 查找组织
    stmt = select(Organization).where(
        Organization.org_code == data.org_code,
        Organization.status == "active"
    )
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在或已停用"
        )
    
    # 验证邀请码
    if data.invite_code != org.invite_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码无效"
        )
    
    # 检查是否已经是成员
    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.user_id == current_user["id"]
    )
    result = await db.execute(stmt)
    existing_member = result.scalar_one_or_none()
    
    if existing_member:
        if existing_member.status == "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已经是该组织的成员"
            )
        else:
            # 重新激活成员
            existing_member.status = "active"
            existing_member.joined_at = datetime.utcnow()
            await db.commit()
            member = existing_member
    else:
        # 创建新成员
        member = OrganizationMember(
            organization_id=org.id,
            user_id=current_user["id"],
            role="member",
            status="active"
        )
        db.add(member)
        await db.commit()
    
    # 获取成员数量
    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.status == "active"
    )
    result = await db.execute(stmt)
    member_count = len(result.scalars().all())
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        org_code=org.org_code,
        description=org.description,
        owner_id=org.owner_id,
        status=org.status,
        member_count=member_count,
        role=member.role,
        created_at=org.created_at
    )


@router.get("", response_model=List[OrganizationResponse])
async def get_my_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取我的组织列表"""
    # 查询用户所属的所有组织
    stmt = select(Organization, OrganizationMember).join(
        OrganizationMember,
        Organization.id == OrganizationMember.organization_id
    ).where(
        OrganizationMember.user_id == current_user["id"],
        OrganizationMember.status == "active",
        Organization.status == "active"
    )
    result = await db.execute(stmt)
    org_members = result.all()
    
    organizations = []
    for org, member in org_members:
        # 获取成员数量
        stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.status == "active"
        )
        result = await db.execute(stmt)
        member_count = len(result.scalars().all())
        
        organizations.append(OrganizationResponse(
            id=org.id,
            name=org.name,
            org_code=org.org_code,
            description=org.description,
            owner_id=org.owner_id,
            status=org.status,
            member_count=member_count,
            role=member.role,
            created_at=org.created_at
        ))
    
    return organizations


@router.delete("/{organization_id}")
async def leave_organization(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """离开组织"""
    # 查找组织成员记录
    stmt = select(OrganizationMember, Organization).join(
        Organization,
        OrganizationMember.organization_id == Organization.id
    ).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user["id"],
        OrganizationMember.status == "active"
    )
    result = await db.execute(stmt)
    member_org = result.first()
    
    if not member_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您不是该组织的成员"
        )
    
    member, org = member_org
    
    # 如果是拥有者，不能离开（需要先转让或解散组织）
    if org.owner_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="组织拥有者不能离开组织，请先转让所有权或解散组织"
        )
    
    # 将成员状态设为 inactive
    member.status = "inactive"
    await db.commit()
    
    return {"message": "成功离开组织"}


@router.delete("/{organization_id}/disband")
async def disband_organization(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """解散组织（仅拥有者）"""
    # 查找组织
    stmt = select(Organization).where(Organization.id == organization_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )
    
    # 检查是否是拥有者
    if org.owner_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有组织拥有者可以解散组织"
        )
    
    # 删除组织（会级联删除成员）
    await db.delete(org)
    await db.commit()
    
    return {"message": "组织已解散"}


@router.get("/{organization_id}/invite-code", response_model=InviteCodeResponse)
async def get_invite_code(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取组织邀请码（仅管理员）"""
    # 查找组织和成员记录
    stmt = select(Organization, OrganizationMember).join(
        OrganizationMember,
        Organization.id == OrganizationMember.organization_id
    ).where(
        Organization.id == organization_id,
        OrganizationMember.user_id == current_user["id"],
        OrganizationMember.status == "active"
    )
    result = await db.execute(stmt)
    org_member = result.first()
    
    if not org_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在或您不是成员"
        )
    
    org, member = org_member
    
    # 检查是否是管理员
    if member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以获取邀请码"
        )
    
    # 返回组织的邀请码
    return InviteCodeResponse(
        invite_code=org.invite_code,
        expires_at=None  # 永久有效
    )


@router.get("/{org_id}/members")
async def get_organization_members(
    org_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索成员名称或邮箱"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取组织成员列表"""
    from sqlalchemy import select, func, or_
    from app.models.user import User
    
    # 检查组织是否存在
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )
    
    # 检查当前用户是否是组织成员
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user["id"]
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该组织的成员"
        )
    
    # 构建查询
    query = select(OrganizationMember, User).join(
        User, OrganizationMember.user_id == User.id
    ).where(OrganizationMember.organization_id == org_id)
    
    # 添加搜索条件
    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # 执行查询
    result = await db.execute(query)
    members_data = result.all()
    
    # 构建响应
    members = []
    for member_obj, user_obj in members_data:
        members.append({
            "id": member_obj.id,
            "user_id": user_obj.id,
            "user_name": user_obj.name or user_obj.email.split('@')[0],
            "user_email": user_obj.email,
            "role": member_obj.role,
            "joined_at": member_obj.created_at.isoformat()
        })
    
    return {
        "members": members,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("/{org_id}/members")
async def add_organization_member(
    org_id: str,
    email: str = Query(..., description="成员邮箱"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """添加组织成员"""
    from app.models.user import User
    
    # 检查组织是否存在
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )
    
    # 检查当前用户是否是管理员
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user["id"]
        )
    )
    member = result.scalar_one_or_none()
    if not member or member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以添加成员"
        )
    
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该邮箱对应的用户不存在"
        )
    
    # 检查用户是否已经是组织成员
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id
        )
    )
    existing_member = result.scalar_one_or_none()
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户已经是组织成员"
        )
    
    # 添加成员
    new_member = OrganizationMember(
        organization_id=org_id,
        user_id=user.id,
        role="member"
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)
    
    return {
        "message": "成员添加成功",
        "member": {
            "id": new_member.id,
            "user_id": user.id,
            "user_name": user.name or user.email.split('@')[0],
            "user_email": user.email,
            "role": new_member.role,
            "joined_at": new_member.created_at.isoformat()
        }
    }


@router.delete("/{org_id}/members/{user_id}")
async def remove_organization_member(
    org_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """移除组织成员"""
    # 检查组织是否存在
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )
    
    # 检查当前用户是否是管理员
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user["id"]
        )
    )
    member = result.scalar_one_or_none()
    if not member or member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以移除成员"
        )
    
    # 检查要移除的成员是否存在
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id
        )
    )
    target_member = result.scalar_one_or_none()
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该用户不是组织成员"
        )
    
    # 不能移除管理员
    if target_member.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能移除管理员"
        )
    
    # 移除成员
    await db.delete(target_member)
    await db.commit()
    
    return {"message": "成员已移除"}
