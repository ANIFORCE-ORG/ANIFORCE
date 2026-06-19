from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config.settings import get_settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """获取当前用户 — Demo 模式或开发环境下返回固定用户"""
    settings = get_settings()

    # Demo 模式或没有提供认证信息时，返回测试用户（用于开发）
    if settings.DEMO_MODE or credentials is None:
        return {
            "id": "user_test_001",
            "email": "test@animagus.com",
            "name": "测试用户",
        }

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证信息",
            )
        return {
            "id": user_id,
            "email": payload.get("email", ""),
            "name": payload.get("name", ""),
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证信息已过期或无效",
        )
