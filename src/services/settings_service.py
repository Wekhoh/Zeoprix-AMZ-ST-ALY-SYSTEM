"""Settings + backup service — Sprint 5 · B.2 (lazy-shim phase).

本模块是 backend 访问"设置 / 备份 / 清空 / 配置版本"业务逻辑的**唯一官方入口**。

## 现状（2026-04-24 · C.7 续）

这 4 个函数的真实实现仍在 `src/ui/pages/settings_data.py`，该文件顶层
`import streamlit as st`——所以在过去 B.2 的**静态 re-export** 阶段，任何
backend 路径（FastAPI 启动 / copilot_chat 导入链）都会把 streamlit 拖进
冷启动，实测多花 ~1.1s。

本阶段把 re-export 改成**惰性包装函数**：backend 冷启动不再 import
streamlit；只有真正调用（比如用户点"导出备份"时）才按需 load。函数签名、
返回形状与过去完全一致。

## 未来（B.5）

把 `src/ui/pages/settings_data.py` 中这 4 个纯数据函数的 body 搬进本文件，
删除 `src/ui/pages/*` 时调用方零修改。

## 依赖

- `src.data.db.Database` 作为 db 参数类型（由调用方传入，未在签名强类型化）
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "build_full_backup_export_payload",
    "clear_product_runtime_data",
    "restore_full_backup",
    "save_config_version",
]


def build_full_backup_export_payload(*args: Any, **kwargs: Any):
    """Lazy wrapper — 延迟 import `src.ui.pages.settings_data` 到首次调用。"""
    from src.ui.pages.settings_data import (
        build_full_backup_export_payload as _impl,
    )

    return _impl(*args, **kwargs)


def clear_product_runtime_data(*args: Any, **kwargs: Any):
    """Lazy wrapper — 延迟 import `src.ui.pages.settings_data` 到首次调用。"""
    from src.ui.pages.settings_data import clear_product_runtime_data as _impl

    return _impl(*args, **kwargs)


def restore_full_backup(*args: Any, **kwargs: Any):
    """Lazy wrapper — 延迟 import `src.ui.pages.settings_data` 到首次调用。"""
    from src.ui.pages.settings_data import restore_full_backup as _impl

    return _impl(*args, **kwargs)


def save_config_version(*args: Any, **kwargs: Any):
    """Lazy wrapper — 延迟 import `src.ui.pages.settings_data` 到首次调用。"""
    from src.ui.pages.settings_data import save_config_version as _impl

    return _impl(*args, **kwargs)
