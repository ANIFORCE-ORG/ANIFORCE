from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.config.settings import get_settings
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.base import ResponseBase
from app.repositories.factory import get_user_repo

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
async def login(
    req: LoginRequest,
    user_repo = Depends(get_user_repo)
):
    settings = get_settings()
    
    # 查询用户
    user = await user_repo.get_by_email(req.email)
    if not user:
        if settings.DEMO_MODE:
            user = {"id": "user_test_001", "email": req.email, "name": "测试用户"}
            access_token, refresh_token = _create_token(user["id"], user["email"], user["name"])
            return ResponseBase(
                data=TokenResponse(
                    user=UserResponse(id=user["id"], email=user["email"], name=user["name"]),
                    access_token=access_token,
                    refresh_token=refresh_token,
                )
            )
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 验证密码
    if not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 生成 token
    access_token, refresh_token = _create_token(user["id"], user["email"], user["name"])
    
    return ResponseBase(
        data=TokenResponse(
            user=UserResponse(id=user["id"], email=user["email"], name=user["name"]),
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )


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
