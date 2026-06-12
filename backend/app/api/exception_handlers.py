"""
全局异常处理器

遵循 Block 0 规范：
- 捕获 AppError 并返回友好错误
- 捕获未知异常并记录日志
- 不暴露内部堆栈给用户
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger

from ..agent_platform.errors import AppError, get_http_status


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """AppError 异常处理器"""
    logger.bind(
        path=request.url.path,
        method=request.method,
    ).warning(
        f"AppError: {exc.code.value} - {exc.message}",
        extra={"error_data": exc.data}
    )
    
    return JSONResponse(
        status_code=get_http_status(exc.code),
        content={
            "error": {
                "code": exc.code.value,
                "message": exc.message,
                "category": exc.category.value,
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    logger.bind(
        path=request.url.path,
        method=request.method,
    ).exception(
        f"Unhandled exception: {type(exc).__name__}",
    )
    
    # 不暴露内部堆栈给用户
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal error occurred",
                "category": "runtime",
            }
        },
    )
