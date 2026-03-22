from functools import lru_cache
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.settings import get_settings
from app.config.database import get_db
from app.repositories.protocols import (
    UserRepository,
    ProjectRepository,
    ChatRepository,
    MaterialRepository,
    CampaignRepository,
    MetricRepository,
)
from app.repositories.mock.mock_chat_repo import MockChatRepository
from app.repositories.mock.mock_material_repo import MockMaterialRepository
from app.repositories.mock.mock_campaign_repo import MockCampaignRepository
from app.repositories.mock.mock_metric_repo import MockMetricRepository
from app.repositories.impl.sqlite_user_repo import SqliteUserRepository
from app.repositories.impl.sqlite_project_repo import SqliteProjectRepository
from app.repositories.impl.sqlite_campaign_repo import SqliteCampaignRepository
from app.repositories.impl.sqlite_material_repo import SqliteMaterialRepository
from app.repositories.impl.sqlite_metric_repo import SqliteMetricRepository


def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository:
    """获取用户 Repository"""
    settings = get_settings()
    if settings.DEMO_MODE:
        # Demo 模式暂时也使用 SQLite
        return SqliteUserRepository(session)
    return SqliteUserRepository(session)


def get_project_repo(session: AsyncSession = Depends(get_db)) -> ProjectRepository:
    """获取项目 Repository"""
    settings = get_settings()
    if settings.DEMO_MODE:
        # Demo 模式暂时也使用 SQLite
        return SqliteProjectRepository(session)
    return SqliteProjectRepository(session)


@lru_cache()
def get_chat_repo() -> ChatRepository:
    """获取对话 Repository"""
    settings = get_settings()
    if settings.DEMO_MODE:
        return MockChatRepository()
    # 生产模式：返回真实 MongoDB 实现
    raise NotImplementedError("生产模式 ChatRepository 尚未实现")


def get_material_repo(session: AsyncSession = Depends(get_db)) -> MaterialRepository:
    """获取素材 Repository"""
    settings = get_settings()
    if settings.DEMO_MODE:
        # Demo 模式暂时也使用 SQLite
        return SqliteMaterialRepository(session)
    return SqliteMaterialRepository(session)


def get_campaign_repo(session: AsyncSession = Depends(get_db)) -> CampaignRepository:
    """获取广告投放 Repository"""
    settings = get_settings()
    if settings.DEMO_MODE:
        # Demo 模式暂时也使用 SQLite
        return SqliteCampaignRepository(session)
    return SqliteCampaignRepository(session)


def get_metric_repo(session: AsyncSession = Depends(get_db)) -> MetricRepository:
    """获取监控指标 Repository"""
    settings = get_settings()
    if settings.DEMO_MODE:
        # Demo 模式暂时也使用 SQLite
        return SqliteMetricRepository(session)
    return SqliteMetricRepository(session)
