"""
日志配置模块
提供统一的日志记录功能
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config.settings import get_settings

# 日志文件配置
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_FILE = "amz_analysis.log"
MAX_BYTES = 10 * 1024 * 1024  # 10MB per file
BACKUP_COUNT = 5  # Keep 5 backup files


def setup_logging() -> None:
    """配置全局日志"""
    settings = get_settings()

    # 日志格式
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)

    # 根据配置设置日志级别
    level = getattr(logging, settings.log_level, logging.INFO)

    # 配置handlers
    handlers = [
        logging.StreamHandler(sys.stdout),
    ]

    # 添加文件日志（带轮转）
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=LOG_DIR / LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        handlers.append(file_handler)
    except (OSError, PermissionError) as e:
        # 如果无法创建日志文件，仅使用控制台输出
        print(f"Warning: Could not create log file: {e}", file=sys.stderr)

    # 配置根日志器
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
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
