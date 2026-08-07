from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from loguru import logger
from datetime import datetime
from time import perf_counter
from uuid import uuid4

from app.config.settings import get_settings
from app.config.logging import setup_logging
from app.config.metrics import (
    CONTENT_TYPE_LATEST,
    HTTP_DURATION,
    HTTP_REQUESTS,
    METRICS_AVAILABLE,
    generate_latest,
)
from app.api.v1.router import api_router
from app.schemas.base import ErrorResponse, ErrorDetail

settings = get_settings()

# 初始化日志系统
log_file = settings.LOG_FILE if settings.LOG_FILE else None
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_file=log_file,
    json_logs=settings.LOG_FORMAT.lower() == "json",
    console=settings.LOG_OUTPUT.lower() in {"console", "both"},
    service=settings.LOG_SERVICE,
    role=settings.LOG_ROLE,
    environment=settings.APP_ENV,
)

allow_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3010",
    "http://127.0.0.1:3010",
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
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
    if len(request_id) > 128:
        request_id = f"req_{uuid4().hex}"
    request.state.request_id = request_id
    started = perf_counter()
    with logger.contextualize(request_id=request_id):
        try:
            response = await call_next(request)
        except Exception:
            duration = perf_counter() - started
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")
            HTTP_REQUESTS.labels(settings.LOG_SERVICE, request.method, route_path, "5xx").inc()
            HTTP_DURATION.labels(settings.LOG_SERVICE, request.method, route_path).observe(duration)
            logger.bind(event="http.request.failed").exception(
                "HTTP request failed: method={} path={} duration_ms={}",
                request.method,
                request.url.path,
                int((perf_counter() - started) * 1000),
            )
            raise
        response.headers["X-Request-ID"] = request_id
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        status_class = f"{response.status_code // 100}xx"
        duration = perf_counter() - started
        HTTP_REQUESTS.labels(settings.LOG_SERVICE, request.method, route_path, status_class).inc()
        HTTP_DURATION.labels(settings.LOG_SERVICE, request.method, route_path).observe(duration)
        access_logger = logger.bind(event="http.request.completed")
        access_args = (
            request.method,
            route_path,
            response.status_code,
            int((perf_counter() - started) * 1000),
        )
        if route_path in {"/health", "/metrics"}:
            access_logger.debug(
                "HTTP request completed: method={} route={} status={} duration_ms={}",
                *access_args,
            )
        else:
            access_logger.info(
                "HTTP request completed: method={} route={} status={} duration_ms={}",
                *access_args,
            )
        return response


# 路由
app.include_router(api_router)


@app.get("/metrics", include_in_schema=False)
async def metrics():
    if not METRICS_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "reason": "prometheus-client is not installed"},
        )
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "demo_mode": settings.DEMO_MODE,
        "timestamp": int(datetime.now().timestamp()),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.bind(event="http.unhandled_exception").exception("Unhandled HTTP exception")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(code="INTERNAL_ERROR", message=str(exc))
        ).model_dump(),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
