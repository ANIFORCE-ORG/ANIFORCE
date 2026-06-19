"""OpenAI Agent Service 主入口"""

import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config.settings import settings
from app.agent.openai_adapter import OpenAISDKAdapter
from app.agent.runtime import AgentRuntime
from app.repositories.sqlite_agent_task_repo import SQLiteAgentTaskRepository
from app.services.agent_task_service import AgentTaskService
from app.mcp_server import get_mcp_starlette_app, mcp
from app.core.errors import AppError, get_http_status


# 全局实例
_adapter: OpenAISDKAdapter | None = None
_repo: SQLiteAgentTaskRepository | None = None
_runtime: AgentRuntime | None = None
_service: AgentTaskService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务生命周期"""
    global _adapter, _repo, _runtime, _service

    # 启动时初始化
    Path(settings.RUNTIME_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.SKILLS_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.SANDBOX_DIR).mkdir(parents=True, exist_ok=True)

    _adapter = OpenAISDKAdapter(
        model=settings.OPENAI_AGENTS_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        enable_tracing=settings.AGENT_TRACING_ENABLED,
        skills_dir=settings.SKILLS_DIR,
        sandbox_dir=settings.SANDBOX_DIR,
    )

    _repo = SQLiteAgentTaskRepository(db_path=settings.AGENT_TASK_DB)

    _runtime = AgentRuntime(
        adapter=_adapter,
        repo=_repo,
        session_db_path=settings.AGENT_SESSION_DB,
        enable_tracing=settings.AGENT_TRACING_ENABLED,
    )

    _service = AgentTaskService(_repo, _runtime)

    logger.info(f"OpenAI Agent Service started on {settings.HOST}:{settings.PORT}")
    logger.info(f"Model: {settings.OPENAI_AGENTS_MODEL}")

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        logger.info("FastMCP session manager started")
        yield

    # 关闭时清理
    logger.info("OpenAI Agent Service shutting down")


app = FastAPI(
    title="OpenAI Agent Service",
    version="1.0.0",
    lifespan=lifespan,
)

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
    }


# 路由
from app.api.runs import router as runs_router
from app.api.sessions import router as sessions_router
from app.api.tasks import router as tasks_router

app.include_router(runs_router, prefix="/api/agent")
app.include_router(sessions_router, prefix="/api/agent")
app.include_router(tasks_router, prefix="/api/agent")

# 挂载 MCP server（路径 B：agent-service 内部的 FastMCP server）
# Agent 通过 MCPServerStreamableHttp 连本进程的 /mcp 端点
# FastMCP 的 streamable_http_app 是独立 starlette app，路由为 /mcp，需 mount 到根路径
app.mount("/", get_mcp_starlette_app(), name="mcp_server")