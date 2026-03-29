"""
后端应用基础骨架测试。
"""

from fastapi.testclient import TestClient

from src.backend.app import APP_TITLE, APP_VERSION, create_app


def test_backend_health_endpoint_exposes_service_metadata():
    """后端骨架应至少提供可探活的健康检查。"""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": APP_TITLE,
        "status": "ok",
        "version": APP_VERSION,
    }


def test_backend_root_endpoint_matches_health_contract():
    """根路径先保持与健康检查一致，方便反向代理与 smoke test。"""
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == APP_TITLE


def test_backend_lifespan_initializes_schema_and_bootstrap_admin(monkeypatch, tmp_path):
    """启动应用时，应自动初始化 schema 并落库 bootstrap admin。"""
    monkeypatch.setenv('AMZ_BACKEND_DATABASE_URL', f"sqlite:///{(tmp_path / 'backend-app.db').as_posix()}")
    monkeypatch.setenv('AMZ_BACKEND_JWT_SECRET', 'test-secret-with-at-least-32-bytes')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_EMAIL', 'owner@example.com')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_PASSWORD', 'owner-password')
    monkeypatch.setenv('AMZ_BACKEND_DEFAULT_WORKSPACE_NAME', 'Shared Workspace')

    from sqlalchemy import select

    from src.backend.database import create_engine_for_url, create_session_factory
    from src.backend.models import User, Workspace, WorkspaceMembership

    with TestClient(create_app()):
        pass

    engine = create_engine_for_url(f"sqlite:///{(tmp_path / 'backend-app.db').as_posix()}")
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == 'owner@example.com'))
        workspace = session.scalar(select(Workspace).where(Workspace.name == 'Shared Workspace'))
        membership = session.scalar(select(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id, WorkspaceMembership.workspace_id == workspace.id))

    assert user is not None
    assert workspace is not None
    assert membership is not None
    assert membership.role == 'admin'
