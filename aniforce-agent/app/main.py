"""OpenAI Agent Service 主入口"""

import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config.settings import settings
from app.agent.openai_adapter import OpenAISDKAdapter
from app.runtime.service import AgentRuntime
from app.runtime.migrations import RuntimeSchemaMigrator
from app.mcp_server import get_mcp_starlette_app, mcp
from app.core.errors import AppError, get_http_status
from app.core.logging import settings_logging_values, setup_logging
from app.core.sdk_tracing import configure_sdk_tracing, shutdown_sdk_tracing


setup_logging(**settings_logging_values(settings))

# 全局实例
_adapter: OpenAISDKAdapter | None = None
_runtime: AgentRuntime | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务生命周期"""
    global _adapter, _runtime

    # 启动时初始化
    settings.validate_for_startup()
    Path("data").mkdir(parents=True, exist_ok=True)
    configure_sdk_tracing(settings)

    _adapter = OpenAISDKAdapter(
        model=settings.OPENAI_AGENTS_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        enable_tracing=settings.AGENT_TRACING_ENABLED,
        api_mode=settings.OPENAI_AGENTS_API,
        trace_include_sensitive_data=settings.AGENT_TRACE_INCLUDE_SENSITIVE_DATA,
    )

    _runtime = AgentRuntime(
        adapter=_adapter,
        agent_runtime_db_url=settings.AGENT_RUNTIME_DB_URL,
        enable_tracing=settings.AGENT_TRACING_ENABLED,
    )
    runtime_engine = _adapter._get_agent_db_engine(settings.AGENT_RUNTIME_DB_URL)
    await RuntimeSchemaMigrator(runtime_engine).migrate()

    logger.info(f"OpenAI Agent Service started on {settings.HOST}:{settings.PORT}")
    logger.info(f"Model: {settings.OPENAI_AGENTS_MODEL}")
    logger.info(f"Agent API: {settings.OPENAI_AGENTS_API}")

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        logger.info("FastMCP session manager started")
        yield

    # 关闭时清理
    if _adapter:
        await _adapter.close()
    shutdown_sdk_tracing()
    logger.info("OpenAI Agent Service shutting down")


app = FastAPI(
    title="OpenAI Agent Service",
    version="1.0.0",
    lifespan=lifespan,
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
            logger.bind(event="http.request.failed").exception(
                "HTTP request failed: method={} path={} duration_ms={}",
                request.method,
                request.url.path,
                int((perf_counter() - started) * 1000),
            )
            raise
        response.headers["X-Request-ID"] = request_id
        route = request.scope.get("route")
        logger.bind(event="http.request.completed").info(
            "HTTP request completed: method={} route={} status={} duration_ms={}",
            request.method,
            getattr(route, "path", request.url.path),
            response.status_code,
            int((perf_counter() - started) * 1000),
        )
        return response


# 全局异常处理器
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """AppError 异常处理器"""
    return JSONResponse(
        status_code=get_http_status(exc.code),
        content=exc.to_dict(),
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "openai-agent-service",
        "model": settings.OPENAI_AGENTS_MODEL,
        "api": settings.OPENAI_AGENTS_API,
    }


# 路由
from app.api.runtime_runs import router as runtime_runs_router
from app.api.runtime_sessions import router as runtime_sessions_router
from app.api.runtime_checkpoints import router as runtime_checkpoints_router

app.include_router(runtime_runs_router, prefix="/api")
app.include_router(runtime_sessions_router, prefix="/api")
app.include_router(runtime_checkpoints_router, prefix="/api")

# 挂载 MCP server（路径 B：agent-service 内部的 FastMCP server）
# Agent 通过 MCPServerStreamableHttp 连本进程的 /mcp 端点
# FastMCP 的 streamable_http_app 是独立 starlette app，路由为 /mcp，需 mount 到根路径
app.mount("/", get_mcp_starlette_app(), name="mcp_server")
