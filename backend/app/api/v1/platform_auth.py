"""
平台账号连接 API
处理 OAuth 认证和账号管理
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import secrets

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== 请求/响应模型 ====================

class PlatformAccount(BaseModel):
    """平台账号模型"""
    id: int
    platform: str
    account_id: str
    account_name: str
    status: str
    connected_at: datetime


class ConnectResponse(BaseModel):
    """连接响应"""
    auth_url: str
    state: str


class CallbackRequest(BaseModel):
    """OAuth 回调请求"""
    platform: str
    code: str
    redirect_uri: str
    state: Optional[str] = None


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None


# ==================== 临时存储（实际应使用数据库）====================

# 临时存储已连接的账号
connected_accounts = []


# ==================== API 路由 ====================

@router.post("/connect", response_model=ConnectResponse)
async def connect_platform(platform: str):
    """
    获取平台 OAuth 授权 URL

    Args:
        platform: 平台类型 (meta/google/tiktok)

    Returns:
        ConnectResponse: 包含授权 URL 和 state
    """
    state = secrets.token_urlsafe(32)
    redirect_uri = "http://localhost:3013/auth-callback"

    if platform == "meta":
        auth_url = (
            f"https://www.facebook.com/v19.0/dialog/oauth?"
            f"client_id=YOUR_META_APP_ID&"
            f"redirect_uri={redirect_uri}?platform=meta&"
            f"scope=ads_management,ads_read,business_management&"
            f"state={state}&"
            f"response_type=code"
        )
    elif platform == "google":
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id=YOUR_GOOGLE_CLIENT_ID&"
            f"redirect_uri={redirect_uri}?platform=google&"
            f"response_type=code&"
            f"scope=https://www.googleapis.com/auth/adwords&"
            f"access_type=offline&"
            f"prompt=consent&"
            f"state={state}"
        )
    elif platform == "tiktok":
        auth_url = (
            f"https://business-api.tiktok.com/portal/auth?"
            f"app_id=YOUR_TIKTOK_APP_ID&"
            f"redirect_uri={redirect_uri}?platform=tiktok&"
            f"state={state}"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    logger.info(f"Generated OAuth URL for platform: {platform}")
    return ConnectResponse(auth_url=auth_url, state=state)


@router.post("/callback", response_model=TokenResponse)
async def auth_callback(request: CallbackRequest):
    """
    处理 OAuth 回调，用 code 换取 access_token

    Args:
        request: 回调请求

    Returns:
        TokenResponse: Token 信息
    """
    logger.info(f"Processing OAuth callback for platform: {request.platform}")

    # 这里应该调用对应平台的 API 用 code 换取 token
    # 由于需要真实的 API 凭证，这里返回模拟数据

    if request.platform == "meta":
        # 实际应调用: https://graph.facebook.com/v19.0/oauth/access_token
        return TokenResponse(
            access_token="DEMO_META_ACCESS_TOKEN",
            token_type="bearer",
            expires_in=5183944,  # 60 天
            refresh_token=None
        )
    elif request.platform == "google":
        # 实际应调用: https://oauth2.googleapis.com/token
        return TokenResponse(
            access_token="DEMO_GOOGLE_ACCESS_TOKEN",
            token_type="bearer",
            expires_in=3600,
            refresh_token="DEMO_GOOGLE_REFRESH_TOKEN"
        )
    elif request.platform == "tiktok":
        # 实际应调用 TikTok OAuth API
        return TokenResponse(
            access_token="DEMO_TIKTOK_ACCESS_TOKEN",
            token_type="bearer",
            expires_in=86400,  # 24 小时
            refresh_token=None
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {request.platform}")


@router.get("/accounts", response_model=List[PlatformAccount])
async def get_connected_accounts():
    """
    获取已连接的平台账号列表

    Returns:
        List[PlatformAccount]: 账号列表
    """
    # 实际应从数据库查询
    return connected_accounts


@router.delete("/accounts/{account_id}")
async def disconnect_account(account_id: int):
    """
    断开平台账号连接

    Args:
        account_id: 账号 ID

    Returns:
        成功消息
    """
    global connected_accounts

    # 实际应从数据库删除
    connected_accounts = [acc for acc in connected_accounts if acc.id != account_id]

    logger.info(f"Disconnected account: {account_id}")
    return {"message": "Account disconnected successfully"}


@router.post("/accounts/test")
async def add_test_account(platform: str):
    """
    添加测试账号（用于开发测试）

    Args:
        platform: 平台类型

    Returns:
        创建的账号信息
    """
    account = PlatformAccount(
        id=len(connected_accounts) + 1,
        platform=platform,
        account_id=f"test_{platform}_123456",
        account_name=f"Test {platform.title()} Account",
        status="active",
        connected_at=datetime.now()
    )

    connected_accounts.append(account)
    logger.info(f"Added test account for platform: {platform}")

    return account
