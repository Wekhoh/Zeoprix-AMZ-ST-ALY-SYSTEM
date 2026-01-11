"""
UI工具模块
提供安全的错误处理和通用UI辅助函数
"""

import streamlit as st

from src.config.logger import get_logger

logger = get_logger(__name__)


# 错误类型到用户友好消息的映射
ERROR_MESSAGES = {
    "FileNotFoundError": "找不到指定的文件",
    "PermissionError": "没有权限执行此操作",
    "ValueError": "输入数据格式不正确",
    "KeyError": "缺少必要的数据字段",
    "sqlite3.Error": "数据库操作失败",
    "sqlite3.IntegrityError": "数据完整性错误",
    "ConnectionError": "网络连接失败",
    "TimeoutError": "操作超时",
    "json.JSONDecodeError": "数据格式解析失败",
    "pd.errors.EmptyDataError": "文件为空或格式不正确",
}


def safe_error(
    operation: str,
    exception: Exception,
    show_toast: bool = False,
) -> None:
    """
    安全地显示错误信息给用户

    - 记录详细错误到日志（供开发者调试）
    - 向用户显示通用友好消息（不暴露敏感信息）

    Args:
        operation: 操作描述（如"导出", "保存", "分析"）
        exception: 捕获的异常
        show_toast: 是否使用toast显示（默认使用st.error）
    """
    # 记录详细错误到日志
    logger.error(f"{operation}失败: {type(exception).__name__}: {exception}")

    # 获取用户友好的错误消息
    error_type = type(exception).__name__
    user_message = ERROR_MESSAGES.get(error_type, "操作失败")

    # 构建显示给用户的消息
    display_message = f"{operation}失败: {user_message}"

    # 显示错误
    if show_toast:
        st.toast(display_message, icon="❌")
    else:
        st.error(display_message)


def safe_warning(
    message: str,
    exception: Exception = None,
) -> None:
    """
    安全地显示警告信息

    Args:
        message: 显示给用户的警告消息
        exception: 可选的异常（会记录到日志）
    """
    if exception:
        logger.warning(f"{message}: {type(exception).__name__}: {exception}")
    st.warning(message)
