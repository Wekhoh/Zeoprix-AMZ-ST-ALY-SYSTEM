"""
后端用户/工作区模型测试。
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from src.backend.database import create_engine_for_url, create_session_factory, init_backend_schema
from src.backend.models import User, Workspace, WorkspaceMembership


def test_init_backend_schema_bootstraps_admin_and_workspace(monkeypatch, tmp_path: Path):
    """初始化 schema 后，应自动建立 bootstrap admin、默认工作区与 admin membership。"""
    database_url = f"sqlite:///{tmp_path / 'backend-models.db'}"
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_EMAIL', 'owner@example.com')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_PASSWORD', 'owner-password')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_NAME', 'Workspace Owner')
    monkeypatch.setenv('AMZ_BACKEND_DEFAULT_WORKSPACE_NAME', 'Team Workspace')

    engine = create_engine_for_url(database_url)
    session_factory = create_session_factory(engine)

    init_backend_schema(engine, session_factory)

    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == 'owner@example.com'))
        workspace = session.scalar(select(Workspace).where(Workspace.name == 'Team Workspace'))
        membership = session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.workspace_id == workspace.id,
            )
        )

    assert user is not None
    assert workspace is not None
    assert membership is not None
    assert membership.role == 'admin'


def test_init_backend_schema_is_idempotent(monkeypatch, tmp_path: Path):
    """重复初始化不应重复创建 bootstrap admin 或 membership。"""
    database_url = f"sqlite:///{tmp_path / 'backend-models-idempotent.db'}"
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_EMAIL', 'owner@example.com')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_PASSWORD', 'owner-password')

    engine = create_engine_for_url(database_url)
    session_factory = create_session_factory(engine)

    init_backend_schema(engine, session_factory)
    init_backend_schema(engine, session_factory)

    with session_factory() as session:
        users = session.scalars(select(User)).all()
        workspaces = session.scalars(select(Workspace)).all()
        memberships = session.scalars(select(WorkspaceMembership)).all()

    assert len(users) == 1
    assert len(workspaces) == 1
    assert len(memberships) == 1
