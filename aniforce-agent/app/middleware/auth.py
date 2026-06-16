"""JWT 认证中间件"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.auth import decode_access_token, AuthError
from app.core.context import set_user_context, clear_user_context


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT 认证中间件（自动解析 Token 到上下文）"""
    
    async def dispatch(self, request: Request, call_next):
        # 清除旧的上下文
        clear_user_context()
        
        # 提取 Authorization header
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = decode_access_token(token)
                # 提取用户信息并存入上下文
                user = {
                    "id": payload.get("sub"),
                    "email": payload.get("email"),
                    "name": payload.get("name"),
                }
                set_user_context(user)
            except AuthError:
                # Token 无效，但不阻塞请求（由路由层决定是否需要认证）
                pass
        
        response = await call_next(request)
        return response
