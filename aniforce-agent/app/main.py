"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings, init_task_db
from app.middleware import AuthMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_task_db()
    yield
    # 关闭时清理资源（暂无需要清理的资源）


# 创建 FastAPI 应用
settings = get_settings()
app = FastAPI(
    title="ANIFORCE Agent Service",
    description="Claude Agent SDK 驱动的智能 Agent 服务",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# 配置 CORS
origins = settings.CORS_ALLOW_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册认证中间件
app.add_middleware(AuthMiddleware)


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "service": "aniforce-agent"}


@app.get("/health")
async def health():
    """健康检查（详细）"""
    return {
        "status": "healthy",
        "service": "aniforce-agent",
        "version": "1.0.0",
    }
