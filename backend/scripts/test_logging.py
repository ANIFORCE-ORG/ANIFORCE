"""
测试日志格式配置
"""
from app.config.logging import setup_logging
from loguru import logger
import logging

# 初始化日志系统
setup_logging(log_level="DEBUG", log_file="logs/test.log")

# 测试 loguru 日志
logger.debug("This is a DEBUG message from loguru")
logger.info("This is an INFO message from loguru")
logger.warning("This is a WARNING message from loguru")
logger.error("This is an ERROR message from loguru")

# 测试标准 logging 模块（会被重定向到 loguru）
std_logger = logging.getLogger("test_module")
std_logger.debug("This is a DEBUG message from standard logging")
std_logger.info("This is an INFO message from standard logging")
std_logger.warning("This is a WARNING message from standard logging")
std_logger.error("This is an ERROR message from standard logging")

# 测试异常日志
try:
    1 / 0
except Exception as e:
    logger.exception("Caught an exception")

print("\n✅ 日志测试完成，请查看控制台输出和 logs/test.log 文件")
