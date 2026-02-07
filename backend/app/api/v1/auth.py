from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from jose import jwt
from app.config.settings import get_settings
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.base import ResponseBase

router = APIRouter(prefix="/auth", tags=["认证"])


def _create_token(user_id: str, email: str, name: str) -> tuple[str, str]:
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "name": name, "exp": expire}
    access_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    refresh_token = jwt.encode(
        {**payload, "exp": expire + timedelta(days=7)},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return access_token, refresh_token


@router.post("/login", response_model=ResponseBase[TokenResponse])
async def login(request: LoginRequest):
    """用户登录 — Demo 模式下任意账号均可登录"""
    settings = get_settings()
    if settings.DEMO_MODE:
        user = UserResponse(id="demo-user-001", email=request.email, name="Demo User")
        access_token, refresh_token = _create_token(user.id, user.email, user.name)
        return ResponseBase(
            data=TokenResponse(
                user=user,
                access_token=access_token,
                refresh_token=refresh_token,
            )
        )
    # 生产模式：查询数据库验证
    raise NotImplementedError("生产模式认证尚未实现")


@router.post("/register", response_model=ResponseBase[TokenResponse], status_code=201)
async def register(request: RegisterRequest):
    """用户注册"""
    settings = get_settings()
    if settings.DEMO_MODE:
        user = UserResponse(id="demo-user-001", email=request.email, name=request.name)
        access_token, refresh_token = _create_token(user.id, user.email, user.name)
        return ResponseBase(
            data=TokenResponse(
                user=user,
                access_token=access_token,
                refresh_token=refresh_token,
            )
        )
    raise NotImplementedError("生产模式注册尚未实现")
