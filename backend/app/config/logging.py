"""
日志配置模块
统一配置 loguru 和标准 logging 模块的日志格式
"""
import sys
import logging
from loguru import logger
from pathlib import Path


# 自定义日志格式
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 标准 logging 模块的格式
STANDARD_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
)

# 日期格式
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    配置日志系统
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，如果为 None 则只输出到控制台
    """
    # 移除默认的 loguru handler
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # 如果指定了日志文件，添加文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果日志文件名包含日期占位符，使用按日期轮转
        # 例如：backend_logs_{time:YYYYMMDD}.log
        if "{time" in log_file:
            # 使用 loguru 的时间占位符，自动按日期轮转
            logger.add(
                log_file,
                format=LOG_FORMAT,
                level=log_level,
                rotation="00:00",  # 每天午夜轮转
                retention="30 days",  # 保留 30 天的日志
                compression="zip",  # 压缩旧日志
                backtrace=True,
                diagnose=True,
            )
        else:
            # 传统方式：按文件大小轮转
            logger.add(
                log_file,
                format=LOG_FORMAT,
                level=log_level,
                rotation="100 MB",  # 日志文件达到 100MB 时轮转
                retention="30 days",  # 保留 30 天的日志
                compression="zip",  # 压缩旧日志
                backtrace=True,
                diagnose=True,
            )
    
    # 配置标准 logging 模块，将其输出重定向到 loguru
    class InterceptHandler(logging.Handler):
        """
        拦截标准 logging 模块的日志，重定向到 loguru
        """
        def emit(self, record):
            # 获取对应的 loguru 日志级别
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # 查找调用者的位置
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # 配置标准 logging 模块
    logging.basicConfig(
        handlers=[InterceptHandler()],
        level=log_level,
        format=STANDARD_FORMAT,
        datefmt=DATE_FORMAT,
    )
    
    # 设置所有已存在的 logger
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    
    # 配置 uvicorn 和 fastapi 的日志
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("fastapi").handlers = [InterceptHandler()]
    
    logger.info(f"Logging configured with level: {log_level}")


def get_logger(name: str = None):
    """
    获取 logger 实例
    
    Args:
        name: logger 名称，通常使用 __name__
        
    Returns:
        loguru logger 实例
    """
    if name:
        return logger.bind(name=name)
    return logger
