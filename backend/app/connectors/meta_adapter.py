"""
ANIFORCE Meta Ads API 适配器
基于 Meta Marketing API v19.0
"""

import aiohttp
import asyncio
from urllib.parse import urlencode
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class MetaAdsAdapter:
    """Meta (Facebook) Ads API 适配器"""

    def __init__(self, config: Dict):
        self.api_version = config.get('api_version', 'v19.0')
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.app_id = config.get('app_id', '')
        self.app_secret = config.get('app_secret', '')
        self.access_token = config.get('access_token')
        self.ad_account_id = config.get('ad_account_id')
        self.proxy_url = config.get('proxy_url') or None

    # ==================== 认证模块 ====================

    def get_oauth_url(self, redirect_uri: str, state: str = None) -> str:
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

        query_string = urlencode(params)
        return f"https://www.facebook.com/{self.api_version}/dialog/oauth?{query_string}"

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict:
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

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params, proxy=self.proxy_url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data['access_token']
                    logger.info("Successfully obtained access token")
                    return data
                else:
                    error = await response.json()
                    logger.error(f"Failed to exchange code: {error}")
                    raise Exception(f"OAuth error: {error}")

    async def get_long_lived_token(self, short_lived_token: str) -> Dict:
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

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params, proxy=self.proxy_url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data['access_token']
                    logger.info("Successfully obtained long-lived token")
                    return data
                else:
                    error = await response.json()
                    logger.error(f"Failed to get long-lived token: {error}")
                    raise Exception(f"Token exchange error: {error}")

    async def debug_token(self, input_token: str) -> Dict:
        """校验 token 并返回 Meta 调试信息。"""
        if not self.app_id or not self.app_secret:
            raise Exception("Meta app_id/app_secret are required to debug token.")

        url = f"{self.base_url}/debug_token"
        params = {
            "input_token": input_token,
            "access_token": f"{self.app_id}|{self.app_secret}",
        }

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params, proxy=self.proxy_url) as response:
                data = await response.json()
                if response.status == 200:
                    return data.get("data", data)
                logger.error(f"Failed to debug token: {data}")
                raise Exception(f"Token debug error: {data}")

    async def get_ad_accounts(self) -> List[Dict]:
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
        url = f"{self.base_url}/me/adaccounts"
        params = {
            'access_token': self.access_token,
            'fields': 'id,name,account_status,currency,timezone_name,amount_spent'
        }

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params, proxy=self.proxy_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    error = await response.json()
                    logger.error(f"Failed to get ad accounts: {error}")
                    raise Exception(f"API error: {error}")

    def set_ad_account(self, ad_account_id: str):
        """设置当前操作的广告账户"""
        # Meta API 要求账户 ID 格式为 act_{account_id}
        if not ad_account_id.startswith('act_'):
            ad_account_id = f"act_{ad_account_id}"
        self.ad_account_id = ad_account_id
        logger.info(f"Set ad account to: {ad_account_id}")

    # ==================== Campaign 管理 ====================

    async def create_campaign(self, params: Dict) -> Dict:
        """
        创建广告系列

        Args:
            params: {
                'name': 'Campaign Name',
                'objective': 'OUTCOME_SALES',  # OUTCOME_SALES/OUTCOME_TRAFFIC/OUTCOME_AWARENESS
                'status': 'PAUSED',  # ACTIVE/PAUSED
                'special_ad_categories': [],  # 特殊广告类别
                'daily_budget': 10000,  # 单位：分（$100.00 = 10000）
                'lifetime_budget': None,
                'bid_strategy': 'LOWEST_COST_WITHOUT_CAP'
            }

        Returns:
            {
                'id': '120212345678901234',
                'success': True
            }
        """
        if not self.ad_account_id:
            raise Exception("Ad account not set. Call set_ad_account() first.")
        if not self.access_token:
            raise Exception("Access token not set.")

        url = f"{self.base_url}/{self.ad_account_id}/campaigns"

        # 构建请求体
        data = {
            'name': params['name'],
            'objective': params.get('objective', 'OUTCOME_SALES'),
            'status': params.get('status', 'PAUSED'),
            'buying_type': params.get('buying_type', 'AUCTION'),
            'is_adset_budget_sharing_enabled': str(params.get('is_adset_budget_sharing_enabled', False)).lower(),
            'special_ad_categories': json.dumps(params.get('special_ad_categories', [])),
            'access_token': self.access_token
        }

        # 预算设置（日预算或总预算，二选一）
        if params.get('daily_budget'):
            data['daily_budget'] = params['daily_budget']
        elif params.get('lifetime_budget'):
            data['lifetime_budget'] = params['lifetime_budget']

        # 出价策略
        if params.get('bid_strategy'):
            data['bid_strategy'] = params['bid_strategy']

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, data=data, proxy=self.proxy_url) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Campaign created: {result['id']}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Failed to create campaign: {error}")
                    raise Exception(f"Campaign creation error: {error}")

    async def create_adset(self, campaign_id: str, params: Dict) -> Dict:
        """
        创建广告组

        Args:
            campaign_id: 广告系列 ID
            params: {
                'name': 'AdSet Name',
                'optimization_goal': 'OFFSITE_CONVERSIONS',
                'billing_event': 'IMPRESSIONS',
                'bid_amount': 500,  # 单位：分
                'daily_budget': 5000,
                'targeting': {
                    'geo_locations': {'countries': ['US']},
                    'age_min': 25,
                    'age_max': 34,
                    'genders': [2],  # 1=male, 2=female, 0=all
                    'interests': [{'id': '6003139266461', 'name': 'Video games'}]
                },
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

        # 预算
        if params.get('daily_budget'):
            data['daily_budget'] = params['daily_budget']
        elif params.get('lifetime_budget'):
            data['lifetime_budget'] = params['lifetime_budget']

        # 出价
        if params.get('bid_amount'):
            data['bid_amount'] = params['bid_amount']

        # 时间范围
        if params.get('start_time'):
            data['start_time'] = params['start_time']
        if params.get('end_time'):
            data['end_time'] = params['end_time']

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"AdSet created: {result['id']}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Failed to create adset: {error}")
                    raise Exception(f"AdSet creation error: {error}")

    async def upload_image(self, image_path: str) -> Dict:
        """
        上传图片素材

        Args:
            image_path: 图片文件路径

        Returns:
            {
                'images': {
                    'filename.jpg': {
                        'hash': 'abc123...',
                        'url': 'https://...'
                    }
                }
            }
        """
        url = f"{self.base_url}/{self.ad_account_id}/adimages"

        with open(image_path, 'rb') as f:
            files = {'filename': f}
            data = {'access_token': self.access_token}

            async with aiohttp.ClientSession() as session:
                form_data = aiohttp.FormData()
                form_data.add_field('access_token', self.access_token)
                form_data.add_field('filename', f, filename=image_path.split('/')[-1])

                async with session.post(url, data=form_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Image uploaded: {result}")
                        return result
                    else:
                        error = await response.json()
                        logger.error(f"Failed to upload image: {error}")
                        raise Exception(f"Image upload error: {error}")

    async def upload_video(self, video_path: str) -> Dict:
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
        import os
        file_size = os.path.getsize(video_path)

        # Step 1: 初始化上传会话
        url = f"{self.base_url}/{self.ad_account_id}/advideos"
        data = {
            'upload_phase': 'start',
            'file_size': file_size,
            'access_token': self.access_token
        }

        async with aiohttp.ClientSession() as session:
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
                    logger.info(f"Video uploaded: {result}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Failed to finish video upload: {error}")
                    raise Exception(f"Video upload finish error: {error}")

    async def create_creative(self, params: Dict) -> Dict:
        """
        创建广告创意

        Args:
            params: {
                'name': 'Creative Name',
                'object_story_spec': {
                    'page_id': '123456789',
                    'link_data': {
                        'image_hash': 'abc123...',  # 或 'video_id': '1234567890'
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
                    logger.info(f"Creative created: {result['id']}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Failed to create creative: {error}")
                    raise Exception(f"Creative creation error: {error}")

    async def create_ad(self, adset_id: str, creative_id: str, params: Dict) -> Dict:
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
                    logger.info(f"Ad created: {result['id']}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Failed to create ad: {error}")
                    raise Exception(f"Ad creation error: {error}")

    # ==================== 数据获取 ====================

    async def get_campaign_insights(self, campaign_id: str, date_range: Dict) -> Dict:
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
                        'actions': [
                            {'action_type': 'purchase', 'value': '10'}
                        ],
                        'date_start': '2026-04-01',
                        'date_stop': '2026-04-06'
                    }
                ]
            }
        """
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
                    logger.error(f"Failed to get insights: {error}")
                    raise Exception(f"Insights error: {error}")

    # ==================== 状态管理 ====================

    async def update_campaign_status(self, campaign_id: str, status: str) -> Dict:
        """
        更新广告系列状态

        Args:
            campaign_id: 广告系列 ID
            status: ACTIVE/PAUSED/DELETED

        Returns:
            {'success': True}
        """
        url = f"{self.base_url}/{campaign_id}"

        data = {
            'status': status,
            'access_token': self.access_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Campaign {campaign_id} status updated to {status}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Failed to update campaign status: {error}")
                    raise Exception(f"Status update error: {error}")

    async def update_budget(self, campaign_id: str, budget: int, budget_type: str = 'daily') -> Dict:
        """
        更新预算

        Args:
            campaign_id: 广告系列 ID
            budget: 预算金额（单位：分）
            budget_type: 'daily' 或 'lifetime'

        Returns:
            {'success': True}
        """
        url = f"{self.base_url}/{campaign_id}"

        data = {
            'access_token': self.access_token
        }

        if budget_type == 'daily':
            data['daily_budget'] = budget
        else:
            data['lifetime_budget'] = budget

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Campaign {campaign_id} budget updated to {budget}")
                    return result
                else:
                    error = await response.json()
                    logger.error(f"Failed to update budget: {error}")
                    raise Exception(f"Budget update error: {error}")


# ==================== 使用示例 ====================

async def example_usage():
    """使用示例"""

    # 初始化适配器
    config = {
        'api_version': 'v19.0',
        'app_id': 'YOUR_APP_ID',
        'app_secret': 'YOUR_APP_SECRET'
    }

    adapter = MetaAdsAdapter(config)

    # 1. 获取 OAuth URL（前端跳转）
    oauth_url = adapter.get_oauth_url(
        redirect_uri='https://your-domain.com/auth/meta/callback',
        state='random_state_string'
    )
    print(f"OAuth URL: {oauth_url}")

    # 2. 用户授权后，用 code 换取 token
    # code = request.args.get('code')
    # token_data = await adapter.exchange_code_for_token(code, redirect_uri)

    # 3. 获取长期 token
    # long_lived_token = await adapter.get_long_lived_token(token_data['access_token'])

    # 4. 获取广告账户列表
    # ad_accounts = await adapter.get_ad_accounts()
    # adapter.set_ad_account(ad_accounts[0]['id'])

    # 5. 创建 Campaign
    # campaign = await adapter.create_campaign({
    #     'name': 'Test Campaign',
    #     'objective': 'OUTCOME_SALES',
    #     'status': 'PAUSED',
    #     'daily_budget': 10000  # $100.00
    # })

    # 6. 创建 AdSet
    # adset = await adapter.create_adset(campaign['id'], {
    #     'name': 'Test AdSet',
    #     'daily_budget': 5000,
    #     'targeting': {
    #         'geo_locations': {'countries': ['US']},
    #         'age_min': 25,
    #         'age_max': 34
    #     }
    # })

    # 7. 上传素材并创建 Creative
    # image = await adapter.upload_image('/path/to/image.jpg')
    # creative = await adapter.create_creative({
    #     'name': 'Test Creative',
    #     'object_story_spec': {
    #         'page_id': 'YOUR_PAGE_ID',
    #         'link_data': {
    #             'image_hash': image['images']['image.jpg']['hash'],
    #             'link': 'https://example.com',
    #             'message': 'Check this out!'
    #         }
    #     }
    # })

    # 8. 创建 Ad
    # ad = await adapter.create_ad(adset['id'], creative['id'], {
    #     'name': 'Test Ad',
    #     'status': 'PAUSED'
    # })

    # 9. 获取数据
    # insights = await adapter.get_campaign_insights(campaign['id'], {
    #     'since': '2026-04-01',
    #     'until': '2026-04-06'
    # })


if __name__ == '__main__':
    asyncio.run(example_usage())
