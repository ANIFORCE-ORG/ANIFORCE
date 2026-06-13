"""
MCP 服务鉴权中间件

用于保护 MCP 服务端点，验证客户端传递的 JWT Token
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import HTTPException, status
from jose import jwt, JWTError
from loguru import logger

from app.config.settings import get_settings


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """
    MCP 服务鉴权中间件
    
    职责：
    1. 验证 Authorization header
    2. 解析 JWT Token
    3. 设置 request.state.user（供 MCP 工具使用）
    
    使用场景：
    - 独立的 MCP 服务（FastAPI App）
    - 需要验证来自 Agent 的请求
    """
    
    async def dispatch(self, request: Request, call_next):
        # 提取 Authorization header
        auth_header = request.headers.get("authorization", "")
        
        if not auth_header.startswith("Bearer "):
            logger.warning(f"MCP request without authorization: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = auth_header[7:]  # 去掉 "Bearer " 前缀
        settings = get_settings()
        
        try:
            # 解析 JWT Token
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload: missing user_id"
                )
            
            # 将用户信息存入 request.state（供 MCP 工具获取）
            request.state.user_id = user_id
            request.state.user_type = payload.get("type", "user")
            request.state.user_email = payload.get("email", "")
            
            logger.debug(f"MCP request authenticated: user_id={user_id}")
            
        except JWTError as e:
            logger.warning(f"Invalid JWT token in MCP request: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error validating MCP token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal authentication error"
            )
        
        response = await call_next(request)
        return response
