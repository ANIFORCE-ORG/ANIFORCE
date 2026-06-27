"""JWT 认证和授权"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.config.settings import get_settings


class AuthError(Exception):
    """认证错误"""
    pass


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Token（用 sub 字段，对齐 backend auth.py）"""
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解析 JWT Token"""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise AuthError(f"Invalid token: {str(e)}")
