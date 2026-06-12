"""用户信息管理相关接口"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import hash_password, verify_password
from app.schemas.auth import UserResponse, UpdateNameRequest, UpdatePasswordRequest
from app.schemas.base import ResponseBase
from app.repositories.factory import get_user_repo
from app.api.deps import get_current_user

router = APIRouter(prefix="/user", tags=["用户管理"])


@router.put("/name", response_model=ResponseBase[UserResponse])
async def update_name(
    request: UpdateNameRequest,
    current_user: dict = Depends(get_current_user),
    user_repo = Depends(get_user_repo)
):
    """更新用户名"""
    if not request.name or not request.name.strip():
        raise HTTPException(status_code=400, detail="用户名不能为空")
    
    # 更新用户名
    user = await user_repo.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 执行更新
    updated_user = await user_repo.update(
        user_id=current_user["id"],
        name=request.name.strip()
    )
    
    return ResponseBase(
        data=UserResponse(
            id=updated_user["id"],
            email=updated_user["email"],
            name=updated_user["name"]
        ),
        message="用户名更新成功"
    )


@router.put("/password", response_model=ResponseBase[dict])
async def update_password(
    request: UpdatePasswordRequest,
    current_user: dict = Depends(get_current_user),
    user_repo = Depends(get_user_repo)
):
    """更新密码"""
    # 验证新密码长度
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度至少为 6 个字符")
    
    # 获取用户信息
    user = await user_repo.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 验证当前密码
    if not verify_password(request.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="当前密码错误")
    
    # 加密新密码
    new_password_hash = hash_password(request.new_password)
    
    # 更新密码
    await user_repo.update(
        user_id=current_user["id"],
        password_hash=new_password_hash
    )
    
    return ResponseBase(
        data={"success": True},
        message="密码更新成功"
    )
