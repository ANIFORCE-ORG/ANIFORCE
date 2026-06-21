"""
平台账号授权 API
处理 OAuth 认证和账号管理
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import asyncio
import httpx
from loguru import logger
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.user import User
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError

from app.adapters import MetaAdsAdapter
from app.config.settings import get_settings
from app.config.database import get_db
from app.models import PlatformConnection
from app.models.sub_account_binding import SubAccountBinding
from app.api.deps import get_current_user

router = APIRouter(prefix="/platform-auth", tags=["platform-auth"])
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


class GoogleConfigRequest(BaseModel):
    """Google 配置请求"""
    account_name: str
    client_id: str
    client_secret: Optional[str] = None
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
    token_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SubAccountRequest(BaseModel):
    """子账号请求"""
    name: str
    sub_account_id: str
    bm_customer_id: Optional[str] = None


class SubAccountResponse(BaseModel):
    """子账号响应"""
    id: str
    name: str
    sub_account_id: str
    bm_customer_id: Optional[str] = None
    status: str
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== API 路由 ====================
# 注意：平台配置现在通过数据库 PlatformConnection 模型管理
# 每个用户可以配置多个平台账号，配置存储在数据库中而非全局 settings


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


@router.post("/google/config", response_model=PlatformConnectionResponse)
async def save_google_config(
    config: GoogleConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    保存 Google 平台配置
    
    Args:
        config: Google 配置信息
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
            
            # 检查 Client ID 是否与其他记录冲突（排除当前记录）
            if existing.account_id != config.client_id:
                conflict_stmt = select(PlatformConnection).where(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.platform == "Google",
                    PlatformConnection.account_id == config.client_id,
                    PlatformConnection.id != config.connection_id
                )
                conflict_result = await db.execute(conflict_stmt)
                conflict = conflict_result.scalar_one_or_none()
                
                if conflict:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Client ID 已存在，与账户「{conflict.account_name or conflict.account_id}」冲突"
                    )
            
            # 更新配置
            existing.account_name = config.account_name
            existing.account_id = config.client_id
            # 只在提供了 client_secret 时才更新
            if config.client_secret:
                existing.account_secret = config.client_secret
            existing.scopes = config.scopes
            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            logger.info(f"Updated Google config for user: {user_id}, connection: {config.connection_id}")
            return existing
        
        # 新建模式：检查 Client ID 是否已存在
        conflict_stmt = select(PlatformConnection).where(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == "Google",
            PlatformConnection.account_id == config.client_id
        )
        conflict_result = await db.execute(conflict_stmt)
        conflict = conflict_result.scalar_one_or_none()
        
        if conflict:
            raise HTTPException(
                status_code=409,
                detail=f"Client ID 已存在，与账户「{conflict.account_name or conflict.account_id}」冲突"
            )
        
        # 创建新配置
        if not config.client_secret:
            raise HTTPException(status_code=400, detail="创建新配置时 Client Secret 不能为空")
        
        new_connection = PlatformConnection(
            user_id=user_id,
            platform="Google",
            account_id=config.client_id,
            account_name=config.account_name,
            account_secret=config.client_secret,
            access_token="",  # 暂时为空，等待 OAuth 授权
            scopes=config.scopes,
            status="unauthorized"
        )
        db.add(new_connection)
        await db.commit()
        await db.refresh(new_connection)
        logger.info(f"Created Google config for user: {user_id}")
        return new_connection
            
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save Google config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/google/config", response_model=Optional[PlatformConnectionResponse])
async def get_google_config(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取 Google 平台配置
    
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
            PlatformConnection.platform == "Google"
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        return connection
        
    except Exception as e:
        logger.error(f"Failed to get Google config: {e}")
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
        
        # 查询连接
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(status_code=404, detail="连接不存在")
        
        # 删除连接
        await db.delete(connection)
        await db.commit()
        logger.info(f"Deleted connection: {connection_id} for user: {user_id}")
        
        return {"message": "连接已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Meta OAuth API ====================

@router.post("/meta/start_oauth")
async def start_meta_oauth(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    直接启动 Meta OAuth 流程（自动创建 connection 并返回授权 URL）
    
    Args:
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        包含授权 URL 和 connection_id 的字典
    """
    try:
        user_id = current_user["id"]
        
        # 自动创建一个新的 connection 记录
        # account_id 和 account_secret 留空，避免在数据库中暴露平台核心信息
        # 实际使用时从 settings 中获取
        new_connection = PlatformConnection(
            user_id=user_id,
            platform="Meta",
            account_id="",  # 留空，不存储敏感信息
            account_name="Meta 广告账户",  # 默认名称
            account_secret="",  # 留空，不存储敏感信息
            access_token="",  # 暂时为空，等待 OAuth 授权
            scopes=settings.META_SCOPES.split(","),  # 从 settings 获取 scopes
            status="unauthorized"
        )
        db.add(new_connection)
        await db.commit()
        await db.refresh(new_connection)
        
        logger.info(f"Created new Meta connection for user: {user_id}, connection_id: {new_connection.id}")
        
        # 构建 OAuth 授权 URL
        scopes = settings.META_SCOPES
        auth_url = (
            f"https://www.facebook.com/v25.0/dialog/oauth?"
            f"client_id={settings.META_APP_ID}&"
            f"redirect_uri={settings.OAUTH_REDIRECT_BASE_URL}/api/v1/platform-auth/meta/auth_callback&"
            f"scope={scopes}&"
            f"response_type=code&"
            f"state={new_connection.id}"
        )
        
        logger.info(f"Generated Meta authorize URL for new connection: {new_connection.id}, authorize_url: {auth_url}")
        
        return {
            "authorize_url": auth_url,
            "connection_id": new_connection.id
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to start Meta OAuth: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/meta/authorize_url/{connection_id}")
async def get_meta_authorize_url(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取 Meta OAuth 授权 URL（供前端使用，用于重新授权）
    
    Args:
        connection_id: 连接 ID
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        授权 URL
    """
    try:
        user_id = current_user["id"]
        
        # 查询连接
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(status_code=404, detail="连接不存在")
        
        # 构建 OAuth 授权 URL
        # 使用 settings 中配置的 scopes
        scopes = settings.META_SCOPES
        auth_url = (
            f"https://www.facebook.com/v25.0/dialog/oauth?"
            f"client_id={settings.META_APP_ID}&"
            f"redirect_uri={settings.OAUTH_REDIRECT_BASE_URL}/api/v1/platform-auth/meta/auth_callback&"
            f"scope={scopes}&"
            f"response_type=code&"
            f"state={connection_id}"
        )

        logger.info(f"Generated Meta authorize URL for connection: {connection_id}, authroize_url: {auth_url}")
        
        return {"authorize_url": auth_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get authorize URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta/auth_callback")
async def meta_auth_callback(
    code: Optional[str] = Query(None, description="OAuth 授权码"),
    state: Optional[str] = Query(None, description="状态参数"),
    db: AsyncSession = Depends(get_db)
):
    """
    Meta OAuth 授权回调接口
    
    Args:
        code: OAuth 授权码
        state: 状态参数（包含 connection_id）
        db: 数据库会话
    
    Returns:
        重定向到前端页面
    """
    logger.info(f"Meta auth callback received: code={code[:10] if code else 'None'}, state={state}")
    
    # 验证必需参数
    if not code:
        logger.error("Missing required parameter: code")
        return RedirectResponse(
            url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=missing_code"
        )
    
    if not state:
        logger.error("Missing required parameter: state")
        return RedirectResponse(
            url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=missing_state"
        )
    
    try:
        connection_id = state
        logger.info(f"Received OAuth callback for connection: {connection_id}, code: {code[:10]}...")
        
        # 查询连接信息
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            logger.error(f"Connection not found: {connection_id}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=connection_not_found"
            )
        
        # 使用 code 换取 access_token
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            try:
                logger.info(f"Requesting access token from Facebook API for connection: {connection_id}")
                token_response = await client.get(
                    "https://graph.facebook.com/v25.0/oauth/access_token",
                    params={
                        "client_id": settings.META_APP_ID,
                        "client_secret": settings.META_APP_SECRET,
                        "redirect_uri": f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/platform-auth/meta/auth_callback",
                        "code": code
                    }
                )
                
                if token_response.status_code != 200:
                    logger.error(f"Failed to get access token: status={token_response.status_code}, response={token_response.text}")
                    return RedirectResponse(
                        url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=token_exchange_failed"
                    )
                
                token_data = token_response.json()
                short_lived_token = token_data.get("access_token")
                logger.info(f"Got short-lived access token for connection: {connection_id}, token: {short_lived_token[:20] if short_lived_token else 'None'}, expires_in: {token_data.get('expires_in')} seconds")
                
            except httpx.TimeoutException as e:
                logger.error(f"Timeout while getting access token: {e}")
                return RedirectResponse(
                    url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=token_timeout"
                )
            except httpx.ConnectError as e:
                logger.error(f"Connection error while getting access token: {e}")
                return RedirectResponse(
                    url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=connection_error"
                )
            except Exception as e:
                logger.error(f"Unexpected error while getting access token: {e}", exc_info=True)
                return RedirectResponse(
                    url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=token_exchange_failed"
                )
            
            # 将短期 token 转换为长期 token（60天有效期）
            try:
                logger.info(f"Converting to long-lived token for connection: {connection_id}")
                long_token_response = await client.get(
                    "https://graph.facebook.com/v25.0/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": settings.META_APP_ID,
                        "client_secret": settings.META_APP_SECRET,
                        "fb_exchange_token": short_lived_token
                    }
                )
                
                if long_token_response.status_code == 200:
                    long_token_data = long_token_response.json()
                    token_data = long_token_data
                    logger.info(f"Successfully converted to long-lived token for connection: {connection_id}, expires_in: {long_token_data.get('expires_in')} seconds (~{long_token_data.get('expires_in', 0) // 86400} days)")
                else:
                    logger.warning(f"Failed to get long-lived token: status={long_token_response.status_code}, response={long_token_response.text}, using short-lived token instead")
            except httpx.TimeoutException as e:
                logger.warning(f"Timeout during long-lived token conversion: {e}, using short-lived token instead")
            except Exception as e:
                logger.warning(f"Exception during long-lived token conversion: {e}, using short-lived token instead")
        
        # 获取访问令牌
        access_token = token_data.get("access_token")
        
        # 使用 access_token 调用 Meta API 获取账户信息
        account_id = ""
        account_name = ""
        try:
            logger.info(f"Fetching account info from Meta API for connection: {connection_id}")
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                me_response = await client.get(
                    "https://graph.facebook.com/v25.0/me",
                    params={
                        "fields": "id,name",
                        "access_token": access_token
                    }
                )
                
                if me_response.status_code == 200:
                    me_data = me_response.json()
                    account_id = me_data.get("id", "")
                    account_name = me_data.get("name", "")
                    logger.info(f"Successfully fetched account info: id={account_id}, name={account_name}")
                else:
                    logger.warning(f"Failed to fetch account info: status={me_response.status_code}, response={me_response.text}")
        except Exception as e:
            logger.warning(f"Exception while fetching account info: {e}, will leave account_id and account_name empty")
        
        # 更新连接信息
        connection.access_token = access_token
        connection.token_type = token_data.get("token_type", "bearer")
        connection.account_id = account_id  # 更新账户ID
        connection.account_name = account_name if account_name else "Meta 广告账户"  # 更新账户名称
        
        # 计算过期时间
        expires_in = token_data.get("expires_in")
        if expires_in:
            connection.token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
            logger.info(f"Token will expire at: {connection.token_expires_at} UTC")
        
        # 更新状态和同步时间
        connection.status = "active"
        connection.last_sync_at = datetime.utcnow()
        connection.updated_at = datetime.utcnow()
        
        await db.commit()
        logger.info(f"Updated connection with access token and account info: {connection_id}, account_id={account_id}, account_name={account_name}")
        
        # 重定向到前端页面
        return RedirectResponse(
            url=f"{settings.FRONTEND_BASE_URL}/platform-connections?success=authorized"
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        logger.error(f"Exception type: {type(e).__name__}, Exception details: {str(e)}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=callback_failed"
        )


# ==================== Google OAuth API ====================

@router.post("/google/start_oauth")
async def start_google_oauth(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    直接启动 Google OAuth 流程（自动创建 connection 并返回授权 URL）
    
    Args:
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        包含授权 URL 和 connection_id 的字典
    """
    try:
        user_id = current_user["id"]
        
        # 自动创建一个新的 connection 记录
        # account_id 和 account_secret 留空，避免在数据库中暴露平台核心信息
        # 实际使用时从 settings 中获取
        new_connection = PlatformConnection(
            user_id=user_id,
            platform="Google",
            account_id="",  # 留空，不存储敏感信息
            account_name="Google 广告账户",  # 默认名称
            account_secret="",  # 留空，不存储敏感信息
            access_token="",  # 暂时为空，等待 OAuth 授权
            scopes=[settings.GOOGLE_SCOPES],  # 从 settings 获取 scopes
            status="unauthorized"
        )
        db.add(new_connection)
        await db.commit()
        await db.refresh(new_connection)
        
        logger.info(f"Created new Google connection for user: {user_id}, connection_id: {new_connection.id}")
        
        # 构建 OAuth 授权 URL
        # 将逗号分隔的 scopes 转换为空格分隔（Google OAuth 要求）
        scopes = settings.GOOGLE_SCOPES.replace(",", "%20")
        redirect_uri = f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/platform-auth/google/auth_callback"
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?response_type=code"
            f"&client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
            f"&access_type=offline"
            f"&prompt=consent"
            f"&state={new_connection.id}"
        )
        
        logger.info(f"Generated Google authorize URL for new connection: {new_connection.id}, authorize_url: {auth_url}")
        
        return {
            "authorize_url": auth_url,
            "connection_id": new_connection.id
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to start Google OAuth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/google/authorize_url/{connection_id}")
async def get_google_authorize_url(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取 Google OAuth 授权 URL
    
    Args:
        connection_id: 连接 ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        包含授权 URL 的字典
    """
    try:
        user_id = current_user["id"]
        
        # 查询连接
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == "Google"
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(status_code=404, detail="连接不存在")
        
        # 使用 settings 中配置的 scopes
        scope_str = settings.GOOGLE_SCOPES.replace(",", "%20")
        
        # 构建 Google OAuth 授权 URL
        redirect_uri = f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/platform-auth/google/auth_callback"
        authorize_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?response_type=code"
            f"&client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope_str}"
            f"&access_type=offline"
            f"&prompt=consent"
            f"&state={connection_id}"
        )
        
        logger.info(f"Generated Google authorize URL for connection: {connection_id}, authroize_url: {authorize_url}")
        return {"authorize_url": authorize_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate Google authorize URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/google/auth_callback")
async def google_auth_callback(
    code: Optional[str] = Query(None, description="OAuth 授权码"),
    state: Optional[str] = Query(None, description="状态参数"),
    error: Optional[str] = Query(None, description="错误信息"),
    db: AsyncSession = Depends(get_db)
):
    """
    Google OAuth 授权回调接口
    
    Args:
        code: OAuth 授权码
        state: 状态参数（包含 connection_id）
        error: 错误信息（用户拒绝授权时返回）
        db: 数据库会话
    
    Returns:
        重定向到前端页面
    """
    logger.info(f"Google auth callback received: code={code[:10] if code else 'None'}, state={state}, error={error}")
    
    # 检查用户是否拒绝授权
    if error:
        logger.warning(f"User denied authorization: {error}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=user_denied"
        )
    
    # 验证必需参数
    if not code:
        logger.error("Missing required parameter: code")
        return RedirectResponse(
            url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=missing_code"
        )
    
    if not state:
        logger.error("Missing required parameter: state")
        return RedirectResponse(
            url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=missing_state"
        )
    
    try:
        connection_id = state
        logger.info(f"Received Google OAuth callback for connection: {connection_id}, code: {code[:10]}...")
        
        # 查询连接信息
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            logger.error(f"Connection not found: {connection_id}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=connection_not_found"
            )
        
        # 使用 code 换取 access_token
        redirect_uri = f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/platform-auth/google/auth_callback"
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            try:
                logger.info(f"Requesting access token from Google API for connection: {connection_id}")
                token_response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code"
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                )
                
                if token_response.status_code != 200:
                    logger.error(f"Failed to get access token: status={token_response.status_code}, response={token_response.text}")
                    return RedirectResponse(
                        url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=token_exchange_failed"
                    )
                
                token_data = token_response.json()
                access_token = token_data.get("access_token")
                refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in")
                
                logger.info(f"Got access token for connection: {connection_id}, token: {access_token[:20] if access_token else 'None'}, expires_in: {expires_in} seconds")
                
                if refresh_token:
                    logger.info(f"Got refresh token for connection: {connection_id}, refresh_token: {refresh_token[:20]}...")
                
                # 使用 Google SDK 获取用户信息（openid 和 name）
                logger.info(f"Fetching user info via Google SDK for connection: {connection_id}")
                try:
                    credentials = Credentials(token=access_token)
                    
                    def _fetch_userinfo():
                        service = build('oauth2', 'v2', credentials=credentials)
                        return service.userinfo().get().execute()
                    
                    userinfo = await asyncio.to_thread(_fetch_userinfo)
                    account_id = userinfo.get("id", "")  # Google user ID (openid)
                    account_name = userinfo.get("name", "Google 广告账户")
                    account_email = userinfo.get("email", "")
                    
                    logger.info(f"Got user info via SDK: id={account_id}, name={account_name}, email={account_email}")
                except HttpError as e:
                    logger.error(f"Google SDK HTTP error fetching user info: {e.status_code} - {e.reason}, using default values")
                    account_id = ""
                    account_name = "Google 广告账户"
                except Exception as e:
                    logger.error(f"Error fetching user info via SDK: {e}, using default values")
                    account_id = ""
                    account_name = "Google 广告账户"
                
            except httpx.TimeoutException as e:
                logger.error(f"Timeout while getting access token: {e}")
                return RedirectResponse(
                    url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=token_timeout"
                )
            except httpx.ConnectError as e:
                logger.error(f"Connection error while getting access token: {e}")
                return RedirectResponse(
                    url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=connection_error"
                )
            except Exception as e:
                logger.error(f"Unexpected error while getting access token: {e}", exc_info=True)
                return RedirectResponse(
                    url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=token_exchange_failed"
                )
        
        # 更新连接信息
        connection.access_token = access_token
        connection.refresh_token = refresh_token
        connection.token_type = token_data.get("token_type", "Bearer")
        connection.account_id = account_id  # 更新为真实的 Google user ID
        connection.account_name = account_name  # 更新为真实的用户名
        
        # 计算过期时间
        if expires_in:
            connection.token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
            logger.info(f"Token will expire at: {connection.token_expires_at} UTC")
        
        # 更新状态和同步时间
        connection.status = "active"
        connection.last_sync_at = datetime.utcnow()
        connection.updated_at = datetime.utcnow()
        
        await db.commit()
        logger.info(f"Updated connection with access token: {connection_id}")
        
        # 重定向到前端页面
        return RedirectResponse(
            url=f"{settings.FRONTEND_BASE_URL}/platform-connections?success=authorized"
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Google OAuth callback failed: {e}", exc_info=True)
        logger.error(f"Exception type: {type(e).__name__}, Exception details: {str(e)}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_BASE_URL}/platform-connections?error=callback_failed"
        )


# ==================== 子账号管理 API（使用独立表） ====================

@router.get("/google/{connection_id}/sub-accounts", response_model=List[SubAccountResponse])
async def get_sub_accounts(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取 Google 账户的子账号列表
    从 sub_account_bindings 表查询
    """
    try:
        user_id = current_user["id"]
        
        # 验证连接是否存在且属于当前用户
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(status_code=404, detail="连接不存在")
        
        # 从 SubAccountBinding 表查询子账号
        from app.models import SubAccountBinding
        stmt = select(SubAccountBinding).where(
            SubAccountBinding.parent_connection_id == connection_id
        ).order_by(SubAccountBinding.created_at.desc())
        
        result = await db.execute(stmt)
        bindings = result.scalars().all()
        
        logger.info(f"Found {len(bindings)} sub accounts for connection {connection_id}")
        
        # 转换为响应格式
        return [
            SubAccountResponse(
                id=binding.id,
                name=binding.sub_account_name,
                sub_account_id=binding.sub_account_id,
                bm_customer_id=binding.bm_customer_id,
                status=binding.status,
                updated_at=binding.updated_at
            )
            for binding in bindings
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sub accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google/{connection_id}/sub-accounts", response_model=SubAccountResponse)
async def add_sub_account(
    connection_id: str,
    request: SubAccountRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    添加 Google 子账号
    保存到 sub_account_bindings 表
    """
    try:
        user_id = current_user["id"]
        
        # 验证连接是否存在且属于当前用户
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(status_code=404, detail="连接不存在")
        
        # 创建新的子账号绑定
        from app.models import SubAccountBinding
        new_binding = SubAccountBinding(
            parent_connection_id=connection_id,
            sub_account_name=request.name,
            sub_account_id=request.sub_account_id,
            bm_customer_id=request.bm_customer_id,
            status="active"
        )
        
        db.add(new_binding)
        await db.commit()
        await db.refresh(new_binding)
        
        logger.info(f"Added sub account {new_binding.id} for connection {connection_id}")
        
        return SubAccountResponse(
            id=new_binding.id,
            name=new_binding.sub_account_name,
            sub_account_id=new_binding.sub_account_id,
            bm_customer_id=new_binding.bm_customer_id,
            status=new_binding.status,
            updated_at=new_binding.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add sub account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/google/{connection_id}/sub-accounts/{sub_account_id}")
async def delete_sub_account(
    connection_id: str,
    sub_account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    删除 Google 子账号
    从 sub_account_bindings 表删除
    """
    try:
        user_id = current_user["id"]
        
        # 验证连接是否存在且属于当前用户
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(status_code=404, detail="连接不存在")
        
        # 查找并删除子账号
        from app.models import SubAccountBinding
        stmt = select(SubAccountBinding).where(
            SubAccountBinding.id == sub_account_id,
            SubAccountBinding.parent_connection_id == connection_id
        )
        result = await db.execute(stmt)
        binding = result.scalar_one_or_none()
        
        if not binding:
            raise HTTPException(status_code=404, detail="子账号不存在")
        
        await db.delete(binding)
        await db.commit()
        
        logger.info(f"Deleted sub account {sub_account_id} from connection {connection_id}")
        
        return {"message": "子账号已删除", "sub_account_id": sub_account_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete sub account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/meta/{connection_id}/sync-adaccounts")
async def sync_meta_ad_accounts(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    同步 Meta 广告账户
    使用 Facebook Business SDK 获取 adaccounts 并写入 sub_account_bindings
    """
    try:
        user_id = current_user["id"]
        
        # 验证连接是否存在且属于当前用户
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(status_code=404, detail="连接不存在")
        
        if connection.platform != "Meta":
            raise HTTPException(status_code=400, detail="只支持 Meta 平台")
        
        if connection.status != "active":
            raise HTTPException(status_code=400, detail="连接未授权，请先完成授权")
        
        # 使用 Facebook Business SDK 获取广告账户
        access_token = connection.access_token
        
        # 从配置中获取 Meta App 信息
        meta_app_id = settings.META_APP_ID
        meta_app_secret = settings.META_APP_SECRET
        
        if not meta_app_id or not meta_app_secret:
            logger.error("Meta App ID or App Secret not configured")
            raise HTTPException(status_code=500, detail="Meta 应用配置缺失")
        
        try:
            logger.info(f"Fetching ad accounts from Meta API for connection: {connection_id}")
            
            # 初始化 Facebook Ads API
            FacebookAdsApi.init(
                app_id=meta_app_id,
                app_secret=meta_app_secret,
                access_token=access_token
            )
            
            # 获取当前用户
            me = User(fbid='me')
            
            # 获取用户的广告账户
            ad_accounts = me.get_ad_accounts(fields=[
                AdAccount.Field.id,
                AdAccount.Field.name,
                AdAccount.Field.account_id,
                AdAccount.Field.account_status,
                AdAccount.Field.currency,
                AdAccount.Field.timezone_name,
                AdAccount.Field.business,
            ])
            
            # 转换为列表（SDK 返回的是迭代器）
            accounts_list = list(ad_accounts)
            
            logger.info(f"Fetched {len(accounts_list)} ad accounts from Meta API")
            
            # 状态映射
            status_mapping = {
                1: "active",        # 正常可投放
                2: "disabled",      # 被封/禁用
                3: "pending_review", # 待审核
                7: "payment_required", # 需充值/付款
                9: "suspended"      # 暂停
            }
            
            # 删除现有的子账号绑定（重新同步）
            stmt = select(SubAccountBinding).where(
                SubAccountBinding.parent_connection_id == connection_id
            )
            result = await db.execute(stmt)
            existing_bindings = result.scalars().all()
            for binding in existing_bindings:
                await db.delete(binding)
            
            # 创建新的子账号绑定
            synced_count = 0
            for ad_account in accounts_list:
                account_id = ad_account.get('id', '')
                account_name = ad_account.get('name', '')
                account_status = ad_account.get('account_status')
                
                # 映射状态（SDK 返回的是整数）
                mapped_status = status_mapping.get(account_status, "unknown")
                
                # 创建子账号绑定
                binding = SubAccountBinding(
                    parent_connection_id=connection_id,
                    sub_account_name=account_name,
                    sub_account_id=account_id,
                    status=mapped_status
                )
                db.add(binding)
                synced_count += 1
                
                logger.info(f"Synced ad account: id={account_id}, name={account_name}, status={mapped_status}")
            
            await db.commit()
            
            logger.info(f"Successfully synced {synced_count} ad accounts for connection: {connection_id}")
            
            return {
                "message": f"成功同步 {synced_count} 个广告账户",
                "synced_count": synced_count
            }
            
        except FacebookRequestError as e:
            logger.error(f"Facebook API error: code={e.api_error_code()}, type={e.api_error_type()}, message={e.api_error_message()}")
            
            error_code = e.api_error_code()
            if error_code == 190:
                raise HTTPException(status_code=401, detail="Access Token 无效或已过期，请重新授权")
            elif error_code == 200:
                raise HTTPException(status_code=403, detail="缺少必要权限，请确保已授予 ads_read 权限")
            else:
                raise HTTPException(status_code=500, detail=f"Meta API 错误: {e.api_error_message()}")
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to sync ad accounts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google/{connection_id}/sync-adaccounts")
async def sync_google_ads_accounts(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    同步 Google Ads 广告账户
    使用 Google Ads SDK 获取 MCC 账户及其子账号并写入 sub_account_bindings
    """
    try:
        user_id = current_user["id"]
        
        # 验证连接是否存在且属于当前用户
        stmt = select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(status_code=404, detail="连接不存在")
        
        if connection.platform != "Google":
            raise HTTPException(status_code=400, detail="只支持 Google 平台")
        
        if connection.status != "active":
            raise HTTPException(status_code=400, detail="连接未授权，请先完成授权")
        
        # 获取 refresh_token 和 developer_token
        refresh_token = connection.refresh_token
        if not refresh_token:
            raise HTTPException(status_code=400, detail="缺少 refresh_token")
        
        developer_token = settings.GOOGLE_DEVELOPER_TOKEN
        if not developer_token:
            raise HTTPException(status_code=500, detail="服务器未配置 GOOGLE_DEVELOPER_TOKEN")
        
        # 使用 Google Ads SDK 获取可访问的客户账户
        def _get_google_ads_accounts():
            """同步函数：获取 Google Ads 账户"""
            credentials_dict = {
                "developer_token": developer_token,
                "use_proto_plus": True,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
            }
            
            # 初始化客户端
            client = GoogleAdsClient.load_from_dict(credentials_dict, version="v24")
            
            # 获取可访问的客户账户
            customer_service = client.get_service("CustomerService")
            accessible_customers = customer_service.list_accessible_customers()
            
            customer_ids = [
                resource_name.split('/')[-1] 
                for resource_name in accessible_customers.resource_names
            ]
            
            logger.info(f"Found {len(customer_ids)} accessible customer accounts")
            
            # 对每个 MCC 账户，获取其子账号
            all_sub_accounts = []
            
            for customer_id in customer_ids:
                try:
                    # 为每个 customer_id 创建新的客户端配置
                    credentials_dict_with_login = {
                        "developer_token": developer_token,
                        "use_proto_plus": True,
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "login_customer_id": customer_id,
                    }
                    
                    client_with_login = GoogleAdsClient.load_from_dict(credentials_dict_with_login, version="v24")
                    ga_service = client_with_login.get_service("GoogleAdsService")
                    
                    # 查询子账号
                    query = """
                        SELECT
                            customer_client.client_customer,
                            customer_client.level,
                            customer_client.manager,
                            customer_client.descriptive_name,
                            customer_client.currency_code,
                            customer_client.time_zone,
                            customer_client.id
                        FROM customer_client
                        WHERE customer_client.level <= 1
                    """
                    
                    response = ga_service.search(customer_id=customer_id, query=query)
                    
                    for row in response:
                        customer_client = row.customer_client
                        all_sub_accounts.append({
                            "sub_account_id": str(customer_client.id),
                            "sub_account_name": customer_client.descriptive_name,
                            "bm_customer_id": customer_id,  # MCC ID
                            "level": customer_client.level,
                            "manager": customer_client.manager,
                            "currency_code": customer_client.currency_code,
                            "time_zone": customer_client.time_zone,
                        })
                    
                    logger.info(f"Found sub-accounts under MCC {customer_id}")
                    
                except GoogleAdsException as ex:
                    logger.warning(f"Failed to query sub-accounts for customer {customer_id}: {ex.failure}")
                    continue
                except Exception as e:
                    logger.warning(f"Error querying customer {customer_id}: {e}")
                    continue
            
            return all_sub_accounts
        
        # 在线程中执行同步调用
        logger.info(f"Starting Google Ads sync for connection: {connection_id}")
        sub_accounts = await asyncio.to_thread(_get_google_ads_accounts)
        
        logger.info(f"Retrieved {len(sub_accounts)} total sub-accounts from Google Ads API")
        
        # 删除现有的子账号绑定（重新同步）
        stmt = select(SubAccountBinding).where(
            SubAccountBinding.parent_connection_id == connection_id
        )
        result = await db.execute(stmt)
        existing_bindings = result.scalars().all()
        for binding in existing_bindings:
            await db.delete(binding)
        
        # 创建新的子账号绑定
        synced_count = 0
        for account in sub_accounts:
            binding = SubAccountBinding(
                parent_connection_id=connection_id,
                sub_account_name=account["sub_account_name"],
                sub_account_id=account["sub_account_id"],
                bm_customer_id=account["bm_customer_id"],
                status="active"
            )
            db.add(binding)
            synced_count += 1
            
            logger.info(f"Synced Google Ads account: id={account['sub_account_id']}, name={account['sub_account_name']}, mcc={account['bm_customer_id']}")
        
        await db.commit()
        
        logger.info(f"Successfully synced {synced_count} Google Ads accounts for connection: {connection_id}")
        
        return {
            "message": f"成功同步 {synced_count} 个广告账户",
            "synced_count": synced_count
        }
        
    except HTTPException:
        raise
    except GoogleAdsException as ex:
        await db.rollback()
        logger.error(f"Google Ads API error: {ex.failure}")
        raise HTTPException(status_code=500, detail=f"Google Ads API 错误: {ex.failure.errors[0].message if ex.failure.errors else str(ex)}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to sync Google Ads accounts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 广告账户查询 API ====================

class AdAccountOption(BaseModel):
    """广告账户选项"""
    account_id: str
    account_name: str
    channel: str
    
    class Config:
        from_attributes = True


@router.get("/ad-accounts", response_model=List[AdAccountOption])
async def get_ad_accounts(
    channel: str = Query(..., description="投放渠道: Meta, Google, TikTok"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取指定渠道的广告账户列表
    从 sub_account_bindings 表查询当前用户可用的广告账户
    
    安全性：通过JWT token验证用户身份，只返回当前用户的广告账户
    
    Args:
        channel: 投放渠道 (Meta, Google, TikTok)
        db: 数据库会话
        current_user: 当前用户（从JWT token中提取）
        
    Returns:
        List[AdAccountOption]: 广告账户列表
    """
    try:
        user_id = current_user["id"]
        logger.info(f"Fetching ad accounts for user: {user_id}, channel: {channel}")
        
        # 查询该用户在指定平台的所有连接
        stmt = select(PlatformConnection).where(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == channel,
            PlatformConnection.status == "active"
        )
        result = await db.execute(stmt)
        connections = result.scalars().all()
        
        if not connections:
            logger.warning(f"No active {channel} connections found for user: {user_id}. User may need to configure platform connection first.")
            return []
        
        logger.info(f"Found {len(connections)} active {channel} connection(s) for user: {user_id}")
        
        # 获取所有连接的 ID
        connection_ids = [conn.id for conn in connections]
        
        # 从 sub_account_bindings 表查询所有子账户
        stmt = select(SubAccountBinding).where(
            SubAccountBinding.parent_connection_id.in_(connection_ids),
            SubAccountBinding.status == "active"
        ).order_by(SubAccountBinding.sub_account_name)
        
        result = await db.execute(stmt)
        bindings = result.scalars().all()
        
        if not bindings:
            logger.warning(f"No sub-accounts found for user: {user_id}, channel: {channel}. User may need to sync ad accounts first.")
        
        # 转换为响应格式
        accounts = [
            AdAccountOption(
                account_id=binding.sub_account_id,
                account_name=binding.sub_account_name,
                channel=channel
            )
            for binding in bindings
        ]
        
        logger.info(f"Successfully fetched {len(accounts)} {channel} ad accounts for user: {user_id}")
        return accounts
        
    except Exception as e:
        logger.error(f"Failed to get ad accounts for user: {current_user.get('id', 'unknown')}, channel: {channel}, error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取广告账户失败: {str(e)}")
