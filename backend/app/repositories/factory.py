from functools import lru_cache
from app.config.settings import get_settings
from app.repositories.protocols import ChatRepository, MaterialRepository, CampaignRepository, MetricRepository
from app.repositories.mock.mock_chat_repo import MockChatRepository
from app.repositories.mock.mock_material_repo import MockMaterialRepository
from app.repositories.mock.mock_campaign_repo import MockCampaignRepository
from app.repositories.mock.mock_metric_repo import MockMetricRepository


@lru_cache()
def get_chat_repo() -> ChatRepository:
    settings = get_settings()
    if settings.DEMO_MODE:
        return MockChatRepository()
    # 生产模式：返回真实 MongoDB 实现
    raise NotImplementedError("生产模式 ChatRepository 尚未实现")


@lru_cache()
def get_material_repo() -> MaterialRepository:
    settings = get_settings()
    if settings.DEMO_MODE:
        return MockMaterialRepository()
    raise NotImplementedError("生产模式 MaterialRepository 尚未实现")


@lru_cache()
def get_campaign_repo() -> CampaignRepository:
    settings = get_settings()
    if settings.DEMO_MODE:
        return MockCampaignRepository()
    raise NotImplementedError("生产模式 CampaignRepository 尚未实现")


@lru_cache()
def get_metric_repo() -> MetricRepository:
    settings = get_settings()
    if settings.DEMO_MODE:
        return MockMetricRepository()
    raise NotImplementedError("生产模式 MetricRepository 尚未实现")
