"""项目 Repository SQLite 实现"""
import json
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Project
from app.models.project import ProjectStatus


class SqliteProjectRepository:
    """项目数据访问 SQLite 实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_dict(self, project: Project) -> dict:
        """将 ORM 对象转换为字典"""
        return {
            "id": project.id,
            "user_id": project.user_id,
            "name": project.name,
            "description": project.description,
            "game_type": project.game_type,
            "target_market": project.target_market,
            "tags": json.loads(project.tags) if project.tags else [],
            "total_budget": project.total_budget,
            "spent": project.spent,
            "status": project.status.value,
            "manager": project.manager,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }
    
    async def create(
        self, user_id: str, name: str, total_budget: float, **kwargs
    ) -> dict:
        """创建项目"""
        # 处理 tags
        tags = kwargs.pop("tags", None)
        if tags and isinstance(tags, list):
            kwargs["tags"] = json.dumps(tags)
        
        # 处理 status
        status = kwargs.pop("status", None)
        if status and isinstance(status, str):
            kwargs["status"] = ProjectStatus(status)
        
        # 处理日期字符串转换
        start_date = kwargs.pop("start_date", None)
        if start_date and isinstance(start_date, str):
            kwargs["start_date"] = datetime.fromisoformat(start_date).date()
        
        end_date = kwargs.pop("end_date", None)
        if end_date and isinstance(end_date, str):
            kwargs["end_date"] = datetime.fromisoformat(end_date).date()
        
        project = Project(
            user_id=user_id,
            name=name,
            total_budget=total_budget,
            **kwargs
        )
        self.session.add(project)
        await self.session.flush()
        
        return self._to_dict(project)
    
    async def get_by_id(self, project_id: str) -> dict | None:
        """根据 ID 获取项目"""
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return None
        
        return self._to_dict(project)
    
    async def list_by_user(
        self, user_id: str, status: str | None = None, limit: int = 20
    ) -> list[dict]:
        """查询用户的项目列表"""
        query = select(Project).where(Project.user_id == user_id)
        
        if status:
            query = query.where(Project.status == ProjectStatus(status))
        
        query = query.order_by(Project.created_at.desc()).limit(limit)
        
        result = await self.session.execute(query)
        projects = result.scalars().all()
        
        return [self._to_dict(p) for p in projects]
    
    async def update(self, project_id: str, **kwargs) -> None:
        """更新项目"""
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # 处理 tags
        if "tags" in kwargs and isinstance(kwargs["tags"], list):
            kwargs["tags"] = json.dumps(kwargs["tags"])
        
        # 处理 status
        if "status" in kwargs and isinstance(kwargs["status"], str):
            kwargs["status"] = ProjectStatus(kwargs["status"])
        
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        
        await self.session.flush()
    
    async def update_spent(self, project_id: str, amount: float) -> None:
        """更新项目已消耗金额"""
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        project.spent += amount
        await self.session.flush()
    
    async def delete(self, project_id: str) -> None:
        """删除项目"""
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        await self.session.delete(project)
        await self.session.flush()
