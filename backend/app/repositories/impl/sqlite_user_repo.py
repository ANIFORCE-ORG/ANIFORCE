"""用户 Repository SQLite 实现"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User


class SqliteUserRepository:
    """用户数据访问 SQLite 实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, user_id: str) -> dict | None:
        """根据 ID 获取用户"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        
        return {
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "name": user.name,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
    
    async def get_by_email(self, email: str) -> dict | None:
        """根据邮箱获取用户"""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        
        return {
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "name": user.name,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
    
    async def create(self, email: str, password_hash: str, name: str) -> dict:
        """创建用户"""
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
        )
        self.session.add(user)
        await self.session.flush()
        
        return {
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "name": user.name,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
    
    async def update(self, user_id: str, **kwargs) -> dict:
        """更新用户"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        await self.session.flush()
        
        return {
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "name": user.name,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
