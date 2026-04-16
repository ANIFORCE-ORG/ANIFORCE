"""Schemas 模块"""
from app.schemas.auth import *
from app.schemas.chat import *
from app.schemas.base import *
from app.schemas.project import *
from app.schemas.campaign import *
from app.schemas.material import *

__all__ = [
    # Base
    "ResponseBase",
    "ErrorDetail",
    "ErrorResponse",
    # Auth
    "LoginRequest",
    "TokenResponse",
    # Chat
    "ChatMessage",
    # Project
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListResponse",
    # Campaign
    "CampaignBase",
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignResponse",
    "CampaignListResponse",
    # Material
    "MaterialBase",
    "MaterialCreate",
    "MaterialUpdate",
    "MaterialResponse",
    "MaterialListResponse",
    "MaterialUploadRequest",
    "MaterialLinkCampaignRequest",
]
