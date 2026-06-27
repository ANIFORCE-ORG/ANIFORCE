"""JWT 鉴权（从 Authorization header 解析 user）"""

from time import perf_counter

from fastapi import Request, HTTPException, status
from jose import JWTError, jwt
from loguru import logger

from app.config.settings import get_settings


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user(request: Request) -> dict:
    """从 JWT 解析当前用户（必须已认证）"""
    auth_start = perf_counter()
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    try:
        jwt_start = perf_counter()
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

    logger.info(
        "[PERF][agent_first_token] agent_api.auth total_ms={} jwt_decode_ms={} user_id={}",
        _elapsed_ms(auth_start),
        _elapsed_ms(jwt_start),
        user_id,
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
