"""应用配置管理"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 基础配置
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8020

    # JWT 配置（复用 backend 的 JWT secret）
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

    # 后端服务（用于 MCP 工具调用）
    BACKEND_BASE_URL: str = "http://localhost:8010"

    # OpenAI Agents SDK
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    OPENAI_AGENTS_MODEL: str = "deepseek/deepseek-v4-pro"
    OPENAI_AGENTS_API: str = "responses"

    # 数据库路径
    AGENT_TASK_DB: str = "runtime/agent/tasks.db"
    AGENT_SESSION_DB: str = "runtime/agent/sessions.db"

    # Runtime 配置
    RUNTIME_DIR: str = "runtime/sessions"
    SKILLS_DIR: str = "runtime/skills"
    SANDBOX_DIR: str = "runtime/agent/sandbox"
    AGENT_TRACING_ENABLED: bool = True

    # CORS
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173,http://localhost:3010,http://127.0.0.1:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
