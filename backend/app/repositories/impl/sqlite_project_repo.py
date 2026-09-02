"""项目 Repository SQLite 实现"""
import json
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Campaign, Project
from app.models.project import ProjectStatus


class SqliteProjectRepository:
    """项目数据访问 SQLite 实现"""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _normalize_campaign_platforms(platforms: list[str]) -> list[str]:
        unique_platforms = []
        for platform in platforms:
            value = platform.strip()
            if value and value not in unique_platforms:
                unique_platforms.append(value)

        preferred_order = ["Meta", "Google"]
        ordered_platforms = [platform for platform in preferred_order if platform in unique_platforms]
        ordered_platforms.extend(platform for platform in unique_platforms if platform not in preferred_order)
        return ordered_platforms

    async def _get_campaign_summary_by_project_ids(self, project_ids: list[str]) -> dict[str, dict[str, object]]:
        if not project_ids:
            return {}

        result = await self.session.execute(
            select(
                Campaign.project_id,
                func.count(Campaign.id).label("campaign_count"),
                func.group_concat(Campaign.platform, ",").label("campaign_platforms"),
            )
            .where(Campaign.project_id.in_(project_ids))
            .group_by(Campaign.project_id)
        )

        summary_map: dict[str, dict[str, object]] = {}
        for project_id, campaign_count, campaign_platforms in result.all():
            platforms = []
            if campaign_platforms:
                platforms = self._normalize_campaign_platforms(
                    [platform for platform in str(campaign_platforms).split(",") if platform]
                )
            summary_map[str(project_id)] = {
                "campaign_count": int(campaign_count or 0),
                "campaign_platforms": platforms,
            }
        return summary_map

    def _to_dict(self, project: Project, campaign_summary: dict[str, object] | None = None) -> dict:
        """将 ORM 对象转换为字典"""
        summary = campaign_summary or {}
        return {
            "id": project.id,
            "user_id": project.user_id,
            "name": project.name,
            "product": project.product,
            "description": project.description,
            "game_type": project.game_type,
            "target_market": project.target_market,
            "tags": json.loads(project.tags) if project.tags else [],
            "campaign_count": int(summary.get("campaign_count") or 0),
            "campaign_platforms": list(summary.get("campaign_platforms") or []),
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

        summary_map = await self._get_campaign_summary_by_project_ids([project.id])
        return self._to_dict(project, summary_map.get(project.id))

    async def get_by_id(self, project_id: str) -> dict | None:
        """根据 ID 获取项目"""
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return None

        summary_map = await self._get_campaign_summary_by_project_ids([project.id])
        return self._to_dict(project, summary_map.get(project.id))

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

        summary_map = await self._get_campaign_summary_by_project_ids([project.id for project in projects])
        return [self._to_dict(project, summary_map.get(project.id)) for project in projects]

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

        # 处理日期字符串转换
        if "start_date" in kwargs and isinstance(kwargs["start_date"], str):
            kwargs["start_date"] = datetime.fromisoformat(kwargs["start_date"]).date()

        if "end_date" in kwargs and isinstance(kwargs["end_date"], str):
            kwargs["end_date"] = datetime.fromisoformat(kwargs["end_date"]).date()

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
