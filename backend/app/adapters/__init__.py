"""
广告平台适配器模块
支持多渠道广告平台的统一接口封装
"""

from .base import BaseAdapter
from .meta_ads import MetaAdsAdapter

__all__ = [
    'BaseAdapter',
    'MetaAdsAdapter',
]
