"""
Meta Marketing API 接口
用于获取 Meta 平台的广告相关数据（Pages、Applications、Images、Videos）
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import httpx
from loguru import logger

from app.config.settings import get_settings
from app.config.database import get_db
from app.models import PlatformConnection
from app.api.deps import get_current_user

router = APIRouter()


# ==================== Response Models ====================

class ApplicationResponse(BaseModel):
    """Meta 应用响应模型"""
    id: str
    name: str
    namespace: Optional[str] = None
    object_store_urls: Optional[dict] = None
    supported_platforms: Optional[List[str]] = None
    app_type: Optional[str] = None
    link: Optional[str] = None


class FacebookPageResponse(BaseModel):
    """Facebook Page 响应模型"""
    id: str
    name: str
    category: Optional[str] = None
    tasks: Optional[List[str]] = None
    instagram_business_account: Optional[dict] = None
    has_advertise_permission: bool = False


class AdImageResponse(BaseModel):
    """Meta 广告图片响应模型"""
    id: str
    name: Optional[str] = None
    hash: str
    url: Optional[str] = None
    url_128: Optional[str] = None
    height: Optional[int] = None
    width: Optional[int] = None
    status: Optional[str] = None
    created_time: Optional[str] = None


class AdVideoResponse(BaseModel):
    """Meta 广告视频响应模型"""
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    length: Optional[float] = None
    picture: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    created_time: Optional[str] = None


# ==================== API Endpoints ====================

@router.get("/meta/{connection_id}/pages")
async def get_meta_pages(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> List[FacebookPageResponse]:
    """
    获取用户可管理的 Facebook Pages
    用于广告创建时选择 Page
    
    Args:
        connection_id: 平台连接 ID
        
    Returns:
        Page 列表，包含 ID、名称、类别、权限等信息
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
        
        # 获取 access_token
        access_token = connection.access_token
        if not access_token:
            raise HTTPException(status_code=400, detail="缺少 access_token")
        
        # 调用 Meta Graph API 获取用户管理的 Pages
        async with httpx.AsyncClient() as client:
            url = "https://graph.facebook.com/v25.0/me/accounts"
            params = {
                'fields': 'id,name,category,tasks,instagram_business_account',
                'access_token': access_token
            }
            
            response = await client.get(url, params=params, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                pages_list = data.get('data', [])
                
                logger.info(f"Successfully fetched {len(pages_list)} pages for connection: {connection_id}")
                
                # 转换为响应格式，并标记是否有广告权限
                pages = [
                    FacebookPageResponse(
                        id=page.get('id'),
                        name=page.get('name'),
                        category=page.get('category'),
                        tasks=page.get('tasks', []),
                        instagram_business_account=page.get('instagram_business_account'),
                        has_advertise_permission='ADVERTISE' in page.get('tasks', [])
                    )
                    for page in pages_list
                ]
                
                return pages
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"Meta API error: {response.status_code}, message: {error_message}")
                
                if response.status_code == 401 or response.status_code == 190:
                    raise HTTPException(status_code=401, detail="Access Token 无效或已过期，请重新授权")
                elif response.status_code == 403:
                    raise HTTPException(status_code=403, detail="缺少必要权限，请确保已授予 pages_show_list 权限")
                else:
                    raise HTTPException(status_code=500, detail=f"Meta API 错误: {error_message}")
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch pages: connection_id={connection_id}, error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Pages 列表失败: {str(e)}")


@router.get("/meta/{connection_id}/adaccounts/{ad_account_id}/applications")
async def get_meta_applications(
    connection_id: str,
    ad_account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> List[ApplicationResponse]:
    """
    获取 Meta 广告账户可用的应用列表
    用于 App Promotion 广告创建
    
    Args:
        connection_id: 平台连接 ID
        ad_account_id: 广告账户 ID（带或不带 'act_' 前缀均可）
        
    Returns:
        应用列表，包含 ID、名称、平台、商店 URL 等信息
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
        
        # 获取 access_token
        access_token = connection.access_token
        if not access_token:
            raise HTTPException(status_code=400, detail="缺少 access_token")
        
        # 确保广告账户 ID 格式正确（带 'act_' 前缀）
        if not ad_account_id.startswith('act_'):
            ad_account_id = f'act_{ad_account_id}'
        
        # 调用 Meta Graph API 获取应用列表
        async with httpx.AsyncClient() as client:
            url = f"https://graph.facebook.com/v25.0/{ad_account_id}/applications"
            params = {
                'fields': 'id,name,namespace,object_store_urls,supported_platforms,app_type,link',
                'access_token': access_token
            }
            
            response = await client.get(url, params=params, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                applications = data.get('data', [])
                
                logger.info(f"Successfully fetched {len(applications)} applications for ad account: {ad_account_id}")
                
                return [
                    ApplicationResponse(
                        id=app.get('id'),
                        name=app.get('name'),
                        namespace=app.get('namespace'),
                        object_store_urls=app.get('object_store_urls'),
                        supported_platforms=app.get('supported_platforms'),
                        app_type=app.get('app_type'),
                        link=app.get('link')
                    )
                    for app in applications
                ]
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"Meta API error: {response.status_code}, message: {error_message}")
                
                if response.status_code == 401 or response.status_code == 190:
                    raise HTTPException(status_code=401, detail="Access Token 无效或已过期，请重新授权")
                elif response.status_code == 403 or response.status_code == 200:
                    raise HTTPException(status_code=403, detail="缺少必要权限，请确保已授予相关权限")
                else:
                    raise HTTPException(status_code=500, detail=f"Meta API 错误: {error_message}")
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch applications: connection_id={connection_id}, ad_account_id={ad_account_id}, error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取应用列表失败: {str(e)}")


@router.get("/meta/{connection_id}/adaccounts/{ad_account_id}/images")
async def get_meta_ad_images(
    connection_id: str,
    ad_account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> List[AdImageResponse]:
    """
    获取 Meta 广告账户的图片素材列表
    使用 Facebook Business SDK
    
    Args:
        connection_id: 平台连接 ID
        ad_account_id: 广告账户 ID
        
    Returns:
        图片素材列表，包含 ID、名称、hash、URL、缩略图等信息
    """
    try:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.adimage import AdImage
        from facebook_business.exceptions import FacebookRequestError
        
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
        
        # 获取 access_token 和 app credentials
        access_token = connection.access_token
        if not access_token:
            raise HTTPException(status_code=400, detail="缺少 access_token")
        
        # 从 settings 获取 app_id 和 app_secret
        settings = get_settings()
        app_id = settings.META_APP_ID
        app_secret = settings.META_APP_SECRET
        
        if not app_id or not app_secret:
            raise HTTPException(status_code=500, detail="Meta App 配置缺失")
        
        # 确保 ad_account_id 格式正确
        if not ad_account_id.startswith('act_'):
            ad_account_id = f'act_{ad_account_id}'
        
        # 初始化 Facebook Ads API
        FacebookAdsApi.init(
            app_id=app_id,
            app_secret=app_secret,
            access_token=access_token
        )
        
        # 获取广告账户对象
        account = AdAccount(ad_account_id)
        
        # 使用 SDK 获取图片素材列表
        images = account.get_ad_images(fields=[
            AdImage.Field.id,
            AdImage.Field.name,
            AdImage.Field.hash,
            AdImage.Field.url,
            AdImage.Field.url_128,
            AdImage.Field.permalink_url,
            AdImage.Field.height,
            AdImage.Field.width,
            AdImage.Field.created_time,
            AdImage.Field.updated_time,
            AdImage.Field.status,
        ])
        
        # 转换为列表
        images_list = list(images)
        
        logger.info(f"Successfully fetched {len(images_list)} images for ad_account: {ad_account_id}")
        
        # 转换为响应格式
        result_images = [
            AdImageResponse(
                id=img.get('id'),
                name=img.get('name'),
                hash=img.get('hash'),
                url=img.get('url'),
                url_128=img.get('url_128'),
                height=img.get('height'),
                width=img.get('width'),
                status=img.get('status'),
                created_time=img.get('created_time')
            )
            for img in images_list
        ]
        
        return result_images
        
    except FacebookRequestError as e:
        logger.error(f"Facebook API error: code={e.api_error_code()}, type={e.api_error_type()}, message={e.api_error_message()}")
        
        error_code = e.api_error_code()
        if error_code == 190 or error_code == 102:
            raise HTTPException(status_code=401, detail="Access Token 无效或已过期，请重新授权")
        elif error_code == 200 or error_code == 10:
            raise HTTPException(status_code=403, detail="缺少必要权限，请确保已授予 ads_read 权限")
        else:
            raise HTTPException(status_code=500, detail=f"Meta API 错误: {e.api_error_message()}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch images: connection_id={connection_id}, ad_account_id={ad_account_id}, error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取图片素材列表失败: {str(e)}")


@router.get("/meta/{connection_id}/adaccounts/{ad_account_id}/videos")
async def get_meta_ad_videos(
    connection_id: str,
    ad_account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> List[AdVideoResponse]:
    """
    获取 Meta 广告账户的视频素材列表
    使用 Facebook Business SDK
    
    Args:
        connection_id: 平台连接 ID
        ad_account_id: 广告账户 ID
        
    Returns:
        视频素材列表，包含 ID、标题、时长、封面图等信息
    """
    try:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.advideo import AdVideo
        from facebook_business.exceptions import FacebookRequestError
        
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
        
        # 获取 access_token 和 app credentials
        access_token = connection.access_token
        if not access_token:
            raise HTTPException(status_code=400, detail="缺少 access_token")
        
        # 从 settings 获取 app_id 和 app_secret
        settings = get_settings()
        app_id = settings.META_APP_ID
        app_secret = settings.META_APP_SECRET
        
        if not app_id or not app_secret:
            raise HTTPException(status_code=500, detail="Meta App 配置缺失")
        
        # 确保 ad_account_id 格式正确
        if not ad_account_id.startswith('act_'):
            ad_account_id = f'act_{ad_account_id}'
        
        # 初始化 Facebook Ads API
        FacebookAdsApi.init(
            app_id=app_id,
            app_secret=app_secret,
            access_token=access_token
        )
        
        # 获取广告账户对象
        account = AdAccount(ad_account_id)
        
        # 使用 SDK 获取视频素材列表
        videos = account.get_ad_videos(fields=[
            AdVideo.Field.id,
            AdVideo.Field.title,
            AdVideo.Field.description,
            AdVideo.Field.length,
            AdVideo.Field.source,
            AdVideo.Field.picture,
            AdVideo.Field.status,
            AdVideo.Field.created_time,
            AdVideo.Field.updated_time,
        ])
        
        # 转换为列表
        videos_list = list(videos)
        
        logger.info(f"Successfully fetched {len(videos_list)} videos for ad_account: {ad_account_id}")
        
        # 转换为响应格式
        result_videos = []
        for video in videos_list:
            # 处理 status 字段：可能是 VideoStatus 对象（支持字典访问）或字符串
            status_value = video.get('status')
            status_str = None
            
            if status_value:
                # VideoStatus 对象支持 get 方法但不是 dict 类型
                try:
                    if hasattr(status_value, 'get'):
                        # 对象支持 get 方法（VideoStatus 或 dict）
                        status_str = status_value.get('video_status', None)
                    if not status_str and isinstance(status_value, str):
                        # 直接是字符串
                        status_str = status_value
                except Exception as e:
                    logger.warning(f"Failed to extract video_status: {e}")
                    status_str = None

            logger.info(f"VideoId: {video.get('id')}, status: {status_str}, type: {type(status_value).__name__}")
            
            result_videos.append(
                AdVideoResponse(
                    id=video.get('id'),
                    title=video.get('title'),
                    description=video.get('description'),
                    length=video.get('length'),
                    picture=video.get('picture'),
                    source=video.get('source'),
                    status=status_str,
                    created_time=video.get('created_time')
                )
            )
        
        return result_videos
        
    except FacebookRequestError as e:
        logger.error(f"Facebook API error: code={e.api_error_code()}, type={e.api_error_type()}, message={e.api_error_message()}")
        
        error_code = e.api_error_code()
        if error_code == 190 or error_code == 102:
            raise HTTPException(status_code=401, detail="Access Token 无效或已过期，请重新授权")
        elif error_code == 200 or error_code == 10:
            raise HTTPException(status_code=403, detail="缺少必要权限，请确保已授予 ads_read 权限")
        else:
            raise HTTPException(status_code=500, detail=f"Meta API 错误: {e.api_error_message()}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch videos: connection_id={connection_id}, ad_account_id={ad_account_id}, error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取视频素材列表失败: {str(e)}")
