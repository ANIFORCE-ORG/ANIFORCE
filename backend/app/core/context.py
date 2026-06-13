"""
请求上下文管理

使用 ContextVar 在异步调用链中传递请求上下文信息，
无需手动在每个函数中传递 user_id、request_id 等参数。

参考: AI2Earn 的 AsyncLocalStorage 模式
"""

from contextvars import ContextVar
from typing import Optional, TypedDict
from fastapi import HTTPException


class UserContext(TypedDict, total=False):
    """用户上下文"""
    id: str
    email: str
    name: str
    type: str  # user | admin


class RequestContext(TypedDict, total=False):
    """请求上下文"""
    user: Optional[UserContext]
    request_id: str
    tenant_id: Optional[str]


# 定义上下文变量（线程安全，异步安全）
_request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    "_request_context", 
    default=None
)


def set_request_context(ctx: RequestContext) -> None:
    """
    设置请求上下文
    
    通常由中间件调用，业务代码不应直接调用
    """
    _request_context.set(ctx)


def get_request_context() -> RequestContext:
    """
    获取请求上下文
    
    Raises:
        RuntimeError: 上下文未设置时抛出
    """
    ctx = _request_context.get()
    if ctx is None:
        raise RuntimeError("Request context not set. Did you forget to add RequestContextMiddleware?")
    return ctx


def get_current_user() -> UserContext:
    """
    从上下文获取当前用户
    
    这是最常用的快捷方法，可在任何地方调用
    
    Raises:
        HTTPException(401): 用户未登录时抛出
        
    Example:
        >>> user = get_current_user()
        >>> print(user["id"])
    """
    ctx = get_request_context()
    user = ctx.get("user")
    
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    return user


def get_current_user_optional() -> Optional[UserContext]:
    """
    从上下文获取当前用户（可选）
    
    用于公开端点，可能有用户也可能没有
    
    Returns:
        UserContext | None: 用户信息，未登录时返回 None
        
    Example:
        >>> user = get_current_user_optional()
        >>> if user:
        >>>     print(f"Welcome {user['name']}")
    """
    try:
        ctx = get_request_context()
        return ctx.get("user")
    except RuntimeError:
        return None


def get_request_id() -> str:
    """
    获取当前请求 ID
    
    用于日志追踪、问题排查
    """
    ctx = get_request_context()
    return ctx.get("request_id", "unknown")


def get_tenant_id() -> Optional[str]:
    """
    获取当前租户 ID（多租户场景）
    
    单租户场景下返回 None
    """
    ctx = get_request_context()
    return ctx.get("tenant_id")


# 便捷别名
get_user = get_current_user
get_user_optional = get_current_user_optional
