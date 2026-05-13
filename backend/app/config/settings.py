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

    # 平台授权配置
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    TIKTOK_APP_ID: str = ""
    TIKTOK_APP_SECRET: str = ""
    OAUTH_REDIRECT_URI: str = "http://localhost:3010/auth-callback"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
