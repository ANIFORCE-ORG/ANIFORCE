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
from datetime import datetime, timedelta
import httpx
from loguru import logger

from app.adapters import MetaAdsAdapter
from app.config.settings import get_settings
from app.config.database import get_db
from app.models import PlatformConnection
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
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SubAccountRequest(BaseModel):
    """子账号请求"""
    name: str
    customer_id: str


class SubAccountResponse(BaseModel):
    """子账号响应"""
    id: str
    name: str
    customer_id: str
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
        
        # 构建 scope 字符串（添加 https://www.googleapis.com/auth/ 前缀）
        scope_prefix = "https://www.googleapis.com/auth/"
        scopes = [f"{scope_prefix}{scope}" for scope in connection.scopes]
        scope_str = " ".join(scopes)
        
        # 构建 Google OAuth 授权 URL
        redirect_uri = f"{settings.BACKEND_BASE_URL}/api/v1/platform-auth/google/auth_callback"
        authorize_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?response_type=code"
            f"&client_id={connection.account_id}"
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
                        "client_id": connection.account_id,
                        "client_secret": connection.account_secret,
                        "redirect_uri": f"{settings.BACKEND_BASE_URL}/api/v1/platform-auth/meta/auth_callback",
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
                        "client_id": connection.account_id,
                        "client_secret": connection.account_secret,
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
        
        # 更新连接信息
        connection.access_token = token_data.get("access_token")
        connection.token_type = token_data.get("token_type", "bearer")
        
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
        logger.info(f"Updated connection with access token: {connection_id}")
        
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


@router.get("/meta/authorize_url/{connection_id}")
async def get_meta_authorize_url(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取 Meta OAuth 授权 URL（供前端使用）
    
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
        scopes = ",".join(connection.scopes or [])
        auth_url = (
            f"https://www.facebook.com/v25.0/dialog/oauth?"
            f"client_id={connection.account_id}&"
            f"redirect_uri={settings.BACKEND_BASE_URL}/api/v1/platform-auth/meta/auth_callback&"
            f"scope={scopes}&"
            f"response_type=code&"
            f"state={connection_id}"
        )

        logger.info(f"Generated Google authorize URL for connection: {connection_id}, authroize_url: {auth_url}")
        
        return {"authorize_url": auth_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get authorize URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                customer_id=binding.customer_id,
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
            customer_id=request.customer_id,
            status="active"
        )
        
        db.add(new_binding)
        await db.commit()
        await db.refresh(new_binding)
        
        logger.info(f"Added sub account {new_binding.id} for connection {connection_id}")
        
        return SubAccountResponse(
            id=new_binding.id,
            name=new_binding.sub_account_name,
            customer_id=new_binding.customer_id,
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
