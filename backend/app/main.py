from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from datetime import datetime

from app.config.settings import get_settings
from app.api.v1.router import api_router
from app.schemas.base import ErrorResponse, ErrorDetail

settings = get_settings()

app = FastAPI(
    title="Game Marketing Pro API",
    description="AD Agent Demo 后端服务",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "demo_mode": settings.DEMO_MODE,
        "timestamp": int(datetime.now().timestamp()),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(code="INTERNAL_ERROR", message=str(exc))
        ).model_dump(),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
