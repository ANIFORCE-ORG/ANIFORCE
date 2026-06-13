from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DEMO_MODE: bool = True
    DEBUG: bool = False

    CORS_ALLOW_ORIGINS: str = ""

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # 模拟延迟（秒）
    DEMO_DELAY_ANALYSIS: float = 2.0
    DEMO_DELAY_MATERIAL: float = 4.0
    DEMO_DELAY_CAMPAIGN: float = 2.0
    DEMO_MONITOR_INTERVAL: float = 3.0

    # 数据库（Demo 模式下可不配置）
    DATABASE_URL: str = ""  # 留空则使用 SQLite
    MONGODB_URL: str = ""
    MONGODB_DB_NAME: str = "animagus"
    REDIS_URL: str = ""

    # 外部服务
    OPENAI_API_KEY: str = ""
    
    # Meta OAuth 配置
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_SCOPES: str = ""
    
    # 服务地址配置（根据运行模式自动切换）
    # Local 模式: http://localhost:3010 / http://localhost:8010
    # Cloud 模式: http://8.148.151.36:3010 / https://8.148.151.36:8010
    FRONTEND_BASE_URL: str = "http://localhost:3010"
    BACKEND_BASE_URL: str = "http://localhost:8010"
    
    # OAuth 回调地址配置（用于第三方平台 OAuth 重定向）
    # 默认使用生产域名，本地开发时可设置为 http://localhost:8010
    OAUTH_REDIRECT_BASE_URL: str = "https://www.aniforce.cc"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = ""  # 日志文件路径，为空则不写入文件

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
