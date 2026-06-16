"""请求上下文管理（异步安全）"""
from contextvars import ContextVar
from typing import Optional

# 用户上下文
_user_context: ContextVar[Optional[dict]] = ContextVar("user_context", default=None)


def set_user_context(user: dict):
    """设置用户上下文"""
    _user_context.set(user)


def get_user_context() -> Optional[dict]:
    """获取用户上下文"""
    return _user_context.get()


def clear_user_context():
    """清除用户上下文"""
    _user_context.set(None)
