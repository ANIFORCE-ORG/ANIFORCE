"""JWT 鉴权（从 Authorization header 解析 user）"""

from fastapi import Request, HTTPException, status
from jose import JWTError, jwt

from app.config.settings import get_settings


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user(request: Request) -> dict:
    """从 JWT 解析当前用户（必须已认证）"""
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 兼容 sub / user_id 两种字段
    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user id",
        )

    return {
        "id": str(user_id),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "token": token,
    }


async def get_current_user_id(request: Request) -> str:
    user = await get_current_user(request)
    return user["id"]
