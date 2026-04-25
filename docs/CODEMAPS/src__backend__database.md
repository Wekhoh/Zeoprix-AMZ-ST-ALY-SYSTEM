# src/backend/database.md

**Purpose:** 后端数据库基础设施（SQLAlchemy 配置、Engine、SessionFactory、schema 初始化）。

**Last Updated:** 2026-04-25

## Public Surface

- `Base` — SQLAlchemy DeclarativeBase，所有后端 ORM 模型的基类
- `SessionFactory` — sessionmaker[Session] 类型别名
- `get_backend_database_url()` — 从环境变量或默认路径返回数据库连接串
- `create_engine_for_url()` — 按 URL 创建 SQLAlchemy Engine（含 SQLite 适配）
- `create_session_factory()` — 创建 sessionmaker（autoflush=False、expire_on_commit=False）
- `init_backend_schema()` — 初始化 schema，落库 bootstrap admin 与默认工作区
- `get_db()` — FastAPI 依赖注入入口（SessionLocal）
- `engine` — 全局 Engine 实例（模块级）
- `SessionLocal` — 全局 SessionFactory 实例（模块级）

## Key Dependencies

1. **src.backend.auth** — `_get_bootstrap_user()` 获取环境变量配置的初始管理员
2. **src.backend.models** — User、Workspace、WorkspaceMembership ORM 模型
3. **sqlalchemy** — SQLAlchemy ORM 库

## Data Touched

**Backend Schema:**
- `users` — 创建表，插入 bootstrap admin（如已配置）
- `workspaces` — 创建表，插入默认工作区
- `workspace_memberships` — 创建表，建立 bootstrap admin 与默认工作区的关系

## Used By

- **src.backend.app** — 依赖 get_backend_database_url、create_engine_for_url、init_backend_schema
- **src.backend.models** — 继承 Base 类
- **任何需要数据库会话的模块** — 通过 `get_db()` 依赖注入

## Architecture Notes

- **Database URL Resolution:** 优先读 `AMZ_BACKEND_DATABASE_URL`，否则用 SQLite（`AMZ_BACKEND_SQLITE_PATH` 或默认 `data/db/backend_app.db`）
- **SQLite 适配:** 禁用 `check_same_thread` 以支持多线程
- **Schema Initialization:** 启动时一次性创建所有表，并落库 bootstrap 数据
- **Session 配置:** autoflush=False 确保显式 commit，expire_on_commit=False 避免 detached instances

## External Dependencies

- **sqlalchemy** (~2.0) — ORM 框架
