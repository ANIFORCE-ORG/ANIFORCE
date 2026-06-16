"""JWT 认证和授权"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.config.settings import get_settings


class AuthError(Exception):
    """认证错误"""
    pass


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Token"""
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """解析 JWT Token"""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise AuthError(f"Invalid token: {str(e)}")


def verify_internal_token(token: str) -> bool:
    """验证内部服务 Token"""
    settings = get_settings()
    return token == settings.INTERNAL_TOKEN
