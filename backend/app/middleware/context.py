"""
请求上下文中间件

自动为每个请求设置上下文，包括：
- 用户信息（从 JWT Token 解析）
- 请求 ID（用于日志追踪）
- 租户 ID（多租户场景）

参考: AI2Earn 的 RequestContextInterceptor
"""

from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from jose import jwt, JWTError
from loguru import logger

from app.core.context import set_request_context, UserContext
from app.config.settings import get_settings


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    请求上下文中间件
    
    职责：
    1. 生成或提取 request_id
    2. 解析 JWT Token 获取用户信息（可选）
    3. 设置上下文变量
    4. 在响应中返回 request_id
    """
    
    async def dispatch(self, request: Request, call_next):
        # 1. 生成或获取 request_id（优先使用客户端传递的）
        request_id = request.headers.get("x-request-id")
        if not request_id:
            request_id = str(uuid4())
        
        # 2. 解析用户信息（可选，不影响公开端点）
        user = self._extract_user(request)
        
        # 3. 提取租户 ID（多租户场景）
        tenant_id = request.headers.get("x-tenant-id")
        
        # 4. 设置上下文
        set_request_context({
            "user": user,
            "request_id": request_id,
            "tenant_id": tenant_id,
        })
        
        # 5. 执行请求
        response: Response = await call_next(request)
        
        # 6. 在响应中返回 request_id（便于前端追踪）
        response.headers["x-request-id"] = request_id
        
        return response
    
    def _extract_user(self, request: Request) -> UserContext | None:
        """
        从请求中提取用户信息
        
        尝试解析 Authorization header 中的 JWT Token
        如果失败（无 token 或 token 无效），返回 None
        这样公开端点仍然可以正常访问
        """
        settings = get_settings()
        
        # 获取 Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # 去掉 "Bearer " 前缀
        
        try:
            # 解析 JWT Token
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            return UserContext(
                id=user_id,
                email=payload.get("email", ""),
                name=payload.get("name", ""),
                type=payload.get("type", "user"),
            )
            
        except JWTError as e:
            # Token 无效，记录日志但不抛出异常
            # 这样公开端点仍然可以访问
            logger.debug(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error extracting user from token: {e}")
            return None
