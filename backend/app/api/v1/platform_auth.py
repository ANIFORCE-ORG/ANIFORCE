"""
平台账号授权 API
处理 OAuth 认证和账号管理
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets
import logging

from app.adapters import MetaAdsAdapter
from app.config.settings import get_settings
from app.config.database import get_db
from app.models import PlatformConnection
from app.api.deps import get_current_user

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


class MetaConfigRequest(BaseModel):
    """Meta 配置请求"""
    account_name: str
    app_id: str
    app_secret: Optional[str] = None
    scopes: List[str]
    connection_id: Optional[str] = None  # 编辑模式下的连接 ID


class PlatformConnectionResponse(BaseModel):
    """平台连接响应"""
    id: str
    platform: str
    account_id: str
    account_name: Optional[str]
    status: str
    scopes: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


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


@router.post("/meta/config", response_model=PlatformConnectionResponse)
async def save_meta_config(
    config: MetaConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    保存 Meta 平台配置
    
    Args:
        config: Meta 配置信息
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        PlatformConnectionResponse: 保存的平台连接信息
    """
    try:
        user_id = current_user["id"]
        
        # 编辑模式：通过 connection_id 更新
        if config.connection_id:
            # 获取要更新的连接
            stmt = select(PlatformConnection).where(
                PlatformConnection.id == config.connection_id,
                PlatformConnection.user_id == user_id
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                raise HTTPException(status_code=404, detail="连接不存在")
            
            # 检查 APP ID 是否与其他记录冲突（排除当前记录）
            if existing.account_id != config.app_id:
                conflict_stmt = select(PlatformConnection).where(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.platform == "Meta",
                    PlatformConnection.account_id == config.app_id,
                    PlatformConnection.id != config.connection_id
                )
                conflict_result = await db.execute(conflict_stmt)
                conflict = conflict_result.scalar_one_or_none()
                
                if conflict:
                    raise HTTPException(
                        status_code=409,
                        detail=f"APP ID 已存在，与账户「{conflict.account_name or conflict.account_id}」冲突"
                    )
            
            # 更新配置
            existing.account_name = config.account_name
            existing.account_id = config.app_id
            # 只在提供了 app_secret 时才更新
            if config.app_secret:
                existing.account_secret = config.app_secret
            existing.scopes = config.scopes
            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            logger.info(f"Updated Meta config for user: {user_id}, connection: {config.connection_id}")
            return existing
        
        # 新建模式：检查 APP ID 是否已存在
        conflict_stmt = select(PlatformConnection).where(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == "Meta",
            PlatformConnection.account_id == config.app_id
        )
        conflict_result = await db.execute(conflict_stmt)
        conflict = conflict_result.scalar_one_or_none()
        
        if conflict:
            raise HTTPException(
                status_code=409,
                detail=f"APP ID 已存在，与账户「{conflict.account_name or conflict.account_id}」冲突"
            )
        
        # 创建新配置
        if not config.app_secret:
            raise HTTPException(status_code=400, detail="创建新配置时 App Secret 不能为空")
        
        new_connection = PlatformConnection(
            user_id=user_id,
            platform="Meta",
            account_id=config.app_id,
            account_name=config.account_name,
            account_secret=config.app_secret,
            access_token="",  # 暂时为空，等待 OAuth 授权
            scopes=config.scopes,
            status="unauthorized"
        )
        db.add(new_connection)
        await db.commit()
        await db.refresh(new_connection)
        logger.info(f"Created Meta config for user: {user_id}")
        return new_connection
            
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save Meta config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta/config", response_model=Optional[PlatformConnectionResponse])
async def get_meta_config(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取 Meta 平台配置
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        PlatformConnectionResponse: 平台连接信息，如果不存在则返回 None
    """
    try:
        user_id = current_user["id"]
        
        stmt = select(PlatformConnection).where(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == "Meta"
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        return connection
        
    except Exception as e:
        logger.error(f"Failed to get Meta config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections", response_model=List[PlatformConnectionResponse])
async def get_all_connections(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取当前用户的所有平台连接
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        List[PlatformConnectionResponse]: 平台连接列表
    """
    try:
        user_id = current_user["id"]
        
        stmt = select(PlatformConnection).where(
            PlatformConnection.user_id == user_id
        ).order_by(PlatformConnection.updated_at.desc())
        
        result = await db.execute(stmt)
        connections = result.scalars().all()
        
        return connections
        
    except Exception as e:
        logger.error(f"Failed to get connections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connections/{connection_id}")
async def delete_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    删除平台连接
    
    Args:
        connection_id: 连接 ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        成功消息
    """
    try:
        user_id = current_user["id"]
        
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(status_code=404, detail="连接不存在")
        
        await db.delete(connection)
        await db.commit()
        
        logger.info(f"Deleted connection: {connection_id}")
        return {"message": "连接已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))
