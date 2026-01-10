"""
日志配置模块
提供统一的日志记录功能
"""

import logging
import sys
from pathlib import Path

from src.config.settings import get_settings


def setup_logging() -> None:
    """配置全局日志"""
    settings = get_settings()

    # 日志格式
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 根据配置设置日志级别
    level = getattr(logging, settings.log_level, logging.INFO)

    # 配置根日志器
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # 降低第三方库的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 模块名称，通常使用 __name__

    Returns:
        配置好的Logger实例

    Usage:
        from src.config.logger import get_logger
        logger = get_logger(__name__)
        logger.info("这是一条日志")
    """
    return logging.getLogger(name)


# 首次导入时自动配置日志
# 使用标志位避免重复配置
_logging_configured = False


def ensure_logging_configured() -> None:
    """确保日志已配置"""
    global _logging_configured
    if not _logging_configured:
        setup_logging()
        _logging_configured = True


# 模块加载时自动配置
ensure_logging_configured()
