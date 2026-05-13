"""
平台账号授权 API
处理 OAuth 认证和账号管理
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import secrets
import logging

from app.adapters import MetaAdsAdapter
from app.config.settings import get_settings

router = APIRouter(prefix="/platform-auth", tags=["platform-auth"])
logger = logging.getLogger(__name__)
settings = get_settings()


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


class AdAccountResponse(BaseModel):
    """广告账户响应"""
    id: str
    name: str
    account_status: int
    currency: str
    timezone_name: Optional[str] = None
    amount_spent: Optional[str] = None


# ==================== 临时存储（实际应使用数据库）====================

connected_accounts = []


# ==================== 适配器工厂 ====================

def get_adapter(platform: str):
    """
    获取平台适配器实例
    
    Args:
        platform: 平台类型 (meta/google/tiktok)
        
    Returns:
        适配器实例
    """
    if platform == "meta":
        config = {
            'api_version': 'v19.0',
            'app_id': settings.META_APP_ID,
            'app_secret': settings.META_APP_SECRET
        }
        return MetaAdsAdapter(config)
    elif platform == "google":
        # TODO: 实现 Google Ads 适配器
        raise HTTPException(status_code=501, detail="Google Ads adapter not implemented yet")
    elif platform == "tiktok":
        # TODO: 实现 TikTok Ads 适配器
        raise HTTPException(status_code=501, detail="TikTok Ads adapter not implemented yet")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")


# ==================== API 路由 ====================

@router.post("/{platform}/connect", response_model=ConnectResponse)
async def connect_platform(platform: str):
    """
    获取平台 OAuth 授权 URL
    
    Args:
        platform: 平台类型 (meta/google/tiktok)
        
    Returns:
        ConnectResponse: 包含授权 URL 和 state
    """
    try:
        adapter = get_adapter(platform)
        state = secrets.token_urlsafe(32)
        
        # 从环境变量或配置获取回调地址
        redirect_uri = settings.OAUTH_REDIRECT_URI or "http://localhost:3010/auth-callback"
        
        auth_url = adapter.get_oauth_url(redirect_uri, state)
        
        logger.info(f"Generated OAuth URL for platform: {platform}")
        return ConnectResponse(auth_url=auth_url, state=state)
        
    except Exception as e:
        logger.error(f"Failed to generate OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/callback", response_model=TokenResponse)
async def auth_callback(request: CallbackRequest):
    """
    处理 OAuth 回调，用 code 换取 access_token
    
    Args:
        request: 回调请求
        
    Returns:
        TokenResponse: Token 信息
    """
    try:
        logger.info(f"Processing OAuth callback for platform: {request.platform}")
        
        adapter = get_adapter(request.platform)
        
        # 用 code 换取 token
        token_data = await adapter.exchange_code_for_token(request.code, request.redirect_uri)
        
        # 如果支持长期 token，则进行转换
        if request.platform == "meta":
            try:
                long_lived_token = await adapter.get_long_lived_token(token_data['access_token'])
                token_data = long_lived_token
            except Exception as e:
                logger.warning(f"Failed to get long-lived token: {e}, using short-lived token")
        
        # TODO: 保存 token 到数据库
        # await save_platform_token(user_id, request.platform, token_data)
        
        return TokenResponse(
            access_token=token_data['access_token'],
            token_type=token_data.get('token_type', 'bearer'),
            expires_in=token_data.get('expires_in', 3600),
            refresh_token=token_data.get('refresh_token')
        )
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{platform}/accounts", response_model=List[AdAccountResponse])
async def get_ad_accounts(platform: str, access_token: str):
    """
    获取平台广告账户列表
    
    Args:
        platform: 平台类型
        access_token: 访问令牌
        
    Returns:
        List[AdAccountResponse]: 广告账户列表
    """
    try:
        adapter = get_adapter(platform)
        adapter.set_access_token(access_token)
        
        accounts = await adapter.get_ad_accounts()
        
        return [
            AdAccountResponse(
                id=acc['id'],
                name=acc['name'],
                account_status=acc.get('account_status', 1),
                currency=acc.get('currency', 'USD'),
                timezone_name=acc.get('timezone_name'),
                amount_spent=acc.get('amount_spent')
            )
            for acc in accounts
        ]
        
    except Exception as e:
        logger.error(f"Failed to get ad accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts", response_model=List[PlatformAccount])
async def get_connected_accounts():
    """
    获取已连接的平台账号列表
    
    Returns:
        List[PlatformAccount]: 账号列表
    """
    # TODO: 从数据库查询
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
    
    # TODO: 从数据库删除
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
