"""
后端数据库基础设施。

V1 先统一数据库 URL、Engine、SessionFactory 与 Declarative Base，
为后续 PostgreSQL、Alembic 迁移与 FastAPI 依赖注入打地基。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / 'data' / 'db' / 'backend_app.db'


class Base(DeclarativeBase):
    """后端 ORM 基类。"""


SessionFactory = sessionmaker[Session]


def get_backend_database_url() -> str:
    """返回后端数据库连接串。

    优先使用 PostgreSQL 等外部连接串；若未配置，则回退到本地 sqlite，
    方便本地开发与单元测试。
    """
    configured_url = os.getenv('AMZ_BACKEND_DATABASE_URL', '').strip()
    if configured_url:
        return configured_url

    sqlite_path = Path(os.getenv('AMZ_BACKEND_SQLITE_PATH', str(DEFAULT_SQLITE_PATH))).expanduser()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{sqlite_path.as_posix()}"


def create_engine_for_url(database_url: str) -> Engine:
    """按 URL 创建 SQLAlchemy Engine。"""
    connect_args: dict[str, Any] = {}
    if database_url.startswith('sqlite'):
        connect_args['check_same_thread'] = False

    return create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
        connect_args=connect_args,
    )


def create_session_factory(engine: Engine) -> SessionFactory:
    """创建 sessionmaker，供 FastAPI 依赖与后台任务复用。"""
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
        class_=Session,
    )


engine = create_engine_for_url(get_backend_database_url())
SessionLocal = create_session_factory(engine)


def get_db():
    """FastAPI 依赖注入入口。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
