"""请求上下文管理（异步安全）"""
from contextvars import ContextVar
from typing import Optional

# 用户上下文
_user_context: ContextVar[Optional[dict]] = ContextVar("user_context", default=None)

# JWT Token 上下文（用于 HTTP MCP 透传）
_jwt_token_context: ContextVar[Optional[str]] = ContextVar("jwt_token", default=None)


def set_user_context(user: dict):
    """设置用户上下文"""
    _user_context.set(user)


def get_user_context() -> Optional[dict]:
    """获取用户上下文"""
    return _user_context.get()


def clear_user_context():
    """清除用户上下文"""
    _user_context.set(None)


def set_jwt_token(token: str):
    """设置 JWT Token（用于 HTTP MCP 透传）"""
    _jwt_token_context.set(token)


def get_jwt_token() -> Optional[str]:
    """获取 JWT Token"""
    return _jwt_token_context.get()


def clear_jwt_token():
    """清除 JWT Token"""
    _jwt_token_context.set(None)
