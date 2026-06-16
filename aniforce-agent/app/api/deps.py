"""API 依赖注入"""
from fastapi import HTTPException, status
from app.core.context import get_user_context


def get_current_user() -> dict:
    """获取当前用户（必须已认证）"""
    user = get_user_context()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_id() -> str:
    """获取当前用户 ID"""
    user = get_current_user()
    return user["id"]
