"""API 依赖注入（兼容旧引用）"""
from app.auth import get_current_user, get_current_user_id

__all__ = ["get_current_user", "get_current_user_id"]
