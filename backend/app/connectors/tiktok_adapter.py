"""
TikTok Ads API 适配器实现
基于 TikTok Marketing API v1.3
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
import json
import hashlib
import hmac
from .platform_interface import PlatformAdapter


logger = logging.getLogger(__name__)


class TikTokAdsAdapter(PlatformAdapter):
    """TikTok 广告平台适配器"""

    def __init__(self, config: Dict):
        """
        初始化 TikTok Ads 适配器

        Args:
            config: {
                "app_id": str,
                "app_secret": str,
                "access_token": str,
                "advertiser_id": str,
                "api_version": str  # v1.3
            }
        """
        self.app_id = config.get("app_id")
        self.app_secret = config.get("app_secret")
        self.access_token = config.get("access_token")
        self.advertiser_id = config.get("advertiser_id")
        self.api_version = config.get("api_version", "v1.3")
        self.base_url = f"https://business-api.tiktok.com/open_api/{self.api_version}"

        # 目标映射
        self.objective_mapping = {
            "CONVERSIONS": "CONVERSIONS",
            "TRAFFIC": "TRAFFIC",
            "AWARENESS": "REACH",
            "APP_INSTALLS": "APP_PROMOTION"
        }

        # 状态映射
        self.status_mapping = {
            "ACTIVE": "ENABLE",
            "PAUSED": "DISABLE",
            "DELETED": "DELETE"
        }

    async def authenticate(self, credentials: Dict) -> Dict:
        """
        OAuth 2.0 认证流程

        Args:
            credentials: {
                "auth_code": str,  # TikTok 使用 auth_code
                "redirect_uri": str
            }

        Returns:
            {
                "access_token": str,
                "expires_in": int,
                "token_type": str
            }
        """
        auth_code = credentials.get("auth_code") or credentials.get("code")
        redirect_uri = credentials.get("redirect_uri")

        if not auth_code:
            raise ValueError("Missing auth_code")

        return await self.exchange_code_for_token(auth_code)

    async def exchange_code_for_token(self, auth_code: str) -> Dict:
        """
        用 auth_code 换取 access token

        Args:
            auth_code: Authorization code

        Returns:
            Token 信息
        """
        url = f"{self.base_url}/oauth2/access_token/"
        data = {
            "app_id": self.app_id,
            "secret": self.app_secret,
            "auth_code": auth_code
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Token exchange failed: {error_text}")
                    raise Exception(f"Failed to exchange token: {error_text}")

                result = await response.json()

                if result.get("code") != 0:
                    raise Exception(f"TikTok API error: {result.get('message')}")

                data = result.get("data", {})
                self.access_token = data.get("access_token")

                logger.info("Successfully exchanged code for access token")

                return {
                    "access_token": data.get("access_token"),
                    "expires_in": data.get("access_token_expire_in"),
                    "token_type": "Bearer"
                }

    async def create_campaign(self, params: Dict) -> Dict:
        """
        创建广告系列

        Args:
            params: {
                "name": str,
                "objective": str,
                "status": str,
                "budget": float,
                "budget_type": str
            }

        Returns:
            创建结果
        """
        url = f"{self.base_url}/campaign/create/"

        # 映射目标
        objective = self.objective_mapping.get(
            params.get("objective", "CONVERSIONS"),
            "CONVERSIONS"
        )

        # 构建请求数据
        data = {
            "advertiser_id": self.advertiser_id,
            "campaign_name": params.get("name"),
            "objective_type": objective,
            "budget_mode": "BUDGET_MODE_DAY" if params.get("budget_type") == "DAILY" else "BUDGET_MODE_TOTAL",
            "budget": params.get("budget"),
            "operation_status": self.status_mapping.get(params.get("status", "PAUSED"), "DISABLE")
        }

        headers = {
            "Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Campaign creation failed: {error_text}")
                    raise Exception(f"Failed to create campaign: {error_text}")

                result = await response.json()

                if result.get("code") != 0:
                    raise Exception(f"TikTok API error: {result.get('message')}")

                campaign_id = result.get("data", {}).get("campaign_id")
                logger.info(f"Campaign created: {campaign_id}")

                return {
                    "id": campaign_id,
                    "name": params.get("name"),
                    "status": params.get("status"),
                    "created_time": datetime.now()
                }

    async def create_adset(self, campaign_id: str, params: Dict) -> Dict:
        """
        创建广告组（TikTok 中称为 AdGroup）

        Args:
            campaign_id: 广告系列 ID
            params: {
                "name": str,
                "status": str,
                "budget": Optional[float],
                "targeting": Dict,
                "bid_strategy": str,
                "bid_amount": Optional[float]
            }

        Returns:
            创建结果
        """
        url = f"{self.base_url}/adgroup/create/"

        # 构建定向参数
        targeting = self._build_targeting(params.get("targeting", {}))

        # 构建请求数据
        data = {
            "advertiser_id": self.advertiser_id,
            "campaign_id": campaign_id,
            "adgroup_name": params.get("name"),
            "placement_type": "PLACEMENT_TYPE_AUTOMATIC",
            "placements": ["PLACEMENT_TIKTOK"],
            "location_ids": targeting.get("location_ids", []),
            "age_groups": targeting.get("age_groups", []),
            "gender": targeting.get("gender", "GENDER_UNLIMITED"),
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": params.get("budget", 50.0),
            "schedule_type": "SCHEDULE_START_END",
            "operation_status": self.status_mapping.get(params.get("status", "PAUSED"), "DISABLE"),
            "billing_event": "CPC",
            "optimization_goal": "CLICK"
        }

        # 添加出价
        if params.get("bid_amount"):
            data["bid_price"] = params.get("bid_amount")
            data["bid_type"] = "BID_TYPE_CUSTOM"
        else:
            data["bid_type"] = "BID_TYPE_NO_BID"

        headers = {
            "Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"AdGroup creation failed: {error_text}")
                    raise Exception(f"Failed to create adgroup: {error_text}")

                result = await response.json()

                if result.get("code") != 0:
                    raise Exception(f"TikTok API error: {result.get('message')}")

                adgroup_id = result.get("data", {}).get("adgroup_id")
                logger.info(f"AdGroup created: {adgroup_id}")

                return {
                    "id": adgroup_id,
                    "campaign_id": campaign_id,
                    "name": params.get("name"),
                    "status": params.get("status")
                }

    def _build_targeting(self, targeting: Dict) -> Dict:
        """
        构建 TikTok 定向参数

        Args:
            targeting: 统一定向参数

        Returns:
            TikTok 格式的定向参数
        """
        tiktok_targeting = {}

        # 地区（TikTok 使用 location_ids）
        if targeting.get("countries"):
            # 这里需要将国家代码映射到 TikTok 的 location_ids
            # 简化处理，实际需要调用 TikTok 的 location API
            tiktok_targeting["location_ids"] = targeting["countries"]

        # 年龄
        age_min = targeting.get("age_min", 18)
        age_max = targeting.get("age_max", 65)
        age_groups = []
        if age_min <= 17:
            age_groups.append("AGE_13_17")
        if age_min <= 24 and age_max >= 18:
            age_groups.append("AGE_18_24")
        if age_min <= 34 and age_max >= 25:
            age_groups.append("AGE_25_34")
        if age_min <= 44 and age_max >= 35:
            age_groups.append("AGE_35_44")
        if age_min <= 54 and age_max >= 45:
            age_groups.append("AGE_45_54")
        if age_max >= 55:
            age_groups.append("AGE_55_100")

        tiktok_targeting["age_groups"] = age_groups if age_groups else ["AGE_18_100"]

        # 性别
        gender = targeting.get("gender", "all")
        if gender == "male":
            tiktok_targeting["gender"] = "GENDER_MALE"
        elif gender == "female":
            tiktok_targeting["gender"] = "GENDER_FEMALE"
        else:
            tiktok_targeting["gender"] = "GENDER_UNLIMITED"

        return tiktok_targeting

    async def create_ad(self, adset_id: str, creative_id: str, params: Dict) -> Dict:
        """
        创建广告

        Args:
            adset_id: 广告组 ID
            creative_id: 创意 ID
            params: {
                "name": str,
                "status": str
            }

        Returns:
            创建结果
        """
        url = f"{self.base_url}/ad/create/"

        data = {
            "advertiser_id": self.advertiser_id,
            "adgroup_id": adset_id,
            "creatives": [{
                "ad_name": params.get("name"),
                "ad_text": params.get("ad_text", "Default ad text"),
                "video_id": creative_id,
                "call_to_action": "LEARN_MORE",
                "landing_page_url": params.get("landing_page_url", "https://example.com")
            }],
            "operation_status": self.status_mapping.get(params.get("status", "PAUSED"), "DISABLE")
        }

        headers = {
            "Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ad creation failed: {error_text}")
                    raise Exception(f"Failed to create ad: {error_text}")

                result = await response.json()

                if result.get("code") != 0:
                    raise Exception(f"TikTok API error: {result.get('message')}")

                ad_ids = result.get("data", {}).get("ad_ids", [])
                ad_id = ad_ids[0] if ad_ids else None

                logger.info(f"Ad created: {ad_id}")

                return {
                    "id": ad_id,
                    "adset_id": adset_id,
                    "creative_id": creative_id,
                    "name": params.get("name"),
                    "status": params.get("status")
                }

    async def upload_creative(self, file_path: str, params: Dict) -> Dict:
        """
        上传创意素材

        Args:
            file_path: 素材文件路径
            params: {
                "type": str,  # image/video
                "name": str
            }

        Returns:
            上传结果
        """
        file_type = params.get("type", "video")

        if file_type == "image":
            return await self.upload_image(file_path)
        elif file_type == "video":
            return await self.upload_video(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    async def upload_image(self, image_path: str) -> Dict:
        """上传图片"""
        url = f"{self.base_url}/file/image/ad/upload/"

        with open(image_path, 'rb') as f:
            image_data = f.read()

        data = aiohttp.FormData()
        data.add_field('advertiser_id', self.advertiser_id)
        data.add_field('image_file', image_data, filename=image_path.split('/')[-1])

        headers = {
            "Access-Token": self.access_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Image upload failed: {error_text}")
                    raise Exception(f"Failed to upload image: {error_text}")

                result = await response.json()

                if result.get("code") != 0:
                    raise Exception(f"TikTok API error: {result.get('message')}")

                image_id = result.get("data", {}).get("image_id")
                logger.info(f"Image uploaded: {image_id}")

                return {
                    "id": image_id,
                    "type": "image",
                    "url": result.get("data", {}).get("image_url", "")
                }

    async def upload_video(self, video_path: str) -> Dict:
        """上传视频"""
        url = f"{self.base_url}/file/video/ad/upload/"

        with open(video_path, 'rb') as f:
            video_data = f.read()

        data = aiohttp.FormData()
        data.add_field('advertiser_id', self.advertiser_id)
        data.add_field('video_file', video_data, filename=video_path.split('/')[-1])

        headers = {
            "Access-Token": self.access_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Video upload failed: {error_text}")
                    raise Exception(f"Failed to upload video: {error_text}")

                result = await response.json()

                if result.get("code") != 0:
                    raise Exception(f"TikTok API error: {result.get('message')}")

                video_id = result.get("data", {}).get("video_id")
                logger.info(f"Video uploaded: {video_id}")

                return {
                    "id": video_id,
                    "type": "video",
                    "url": result.get("data", {}).get("video_url", "")
                }

    async def get_campaign_insights(self, campaign_id: str, date_range: Dict) -> Dict:
        """
        获取广告系列数据

        Args:
            campaign_id: 广告系列 ID
            date_range: {
                "since": str,  # YYYY-MM-DD
                "until": str   # YYYY-MM-DD
            }

        Returns:
            数据洞察
        """
        url = f"{self.base_url}/report/integrated/get/"

        data = {
            "advertiser_id": self.advertiser_id,
            "report_type": "BASIC",
            "data_level": "AUCTION_CAMPAIGN",
            "dimensions": ["campaign_id"],
            "metrics": ["impressions", "clicks", "spend", "conversions", "conversion_rate", "cpc", "cpm"],
            "start_date": date_range.get("since"),
            "end_date": date_range.get("until"),
            "filters": [{
                "field_name": "campaign_id",
                "filter_type": "IN",
                "filter_value": [campaign_id]
            }]
        }

        headers = {
            "Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to get insights: {error_text}")
                    raise Exception(f"Failed to get insights: {error_text}")

                result = await response.json()

                if result.get("code") != 0:
                    raise Exception(f"TikTok API error: {result.get('message')}")

                # 解析数据
                data_list = result.get("data", {}).get("list", [])
                if not data_list:
                    return self._empty_insights()

                metrics = data_list[0].get("metrics", {})

                impressions = int(metrics.get("impressions", 0))
                clicks = int(metrics.get("clicks", 0))
                spend = float(metrics.get("spend", 0))
                conversions = int(metrics.get("conversions", 0))

                # 计算指标
                ctr = (clicks / impressions * 100) if impressions > 0 else 0
                cpc = float(metrics.get("cpc", 0))
                cpa = (spend / conversions) if conversions > 0 else 0

                return {
                    "impressions": impressions,
                    "clicks": clicks,
                    "spend": round(spend, 2),
                    "conversions": conversions,
                    "ctr": round(ctr, 2),
                    "cpc": round(cpc, 2),
                    "cpa": round(cpa, 2),
                    "roas": None
                }

    def _empty_insights(self) -> Dict:
        """返回空的数据洞察"""
        return {
            "impressions": 0,
            "clicks": 0,
            "spend": 0.0,
            "conversions": 0,
            "ctr": 0.0,
            "cpc": 0.0,
            "cpa": 0.0,
            "roas": None
        }

    async def update_campaign_status(self, campaign_id: str, status: str) -> Dict:
        """
        更新广告系列状态

        Args:
            campaign_id: 广告系列 ID
            status: 新状态

        Returns:
            更新结果
        """
        url = f"{self.base_url}/campaign/update/status/"

        data = {
            "advertiser_id": self.advertiser_id,
            "campaign_ids": [campaign_id],
            "operation_status": self.status_mapping.get(status, "DISABLE")
        }

        headers = {
            "Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to update status: {error_text}")
                    raise Exception(f"Failed to update status: {error_text}")

                result = await response.json()

                if result.get("code") != 0:
                    raise Exception(f"TikTok API error: {result.get('message')}")

                logger.info(f"Campaign status updated: {campaign_id} -> {status}")

                return {
                    "id": campaign_id,
                    "status": status,
                    "updated_time": datetime.now()
                }

    async def update_budget(self, campaign_id: str, budget: float) -> Dict:
        """
        更新预算

        Args:
            campaign_id: 广告系列 ID
            budget: 新预算

        Returns:
            更新结果
        """
        url = f"{self.base_url}/campaign/update/"

        data = {
            "advertiser_id": self.advertiser_id,
            "campaign_id": campaign_id,
            "budget": budget
        }

        headers = {
            "Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to update budget: {error_text}")
                    raise Exception(f"Failed to update budget: {error_text}")

                result = await response.json()

                if result.get("code") != 0:
                    raise Exception(f"TikTok API error: {result.get('message')}")

                logger.info(f"Campaign budget updated: {campaign_id} -> ${budget}")

                return {
                    "id": campaign_id,
                    "budget": budget,
                    "updated_time": datetime.now()
                }


# 使用示例
async def example_usage():
    """使用示例"""

    config = {
        "app_id": "YOUR_APP_ID",
        "app_secret": "YOUR_APP_SECRET",
        "access_token": "YOUR_ACCESS_TOKEN",
        "advertiser_id": "123456789"
    }

    adapter = TikTokAdsAdapter(config)

    # 创建广告系列
    campaign = await adapter.create_campaign({
        "name": "测试广告系列",
        "objective": "CONVERSIONS",
        "status": "PAUSED",
        "budget": 100.0,
        "budget_type": "DAILY"
    })

    print(f"Campaign created: {campaign['id']}")


if __name__ == "__main__":
    asyncio.run(example_usage())
