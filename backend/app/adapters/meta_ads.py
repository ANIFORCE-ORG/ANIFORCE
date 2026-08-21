"""
Meta (Facebook/Instagram) Ads 适配器
基于 Meta Marketing API v19.0
"""

import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from loguru import logger

from .base import BaseAdapter


class MetaAdsAdapter(BaseAdapter):
    """Meta (Facebook) Ads API 适配器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Meta Ads 适配器

        Args:
            config: {
                'api_version': 'v19.0',
                'app_id': 'YOUR_APP_ID',
                'app_secret': 'YOUR_APP_SECRET'
            }
        """
        super().__init__('meta', config)
        self._validate_config(['app_id', 'app_secret'])
        
        self.api_version = config.get('api_version', 'v19.0')
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.app_id = config['app_id']
        self.app_secret = config['app_secret']

    # ==================== 认证模块 ====================

    def get_oauth_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        生成 OAuth 授权 URL

        Args:
            redirect_uri: 回调地址
            state: 状态参数（防 CSRF）

        Returns:
            OAuth 授权 URL
        """
        scopes = ['ads_management', 'ads_read', 'business_management']
        params = {
            'client_id': self.app_id,
            'redirect_uri': redirect_uri,
            'scope': ','.join(scopes),
            'response_type': 'code'
        }
        if state:
            params['state'] = state

        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"https://www.facebook.com/{self.api_version}/dialog/oauth?{query_string}"

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        用授权码换取 Access Token

        Args:
            code: 授权码
            redirect_uri: 回调地址（必须与授权时一致）

        Returns:
            {
                'access_token': 'xxx',
                'token_type': 'bearer',
                'expires_in': 5183944
            }
        """
        url = f"{self.base_url}/oauth/access_token"
        params = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'redirect_uri': redirect_uri,
            'code': code
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data['access_token']
                    logger.info("Meta: Successfully obtained access token")
                    return data
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to exchange code: {error}")
                    raise Exception(f"OAuth error: {error}")

    async def get_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """
        将短期 Token 换成长期 Token（60天有效期）

        Args:
            short_lived_token: 短期 Token

        Returns:
            {
                'access_token': 'xxx',
                'token_type': 'bearer',
                'expires_in': 5183944
            }
        """
        url = f"{self.base_url}/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'fb_exchange_token': short_lived_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data['access_token']
                    logger.info("Meta: Successfully obtained long-lived token")
                    return data
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to get long-lived token: {error}")
                    raise Exception(f"Token exchange error: {error}")

    async def get_ad_accounts(self) -> List[Dict[str, Any]]:
        """
        获取用户的广告账户列表

        Returns:
            [
                {
                    'id': 'act_123456789',
                    'name': 'My Ad Account',
                    'account_status': 1,
                    'currency': 'USD'
                }
            ]
        """
        self._ensure_authenticated()
        
        url = f"{self.base_url}/me/adaccounts"
        params = {
            'access_token': self.access_token,
            'fields': 'id,name,account_status,currency,timezone_name,amount_spent'
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to get ad accounts: {error}")
                    raise Exception(f"API error: {error}")

    def set_ad_account(self, ad_account_id: str):
        """设置当前操作的广告账户"""
        if not ad_account_id.startswith('act_'):
            ad_account_id = f"act_{ad_account_id}"
        self.ad_account_id = ad_account_id
        logger.info(f"Meta: Set ad account to: {ad_account_id}")

    # ==================== Campaign 管理 ====================

    async def create_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建广告系列

        Args:
            params: {
                'name': 'Campaign Name',
                'objective': 'OUTCOME_SALES',
                'status': 'PAUSED',
                'special_ad_categories': [],
                'daily_budget': 10000,
                'lifetime_budget': None,
                'bid_strategy': 'LOWEST_COST_WITHOUT_CAP'
            }

        Returns:
            {
                'id': '120212345678901234',
                'success': True
            }
        """
        self._ensure_authenticated()
        self._ensure_ad_account()

        url = f"{self.base_url}/{self.ad_account_id}/campaigns"

        data = {
            'name': params['name'],
            'objective': params.get('objective', 'OUTCOME_SALES'),
            'status': params.get('status', 'PAUSED'),
            'special_ad_categories': params.get('special_ad_categories', []),
            'access_token': self.access_token
        }

        if params.get('daily_budget'):
            data['daily_budget'] = params['daily_budget']
        elif params.get('lifetime_budget'):
            data['lifetime_budget'] = params['lifetime_budget']

        if params.get('bid_strategy'):
            data['bid_strategy'] = params['bid_strategy']

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Meta: Campaign created: {result['id']}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to create campaign: {error}")
                    raise Exception(f"Campaign creation error: {error}")

    async def update_campaign(self, campaign_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新广告系列

        Args:
            campaign_id: 广告系列 ID
            params: 更新参数

        Returns:
            {'success': True}
        """
        self._ensure_authenticated()
        
        url = f"{self.base_url}/{campaign_id}"
        data = {**params, 'access_token': self.access_token}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Meta: Campaign {campaign_id} updated")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to update campaign: {error}")
                    raise Exception(f"Campaign update error: {error}")

    async def update_campaign_status(self, campaign_id: str, status: str) -> Dict[str, Any]:
        """
        更新广告系列状态

        Args:
            campaign_id: 广告系列 ID
            status: ACTIVE/PAUSED/DELETED

        Returns:
            {'success': True}
        """
        self._ensure_authenticated()
        
        url = f"{self.base_url}/{campaign_id}"
        data = {
            'status': status,
            'access_token': self.access_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Meta: Campaign {campaign_id} status updated to {status}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to update campaign status: {error}")
                    raise Exception(f"Status update error: {error}")

    async def update_budget(self, campaign_id: str, budget: int, budget_type: str = 'daily') -> Dict[str, Any]:
        """
        更新预算

        Args:
            campaign_id: 广告系列 ID
            budget: 预算金额（单位：分）
            budget_type: 'daily' 或 'lifetime'

        Returns:
            {'success': True}
        """
        self._ensure_authenticated()
        
        url = f"{self.base_url}/{campaign_id}"
        data = {'access_token': self.access_token}

        if budget_type == 'daily':
            data['daily_budget'] = budget
        else:
            data['lifetime_budget'] = budget

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Meta: Campaign {campaign_id} budget updated to {budget}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to update budget: {error}")
                    raise Exception(f"Budget update error: {error}")

    # ==================== AdSet 管理 ====================

    async def create_adset(self, campaign_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建广告组

        Args:
            campaign_id: 广告系列 ID
            params: {
                'name': 'AdSet Name',
                'optimization_goal': 'OFFSITE_CONVERSIONS',
                'billing_event': 'IMPRESSIONS',
                'bid_amount': 500,
                'daily_budget': 5000,
                'targeting': {...},
                'start_time': '2026-04-07T00:00:00+0000',
                'end_time': None,
                'status': 'PAUSED'
            }

        Returns:
            {
                'id': '120212345678901235',
                'success': True
            }
        """
        self._ensure_authenticated()
        self._ensure_ad_account()
        
        url = f"{self.base_url}/{self.ad_account_id}/adsets"

        data = {
            'name': params['name'],
            'campaign_id': campaign_id,
            'optimization_goal': params.get('optimization_goal', 'OFFSITE_CONVERSIONS'),
            'billing_event': params.get('billing_event', 'IMPRESSIONS'),
            'status': params.get('status', 'PAUSED'),
            'targeting': json.dumps(params['targeting']),
            'access_token': self.access_token
        }

        if params.get('daily_budget'):
            data['daily_budget'] = params['daily_budget']
        elif params.get('lifetime_budget'):
            data['lifetime_budget'] = params['lifetime_budget']

        if params.get('bid_amount'):
            data['bid_amount'] = params['bid_amount']

        if params.get('start_time'):
            data['start_time'] = params['start_time']
        if params.get('end_time'):
            data['end_time'] = params['end_time']

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Meta: AdSet created: {result['id']}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to create adset: {error}")
                    raise Exception(f"AdSet creation error: {error}")

    # ==================== Creative 管理 ====================

    async def upload_image(self, image_path: str) -> Dict[str, Any]:
        """
        上传图片素材

        Args:
            image_path: 图片文件路径

        Returns:
            {
                'hash': 'abc123...',
                'url': 'https://...'
            }
        """
        self._ensure_authenticated()
        self._ensure_ad_account()
        
        url = f"{self.base_url}/{self.ad_account_id}/adimages"

        with open(image_path, 'rb') as f:
            async with aiohttp.ClientSession() as session:
                form_data = aiohttp.FormData()
                form_data.add_field('access_token', self.access_token)
                form_data.add_field('filename', f, filename=image_path.split('/')[-1])

                async with session.post(url, data=form_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Meta: Image uploaded: {result}")
                        return result
                    else:
                        error = await response.json()
                        logger.error(f"Meta: Failed to upload image: {error}")
                        raise Exception(f"Image upload error: {error}")

    async def upload_video(self, video_path: str) -> Dict[str, Any]:
        """
        上传视频素材（分块上传）

        Args:
            video_path: 视频文件路径

        Returns:
            {
                'id': '1234567890',
                'success': True
            }
        """
        self._ensure_authenticated()
        self._ensure_ad_account()
        
        import os
        file_size = os.path.getsize(video_path)

        url = f"{self.base_url}/{self.ad_account_id}/advideos"
        
        async with aiohttp.ClientSession() as session:
            # Step 1: 初始化上传会话
            data = {
                'upload_phase': 'start',
                'file_size': file_size,
                'access_token': self.access_token
            }

            async with session.post(url, data=data) as response:
                if response.status != 200:
                    error = await response.json()
                    raise Exception(f"Video upload init error: {error}")

                init_result = await response.json()
                upload_session_id = init_result['upload_session_id']
                start_offset = init_result['start_offset']
                end_offset = init_result['end_offset']

            # Step 2: 分块上传
            with open(video_path, 'rb') as f:
                f.seek(start_offset)
                chunk = f.read(end_offset - start_offset)

                form_data = aiohttp.FormData()
                form_data.add_field('upload_phase', 'transfer')
                form_data.add_field('upload_session_id', upload_session_id)
                form_data.add_field('start_offset', str(start_offset))
                form_data.add_field('video_file_chunk', chunk)
                form_data.add_field('access_token', self.access_token)

                async with session.post(url, data=form_data) as response:
                    if response.status != 200:
                        error = await response.json()
                        raise Exception(f"Video upload transfer error: {error}")

            # Step 3: 完成上传
            data = {
                'upload_phase': 'finish',
                'upload_session_id': upload_session_id,
                'access_token': self.access_token
            }

            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Meta: Video uploaded: {result}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to finish video upload: {error}")
                    raise Exception(f"Video upload finish error: {error}")

    async def create_creative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建广告创意

        Args:
            params: {
                'name': 'Creative Name',
                'object_story_spec': {
                    'page_id': '123456789',
                    'link_data': {
                        'image_hash': 'abc123...',
                        'link': 'https://example.com',
                        'message': 'Ad text',
                        'name': 'Headline',
                        'description': 'Description',
                        'call_to_action': {
                            'type': 'LEARN_MORE'
                        }
                    }
                }
            }

        Returns:
            {
                'id': '120212345678901236',
                'success': True
            }
        """
        self._ensure_authenticated()
        self._ensure_ad_account()
        
        url = f"{self.base_url}/{self.ad_account_id}/adcreatives"

        data = {
            'name': params['name'],
            'object_story_spec': json.dumps(params['object_story_spec']),
            'access_token': self.access_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Meta: Creative created: {result['id']}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to create creative: {error}")
                    raise Exception(f"Creative creation error: {error}")

    async def create_ad(self, adset_id: str, creative_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建广告

        Args:
            adset_id: 广告组 ID
            creative_id: 创意 ID
            params: {
                'name': 'Ad Name',
                'status': 'PAUSED'
            }

        Returns:
            {
                'id': '120212345678901237',
                'success': True
            }
        """
        self._ensure_authenticated()
        self._ensure_ad_account()
        
        url = f"{self.base_url}/{self.ad_account_id}/ads"

        data = {
            'name': params['name'],
            'adset_id': adset_id,
            'creative': json.dumps({'creative_id': creative_id}),
            'status': params.get('status', 'PAUSED'),
            'access_token': self.access_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Meta: Ad created: {result['id']}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to create ad: {error}")
                    raise Exception(f"Ad creation error: {error}")

    # ==================== 数据获取 ====================

    async def get_account_daily_insights(
        self,
        account_id: str,
        date_range: Dict[str, str],
        level: str,
        *,
        max_pages: int = 10,
    ) -> List[Dict[str, Any]]:
        """Read paginated daily Insights for one explicitly selected account."""
        self._ensure_authenticated()
        if level not in {"campaign", "adset", "ad"}:
            raise ValueError(f"Unsupported Meta Insights level: {level}")
        if max_pages < 1:
            raise ValueError("max_pages must be positive")

        normalized_account_id = str(account_id).removeprefix("act_")
        level_fields = {
            "campaign": ["campaign_id", "campaign_name", "objective"],
            "adset": ["campaign_id", "campaign_name", "adset_id", "adset_name", "objective", "optimization_goal"],
            "ad": ["campaign_id", "campaign_name", "adset_id", "adset_name", "ad_id", "ad_name"],
        }
        fields = [
            "account_id", "account_name", *level_fields[level],
            "impressions", "reach", "frequency", "clicks", "inline_link_clicks",
            "spend", "ctr", "cpc", "cpm", "actions", "action_values",
            "cost_per_action_type", "account_currency", "attribution_setting",
            "date_start", "date_stop",
        ]
        url: str | None = f"{self.base_url}/act_{normalized_account_id}/insights"
        params: Dict[str, Any] | None = {
            "access_token": self.access_token,
            "time_range": json.dumps(date_range),
            "time_increment": 1,
            "fields": ",".join(fields),
            "level": level,
            "limit": 100,
        }
        rows: List[Dict[str, Any]] = []
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for _ in range(max_pages):
                if not url:
                    break
                async with session.get(url, params=params) as response:
                    payload = await response.json()
                    if response.status != 200:
                        error = payload.get("error", payload)
                        raise Exception(f"Meta Insights read failed: {error}")
                    rows.extend(payload.get("data") or [])
                    url = (payload.get("paging") or {}).get("next")
                    params = None
        if url:
            raise RuntimeError(
                f"Meta Insights pagination exceeded the {max_pages}-page safety limit"
            )
        return rows

    async def get_campaign_insights(self, campaign_id: str, date_range: Dict[str, str]) -> Dict[str, Any]:
        """
        获取广告系列数据洞察

        Args:
            campaign_id: 广告系列 ID
            date_range: {
                'since': '2026-04-01',
                'until': '2026-04-06'
            }

        Returns:
            {
                'data': [
                    {
                        'impressions': '1000',
                        'clicks': '50',
                        'spend': '100.50',
                        'actions': [...],
                        'date_start': '2026-04-01',
                        'date_stop': '2026-04-06'
                    }
                ]
            }
        """
        self._ensure_authenticated()
        
        url = f"{self.base_url}/{campaign_id}/insights"

        params = {
            'access_token': self.access_token,
            'time_range': json.dumps(date_range),
            'fields': ','.join([
                'impressions',
                'clicks',
                'spend',
                'ctr',
                'cpc',
                'cpm',
                'actions',
                'conversions',
                'cost_per_action_type',
                'date_start',
                'date_stop'
            ]),
            'level': 'campaign'
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Meta: Failed to get insights: {error}")
                    raise Exception(f"Insights error: {error}")
