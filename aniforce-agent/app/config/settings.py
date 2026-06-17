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
    
    # JWT 配置
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 小时
    
    # 内部服务通信
    INTERNAL_TOKEN: str = "change-me-in-production"
    
    # 后端服务
    BACKEND_URL: str = "http://localhost:8010"
    
    # Claude API
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_AUTH_TOKEN: str = ""  # Claude SDK 需要
    ANTHROPIC_BASE_URL: str = ""  # 可选：代理 URL
    CLAUDE_AGENT_MODEL: str = "claude-opus-4"  # 默认模型
    
    # 数据库路径
    TASK_DB_PATH: str = "runtime/agent/tasks.db"
    SESSION_DB_PATH: str = "runtime/agent/sessions.db"
    
    # Runtime 配置
    RUNTIME_DIR: str = "runtime/sessions"
    SKILLS_SOURCE_DIR: str = "app/skills"
    SKILL_SOURCE_DIR: str = "app/skills"  # 兼容性别名
    
    # CORS
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000,http://localhost:3010"
    
    model_config = {"env_file": ".env"}


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
