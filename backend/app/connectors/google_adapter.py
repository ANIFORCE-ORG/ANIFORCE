"""
Google Ads API 适配器实现
基于 Google Ads API v15
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
import json
from .platform_interface import PlatformAdapter


logger = logging.getLogger(__name__)


class GoogleAdsAdapter(PlatformAdapter):
    """Google 广告平台适配器"""

    def __init__(self, config: Dict):
        """
        初始化 Google Ads 适配器

        Args:
            config: {
                "client_id": str,
                "client_secret": str,
                "developer_token": str,
                "refresh_token": str,
                "customer_id": str,  # 123-456-7890
                "login_customer_id": str  # 可选，MCC 账户 ID
            }
        """
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.developer_token = config.get("developer_token")
        self.refresh_token = config.get("refresh_token")
        self.customer_id = config.get("customer_id", "").replace("-", "")
        self.login_customer_id = config.get("login_customer_id", "").replace("-", "")
        self.api_version = config.get("api_version", "v15")
        self.base_url = f"https://googleads.googleapis.com/{self.api_version}"

        self.access_token = None

        # 目标映射
        self.objective_mapping = {
            "CONVERSIONS": "MAXIMIZE_CONVERSIONS",
            "TRAFFIC": "MAXIMIZE_CLICKS",
            "AWARENESS": "TARGET_IMPRESSION_SHARE",
            "APP_INSTALLS": "MAXIMIZE_CONVERSION_VALUE"
        }

        # 状态映射
        self.status_mapping = {
            "ACTIVE": "ENABLED",
            "PAUSED": "PAUSED",
            "DELETED": "REMOVED"
        }

    async def authenticate(self, credentials: Dict) -> Dict:
        """
        OAuth 2.0 认证流程

        Args:
            credentials: {
                "code": str,  # Authorization code
                "redirect_uri": str
            }

        Returns:
            {
                "access_token": str,
                "expires_in": int,
                "token_type": str,
                "refresh_token": str
            }
        """
        code = credentials.get("code")
        redirect_uri = credentials.get("redirect_uri")

        if not code or not redirect_uri:
            raise ValueError("Missing code or redirect_uri")

        return await self.exchange_code_for_token(code, redirect_uri)

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict:
        """
        用 authorization code 换取 access token

        Args:
            code: Authorization code
            redirect_uri: 回调 URI

        Returns:
            Token 信息
        """
        url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Token exchange failed: {error_text}")
                    raise Exception(f"Failed to exchange token: {error_text}")

                result = await response.json()
                self.access_token = result.get("access_token")
                self.refresh_token = result.get("refresh_token", self.refresh_token)
                logger.info("Successfully exchanged code for access token")
                return result

    async def refresh_access_token(self) -> str:
        """刷新 access token"""
        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to refresh token: {error_text}")

                result = await response.json()
                self.access_token = result.get("access_token")
                return self.access_token

    async def _ensure_access_token(self):
        """确保有有效的 access token"""
        if not self.access_token:
            await self.refresh_access_token()

    async def create_campaign(self, params: Dict) -> Dict:
        """
        创建广告系列

        Args:
            params: {
                "name": str,
                "objective": str,
                "status": str,
                "budget": float,
                "budget_type": str,
                "start_time": Optional[datetime],
                "end_time": Optional[datetime]
            }

        Returns:
            创建结果
        """
        await self._ensure_access_token()

        # 构建 GAQL 查询
        campaign_budget_resource = await self._create_campaign_budget(params.get("budget"))

        # 映射目标
        bidding_strategy = self.objective_mapping.get(
            params.get("objective", "CONVERSIONS"),
            "MAXIMIZE_CONVERSIONS"
        )

        # 构建请求
        operations = [{
            "create": {
                "name": params.get("name"),
                "status": self.status_mapping.get(params.get("status", "PAUSED"), "PAUSED"),
                "campaign_budget": campaign_budget_resource,
                "advertising_channel_type": "SEARCH",
                "bidding_strategy_type": bidding_strategy,
                "start_date": params.get("start_time").strftime("%Y%m%d") if params.get("start_time") else None,
                "end_date": params.get("end_time").strftime("%Y%m%d") if params.get("end_time") else None
            }
        }]

        url = f"{self.base_url}/customers/{self.customer_id}/campaigns:mutate"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json"
        }
        if self.login_customer_id:
            headers["login-customer-id"] = self.login_customer_id

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={"operations": operations}) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Campaign creation failed: {error_text}")
                    raise Exception(f"Failed to create campaign: {error_text}")

                result = await response.json()
                campaign_resource = result["results"][0]["resourceName"]
                campaign_id = campaign_resource.split("/")[-1]

                logger.info(f"Campaign created: {campaign_id}")

                return {
                    "id": campaign_id,
                    "name": params.get("name"),
                    "status": params.get("status"),
                    "created_time": datetime.now()
                }

    async def _create_campaign_budget(self, budget: float) -> str:
        """创建广告系列预算"""
        operations = [{
            "create": {
                "name": f"Budget {datetime.now().strftime('%Y%m%d%H%M%S')}",
                "amount_micros": int(budget * 1_000_000),
                "delivery_method": "STANDARD"
            }
        }]

        url = f"{self.base_url}/customers/{self.customer_id}/campaignBudgets:mutate"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={"operations": operations}) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to create budget: {error_text}")

                result = await response.json()
                return result["results"][0]["resourceName"]

    async def create_adset(self, campaign_id: str, params: Dict) -> Dict:
        """
        创建广告组（Google Ads 中称为 Ad Group）

        Args:
            campaign_id: 广告系列 ID
            params: 创建参数

        Returns:
            创建结果
        """
        await self._ensure_access_token()

        operations = [{
            "create": {
                "name": params.get("name"),
                "campaign": f"customers/{self.customer_id}/campaigns/{campaign_id}",
                "status": self.status_mapping.get(params.get("status", "PAUSED"), "PAUSED"),
                "type": "SEARCH_STANDARD",
                "cpc_bid_micros": int(params.get("bid_amount", 1.0) * 1_000_000) if params.get("bid_amount") else None
            }
        }]

        url = f"{self.base_url}/customers/{self.customer_id}/adGroups:mutate"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={"operations": operations}) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"AdGroup creation failed: {error_text}")
                    raise Exception(f"Failed to create adgroup: {error_text}")

                result = await response.json()
                adgroup_resource = result["results"][0]["resourceName"]
                adgroup_id = adgroup_resource.split("/")[-1]

                logger.info(f"AdGroup created: {adgroup_id}")

                return {
                    "id": adgroup_id,
                    "campaign_id": campaign_id,
                    "name": params.get("name"),
                    "status": params.get("status")
                }

    async def create_ad(self, adset_id: str, creative_id: str, params: Dict) -> Dict:
        """
        创建广告

        Args:
            adset_id: 广告组 ID
            creative_id: 创意 ID（在 Google Ads 中是 Ad 的一部分）
            params: 创建参数

        Returns:
            创建结果
        """
        await self._ensure_access_token()

        # Google Ads 的广告创建需要包含创意内容
        operations = [{
            "create": {
                "ad_group": f"customers/{self.customer_id}/adGroups/{adset_id}",
                "status": self.status_mapping.get(params.get("status", "PAUSED"), "PAUSED"),
                "ad": {
                    "final_urls": params.get("final_urls", ["https://example.com"]),
                    "responsive_search_ad": {
                        "headlines": params.get("headlines", [{"text": "Default Headline"}]),
                        "descriptions": params.get("descriptions", [{"text": "Default Description"}])
                    }
                }
            }
        }]

        url = f"{self.base_url}/customers/{self.customer_id}/adGroupAds:mutate"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={"operations": operations}) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ad creation failed: {error_text}")
                    raise Exception(f"Failed to create ad: {error_text}")

                result = await response.json()
                ad_resource = result["results"][0]["resourceName"]
                ad_id = ad_resource.split("/")[-1]

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
        上传创意素材（Google Ads 使用 Asset Service）

        Args:
            file_path: 素材文件路径
            params: 上传参数

        Returns:
            上传结果
        """
        await self._ensure_access_token()

        # Google Ads 的素材上传较复杂，这里提供简化实现
        # 实际使用中需要根据素材类型（图片/视频）调用不同的 API

        logger.info(f"Creative upload for Google Ads: {file_path}")

        return {
            "id": f"asset_{datetime.now().timestamp()}",
            "type": params.get("type", "image"),
            "url": f"https://googleads.com/assets/{file_path}"
        }

    async def get_campaign_insights(self, campaign_id: str, date_range: Dict) -> Dict:
        """
        获取广告系列数据（使用 GAQL 查询）

        Args:
            campaign_id: 广告系列 ID
            date_range: 日期范围

        Returns:
            数据洞察
        """
        await self._ensure_access_token()

        # 构建 GAQL 查询
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE campaign.id = {campaign_id}
                AND segments.date BETWEEN '{date_range.get("since")}' AND '{date_range.get("until")}'
        """

        url = f"{self.base_url}/customers/{self.customer_id}/googleAds:searchStream"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={"query": query}) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to get insights: {error_text}")
                    raise Exception(f"Failed to get insights: {error_text}")

                result = await response.json()

                # 解析结果
                if not result or not result[0].get("results"):
                    return self._empty_insights()

                data = result[0]["results"][0]["metrics"]

                impressions = int(data.get("impressions", 0))
                clicks = int(data.get("clicks", 0))
                cost_micros = int(data.get("costMicros", 0))
                spend = cost_micros / 1_000_000
                conversions = int(data.get("conversions", 0))
                revenue = float(data.get("conversionsValue", 0))

                # 计算指标
                ctr = (clicks / impressions * 100) if impressions > 0 else 0
                cpc = (spend / clicks) if clicks > 0 else 0
                cpa = (spend / conversions) if conversions > 0 else 0
                roas = (revenue / spend) if spend > 0 else 0

                return {
                    "impressions": impressions,
                    "clicks": clicks,
                    "spend": round(spend, 2),
                    "conversions": conversions,
                    "ctr": round(ctr, 2),
                    "cpc": round(cpc, 2),
                    "cpa": round(cpa, 2),
                    "roas": round(roas, 2) if roas else None
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
        await self._ensure_access_token()

        operations = [{
            "update": {
                "resource_name": f"customers/{self.customer_id}/campaigns/{campaign_id}",
                "status": self.status_mapping.get(status, "PAUSED")
            },
            "update_mask": "status"
        }]

        url = f"{self.base_url}/customers/{self.customer_id}/campaigns:mutate"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={"operations": operations}) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to update status: {error_text}")
                    raise Exception(f"Failed to update status: {error_text}")

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
        await self._ensure_access_token()

        # Google Ads 需要先获取 campaign budget resource name
        # 这里简化处理，实际需要先查询 campaign 获取 budget resource

        logger.info(f"Campaign budget update: {campaign_id} -> ${budget}")

        return {
            "id": campaign_id,
            "budget": budget,
            "updated_time": datetime.now()
        }


# 使用示例
async def example_usage():
    """使用示例"""

    config = {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
        "developer_token": "YOUR_DEVELOPER_TOKEN",
        "refresh_token": "YOUR_REFRESH_TOKEN",
        "customer_id": "123-456-7890"
    }

    adapter = GoogleAdsAdapter(config)

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
