from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from datetime import datetime

from app.config.settings import get_settings
from app.config.logging import setup_logging
from app.api.v1.router import api_router
from app.schemas.base import ErrorResponse, ErrorDetail
from app.api.exception_handlers import app_error_handler, general_exception_handler
from app.agent_platform.errors import AppError

settings = get_settings()

# 初始化日志系统
log_file = settings.LOG_FILE if settings.LOG_FILE else None
setup_logging(
    log_level=settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else "INFO",
    log_file=log_file
)

allow_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3010",
]
if settings.CORS_ALLOW_ORIGINS.strip():
    allow_origins = [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

app = FastAPI(
    title="ANIFORCE API",
    description="AD Agent Demo 后端服务",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3010", "http://127.0.0.1:3010", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 异常处理器
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 路由
app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "demo_mode": settings.DEMO_MODE,
        "timestamp": int(datetime.now().timestamp()),
    }


# 全局异常处理器已在上面注册


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
