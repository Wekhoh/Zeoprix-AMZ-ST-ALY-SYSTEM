"""
日志配置模块
提供统一的日志记录功能
"""

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config.settings import get_settings

# 日志文件配置
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_FILE = "amz_analysis.log"
MAX_BYTES = 10 * 1024 * 1024  # 10MB per file
BACKUP_COUNT = 5  # Keep 5 backup files


class JsonFormatter(logging.Formatter):
    """Sprint 5 B.7 续 · 结构化 JSON 日志。

    每行一个 JSON 对象，适配 Loki / ELK / CloudWatch Insights 等日志聚合。
    通过 env `AMZ_LOG_JSON=1` 启用；默认保留原人类可读格式。
    """

    _STANDARD_FIELDS = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "message",
        "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # 额外通过 logger.info("x", extra={"foo": 1}) 传入的字段也一并序列化
        for key, value in record.__dict__.items():
            if key in self._STANDARD_FIELDS or key.startswith("_"):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        return json.dumps(payload, ensure_ascii=False)


def _select_formatter() -> logging.Formatter:
    """按 env 选择 JSON 或人类可读 formatter。默认后者。"""
    if os.environ.get("AMZ_LOG_JSON", "").strip().lower() in ("1", "true", "yes"):
        return JsonFormatter()
    return logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )


def setup_logging() -> None:
    """配置全局日志"""
    settings = get_settings()

    # 日志格式：按 env 决定 JSON vs 文本
    formatter = _select_formatter()
    # 供 basicConfig 使用的回退 format（文本模式下才起作用）
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 根据配置设置日志级别
    level = getattr(logging, settings.log_level, logging.INFO)

    # 配置handlers — formatter 显式绑到每个 handler，确保 JSON 模式下
    # stdout 和文件都输出 JSON；basicConfig 的 format/datefmt 只作回退。
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    handlers: list[logging.Handler] = [stream_handler]

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
        force=True,
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
