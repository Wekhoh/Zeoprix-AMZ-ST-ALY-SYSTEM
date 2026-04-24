"""Settings + backup service — Sprint 5 · B.2 (shim phase).

本模块是 backend 访问"设置 / 备份 / 清空 / 配置版本"业务逻辑的**唯一官方入口**。

当前（2026-04-24）：这四个函数的真实实现还留在 `src/ui/pages/settings_data.py`，
本文件只做 re-export。这样做的好处：

1. Backend 端（`src/backend/workbench_payload.py`）不再直接 import `src.ui.*`；
   从架构图看后端已完全与 Streamlit legacy 解耦。
2. Streamlit UI 仍可临时继续使用 `src/ui/pages/settings_data.py` 内 4 个函数。
3. 未来 `B.5` 把 Streamlit entry (src/app.py + src/ui/pages/) 整包删除时，
   只需把 4 个函数 body 搬进本文件、删除原文件，backend 端 import 不变。

依赖：
- `src.data.db.Database` 作为 db 参数类型（由调用方传入，未在签名强类型化）
"""

from __future__ import annotations

from src.ui.pages.settings_data import (
    build_full_backup_export_payload,
    clear_product_runtime_data,
    restore_full_backup,
    save_config_version,
)

__all__ = [
    "build_full_backup_export_payload",
    "clear_product_runtime_data",
    "restore_full_backup",
    "save_config_version",
]
