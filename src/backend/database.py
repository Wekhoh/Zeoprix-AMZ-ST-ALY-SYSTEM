"""
后端数据库基础设施。

V1 先统一数据库 URL、Engine、SessionFactory 与 Declarative Base，
并提供最小 schema 初始化与 bootstrap admin 落库能力。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "data" / "db" / "backend_app.db"
DEFAULT_WORKSPACE_NAME = "Default Workspace"


class Base(DeclarativeBase):
    """后端 ORM 基类。"""


SessionFactory = sessionmaker[Session]


def get_backend_database_url() -> str:
    """返回后端数据库连接串。"""
    configured_url = os.getenv("AMZ_BACKEND_DATABASE_URL", "").strip()
    if configured_url:
        return configured_url

    sqlite_path = Path(
        os.getenv("AMZ_BACKEND_SQLITE_PATH", str(DEFAULT_SQLITE_PATH))
    ).expanduser()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{sqlite_path.as_posix()}"


def create_engine_for_url(database_url: str) -> Engine:
    """按 URL 创建 SQLAlchemy Engine。"""
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

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


def _get_default_workspace_name() -> str:
    return (
        os.getenv("AMZ_BACKEND_DEFAULT_WORKSPACE_NAME", DEFAULT_WORKSPACE_NAME).strip()
        or DEFAULT_WORKSPACE_NAME
    )


def init_backend_schema(engine: Engine, session_factory: SessionFactory) -> None:
    """初始化 schema，并按需落库 bootstrap admin 与默认工作区。"""
    from src.backend.auth import _get_bootstrap_user  # 本地导入避免循环依赖
    from src.backend.models import User, Workspace, WorkspaceMembership

    Base.metadata.create_all(bind=engine)

    bootstrap_user = _get_bootstrap_user()
    if bootstrap_user is None:
        return

    workspace_name = _get_default_workspace_name()
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == bootstrap_user["email"]))
        if user is None:
            user = User(
                email=bootstrap_user["email"],
                name=bootstrap_user["name"],
                password_hash=bootstrap_user["password_hash"],
            )
            session.add(user)
            session.flush()
        else:
            user.name = bootstrap_user["name"]
            user.password_hash = bootstrap_user["password_hash"]

        workspace = session.scalar(
            select(Workspace).where(Workspace.name == workspace_name)
        )
        if workspace is None:
            workspace = Workspace(name=workspace_name)
            session.add(workspace)
            session.flush()

        membership = session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.workspace_id == workspace.id,
            )
        )
        if membership is None:
            membership = WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user.id,
                role="admin",
            )
            session.add(membership)
        else:
            membership.role = "admin"

        session.commit()


engine = create_engine_for_url(get_backend_database_url())
SessionLocal = create_session_factory(engine)


def get_db():
    """FastAPI 依赖注入入口。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
