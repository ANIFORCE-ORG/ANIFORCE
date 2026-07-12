"""应用配置管理"""
import os
from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings


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

    # Agents SDK runtime database（调试 SQLite，生产换 PostgreSQL）
    AGENT_RUNTIME_DB_URL: str = "sqlite+aiosqlite:///data/agent.db"
    AGENT_TRACING_ENABLED: bool = True

    # CORS
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173,http://localhost:3010,http://127.0.0.1:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}

    def validate_for_startup(self) -> None:
        """Reject unsafe or incomplete production configuration."""
        errors: list[str] = []
        parsed_backend = urlparse(self.BACKEND_BASE_URL)
        if parsed_backend.scheme not in {"http", "https"} or not parsed_backend.netloc:
            errors.append("BACKEND_BASE_URL must be an absolute HTTP(S) URL")

        workers = int(os.getenv("WEB_CONCURRENCY") or os.getenv("UVICORN_WORKERS") or "1")
        if workers > 1 and self.AGENT_RUNTIME_DB_URL.startswith("sqlite"):
            errors.append("SQLite runtime storage does not support multiple workers")

        if not self.DEBUG:
            if self.JWT_SECRET == "change-me-in-production" or len(self.JWT_SECRET) < 32:
                errors.append("JWT_SECRET must be a non-default value of at least 32 characters")
            if not self.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY is required")
            if not self.OPENAI_AGENTS_MODEL.strip():
                errors.append("OPENAI_AGENTS_MODEL is required")

        if errors:
            raise ValueError("Invalid Agent service configuration: " + "; ".join(errors))


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
