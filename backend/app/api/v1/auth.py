from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from jose import jwt
from app.config.settings import get_settings
from app.core.security import hash_password, verify_password
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse, UpdateNameRequest, UpdatePasswordRequest
from app.schemas.base import ResponseBase
from app.repositories.factory import get_user_repo

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
        raise HTTPException(status_code=404, detail="该邮箱尚未注册")
    
    # 验证密码
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="密码错误")
    
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
async def register(
    request: RegisterRequest,
    user_repo = Depends(get_user_repo)
):
    """用户注册"""
    print(f"[DEBUG] 接收到注册请求")
    print(f"[DEBUG] request 对象: {request}")
    print(f"[DEBUG] request.password type: {type(request.password)}")
    print(f"[DEBUG] request.password repr: {repr(request.password)}")
    print(f"[DEBUG] request.password len: {len(request.password)}")
    
    settings = get_settings()
    
    # Demo 模式
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
    
    # 生产模式：真实注册
    # 1. 检查邮箱是否已存在
    existing_user = await user_repo.get_by_email(request.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
    
    # 2. 验证密码长度（bcrypt 限制为 72 字节）
    password_bytes = request.password.encode('utf-8')
    print(f"[DEBUG] 密码长度: {len(request.password)}, 字节长度: {len(password_bytes)}")
    print(f"[DEBUG] 密码内容: {repr(request.password)}")
    
    if len(password_bytes) > 72:
        raise HTTPException(status_code=400, detail="密码过长，请使用不超过 72 个字符的密码")
    
    # 3. 加密密码
    try:
        password_hash = hash_password(request.password)
        print(f"[DEBUG] 密码加密成功")
    except Exception as e:
        print(f"[DEBUG] 密码加密失败: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"密码加密失败: {str(e)}")
    
    # 3. 创建用户
    user = await user_repo.create(
        email=request.email,
        password_hash=password_hash,
        name=request.name
    )
    
    # 4. 生成 token
    access_token, refresh_token = _create_token(user["id"], user["email"], user["name"])
    
    return ResponseBase(
        data=TokenResponse(
            user=UserResponse(id=user["id"], email=user["email"], name=user["name"]),
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )
