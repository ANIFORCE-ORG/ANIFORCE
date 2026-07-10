"""数据库配置和连接管理"""
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy ORM Base 类"""
    pass


# SQLite 引擎和会话
_engine = None
_async_session_maker = None


def get_engine():
    """获取 SQLite 异步引擎（单例）"""
    global _engine
    if _engine is None:
        settings = get_settings()
        # 默认使用 SQLite，如果配置了其他数据库则使用配置的
        if settings.DATABASE_URL:
            database_url = settings.DATABASE_URL
        else:
            database_url = "sqlite+aiosqlite:///./data/sqlite/animagus.db"
        
        # 根据数据库类型设置连接参数
        connect_args = {}
        if "sqlite" in database_url:
            connect_args = {"check_same_thread": False}
        
        _engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            connect_args=connect_args,
        )
        if "sqlite" in database_url:
            @event.listens_for(_engine.sync_engine, "connect")
            def configure_sqlite(dbapi_connection, _connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """获取 SQLite 会话工厂（单例）"""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_maker


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async_session = get_session_maker()
    async with async_session() as session:
        try:
            yield session
            await session.commit()  # 自动提交事务
        except Exception:
            await session.rollback()  # 发生错误时回滚
            raise


# MongoDB 客户端
_mongo_client = None
_mongo_db = None


def get_mongo_client():
    """获取 MongoDB 客户端（单例）"""
    global _mongo_client
    if _mongo_client is None:
        settings = get_settings()
        if settings.MONGODB_URL:
            _mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    return _mongo_client


def get_mongo_db():
    """获取 MongoDB 数据库（单例）"""
    global _mongo_db
    if _mongo_db is None:
        settings = get_settings()
        client = get_mongo_client()
        if client:
            _mongo_db = client[settings.MONGODB_DB_NAME]
    return _mongo_db


async def close_db_connections():
    """关闭所有数据库连接"""
    global _engine, _mongo_client
    
    # 关闭 SQLite
    if _engine:
        await _engine.dispose()
        _engine = None
    
    # 关闭 MongoDB
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
