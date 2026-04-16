"""
广告平台适配器统一接口定义
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime


class PlatformAdapter(ABC):
    """广告平台适配器基类"""

    @abstractmethod
    async def authenticate(self, credentials: Dict) -> Dict:
        """
        认证并获取 Access Token

        Args:
            credentials: 认证凭据（不同平台格式不同）

        Returns:
            {
                "access_token": str,
                "expires_in": int,
                "token_type": str
            }
        """
        pass

    @abstractmethod
    async def create_campaign(self, params: Dict) -> Dict:
        """
        创建广告系列

        Args:
            params: {
                "name": str,
                "objective": str,  # CONVERSIONS/TRAFFIC/AWARENESS
                "status": str,  # ACTIVE/PAUSED
                "budget": float,
                "budget_type": str,  # DAILY/LIFETIME
                "start_time": Optional[datetime],
                "end_time": Optional[datetime]
            }

        Returns:
            {
                "id": str,
                "name": str,
                "status": str,
                "created_time": datetime
            }
        """
        pass

    @abstractmethod
    async def create_adset(self, campaign_id: str, params: Dict) -> Dict:
        """
        创建广告组

        Args:
            campaign_id: 广告系列 ID
            params: {
                "name": str,
                "status": str,
                "budget": Optional[float],
                "targeting": Dict,  # 定向参数
                "bid_strategy": str,  # LOWEST_COST/COST_CAP
                "bid_amount": Optional[float]
            }

        Returns:
            {
                "id": str,
                "campaign_id": str,
                "name": str,
                "status": str
            }
        """
        pass

    @abstractmethod
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
            {
                "id": str,
                "adset_id": str,
                "creative_id": str,
                "name": str,
                "status": str
            }
        """
        pass

    @abstractmethod
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
            {
                "id": str,
                "type": str,
                "url": str
            }
        """
        pass

    @abstractmethod
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
            {
                "impressions": int,
                "clicks": int,
                "spend": float,
                "conversions": int,
                "ctr": float,
                "cpc": float,
                "cpa": float,
                "roas": Optional[float]
            }
        """
        pass

    @abstractmethod
    async def update_campaign_status(self, campaign_id: str, status: str) -> Dict:
        """
        更新广告系列状态

        Args:
            campaign_id: 广告系列 ID
            status: ACTIVE/PAUSED/DELETED

        Returns:
            {
                "id": str,
                "status": str,
                "updated_time": datetime
            }
        """
        pass

    @abstractmethod
    async def update_budget(self, campaign_id: str, budget: float) -> Dict:
        """
        更新预算

        Args:
            campaign_id: 广告系列 ID
            budget: 新预算金额

        Returns:
            {
                "id": str,
                "budget": float,
                "updated_time": datetime
            }
        """
        pass
