"""
广告平台适配器基类
定义所有广告平台适配器的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """广告平台适配器基类"""

    def __init__(self, platform_name: str, config: Dict[str, Any]):
        """
        初始化适配器

        Args:
            platform_name: 平台名称 (meta/google/tiktok)
            config: 平台配置
        """
        self.platform_name = platform_name
        self.config = config
        self.access_token: Optional[str] = None
        self.ad_account_id: Optional[str] = None

    # ==================== 认证模块 ====================

    @abstractmethod
    def get_oauth_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        生成 OAuth 授权 URL

        Args:
            redirect_uri: 回调地址
            state: 状态参数（防 CSRF）

        Returns:
            OAuth 授权 URL
        """
        pass

    @abstractmethod
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
                'expires_in': 5183944,
                'refresh_token': 'xxx'  # 可选
            }
        """
        pass

    @abstractmethod
    async def get_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """
        将短期 Token 换成长期 Token

        Args:
            short_lived_token: 短期 Token

        Returns:
            {
                'access_token': 'xxx',
                'token_type': 'bearer',
                'expires_in': 5183944
            }
        """
        pass

    @abstractmethod
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
        pass

    def set_access_token(self, access_token: str):
        """设置访问令牌"""
        self.access_token = access_token
        logger.info(f"{self.platform_name}: Access token set")

    def set_ad_account(self, ad_account_id: str):
        """设置当前操作的广告账户"""
        self.ad_account_id = ad_account_id
        logger.info(f"{self.platform_name}: Ad account set to {ad_account_id}")

    # ==================== Campaign 管理 ====================

    @abstractmethod
    async def create_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建广告系列

        Args:
            params: 广告系列参数

        Returns:
            {
                'id': '120212345678901234',
                'success': True
            }
        """
        pass

    @abstractmethod
    async def update_campaign(self, campaign_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新广告系列

        Args:
            campaign_id: 广告系列 ID
            params: 更新参数

        Returns:
            {'success': True}
        """
        pass

    @abstractmethod
    async def update_campaign_status(self, campaign_id: str, status: str) -> Dict[str, Any]:
        """
        更新广告系列状态

        Args:
            campaign_id: 广告系列 ID
            status: 状态 (ACTIVE/PAUSED/DELETED)

        Returns:
            {'success': True}
        """
        pass

    @abstractmethod
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
        pass

    # ==================== AdSet 管理 ====================

    @abstractmethod
    async def create_adset(self, campaign_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建广告组

        Args:
            campaign_id: 广告系列 ID
            params: 广告组参数

        Returns:
            {
                'id': '120212345678901235',
                'success': True
            }
        """
        pass

    # ==================== Creative 管理 ====================

    @abstractmethod
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
        pass

    @abstractmethod
    async def upload_video(self, video_path: str) -> Dict[str, Any]:
        """
        上传视频素材

        Args:
            video_path: 视频文件路径

        Returns:
            {
                'id': '1234567890',
                'success': True
            }
        """
        pass

    @abstractmethod
    async def create_creative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建广告创意

        Args:
            params: 创意参数

        Returns:
            {
                'id': '120212345678901236',
                'success': True
            }
        """
        pass

    @abstractmethod
    async def create_ad(self, adset_id: str, creative_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建广告

        Args:
            adset_id: 广告组 ID
            creative_id: 创意 ID
            params: 广告参数

        Returns:
            {
                'id': '120212345678901237',
                'success': True
            }
        """
        pass

    # ==================== 数据获取 ====================

    @abstractmethod
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
                        'date_start': '2026-04-01',
                        'date_stop': '2026-04-06'
                    }
                ]
            }
        """
        pass

    # ==================== 辅助方法 ====================

    def _validate_config(self, required_keys: List[str]):
        """验证配置是否包含必需的键"""
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            raise ValueError(f"{self.platform_name}: Missing required config keys: {missing_keys}")

    def _ensure_authenticated(self):
        """确保已设置访问令牌"""
        if not self.access_token:
            raise Exception(f"{self.platform_name}: Access token not set. Call set_access_token() first.")

    def _ensure_ad_account(self):
        """确保已设置广告账户"""
        if not self.ad_account_id:
            raise Exception(f"{self.platform_name}: Ad account not set. Call set_ad_account() first.")
