"""
广告平台连接器模块
"""

from .platform_interface import PlatformAdapter
from .meta_adapter import MetaAdsAdapter
from .google_adapter import GoogleAdsAdapter
from .tiktok_adapter import TikTokAdsAdapter

__all__ = [
    'PlatformAdapter',
    'MetaAdsAdapter',
    'GoogleAdsAdapter',
    'TikTokAdsAdapter'
]
