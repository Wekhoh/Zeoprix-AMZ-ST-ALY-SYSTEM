"""Service layer — Sprint 5 · B.2.

聚合后端 / 未来 CLI 工具可直接调用的业务逻辑服务。
本层**不依赖** Streamlit / FastAPI，纯 Python + DB。

当前进度：
- settings_service：设置页 legacy 业务逻辑（shim 阶段，body 待 B.5 搬家）

未来 legacy 清理（B.5）完成后，`src.services` 成为 backend 和任何外部
entrypoint（CLI / cron / unit test）访问核心业务逻辑的唯一官方入口。
"""
