"""
后端应用基础骨架测试。
"""

from fastapi.testclient import TestClient

from src.backend.app import APP_TITLE, APP_VERSION, create_app


def _app_with_error_routes():
    """Helper · Sprint 5 B.6 异常处理器测试。

    为了测试 app 级 exception_handler 是否生效，必须让异常穿过路由
    到达 FastAPI 的全局错误处理链。本 helper 在真实 create_app()
    产出的实例上临时注册 2 个 always-raise 路由。
    """
    app = create_app()

    @app.get("/_test/raise-value-error")
    async def _raise_value_error() -> dict:
        raise ValueError("产品不存在")

    @app.get("/_test/raise-runtime-error")
    async def _raise_runtime_error() -> dict:
        raise RuntimeError("database connection broken at 10.0.0.1:5432")

    return app


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
    monkeypatch.setenv(
        "AMZ_BACKEND_DATABASE_URL",
        f"sqlite:///{(tmp_path / 'backend-app.db').as_posix()}",
    )
    monkeypatch.setenv("AMZ_BACKEND_JWT_SECRET", "test-secret-with-at-least-32-bytes")
    monkeypatch.setenv("AMZ_BOOTSTRAP_ADMIN_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMZ_BOOTSTRAP_ADMIN_PASSWORD", "owner-password")
    monkeypatch.setenv("AMZ_BACKEND_DEFAULT_WORKSPACE_NAME", "Shared Workspace")

    from sqlalchemy import select

    from src.backend.database import create_engine_for_url, create_session_factory
    from src.backend.models import User, Workspace, WorkspaceMembership

    with TestClient(create_app()):
        pass

    engine = create_engine_for_url(
        f"sqlite:///{(tmp_path / 'backend-app.db').as_posix()}"
    )
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == "owner@example.com"))
        workspace = session.scalar(
            select(Workspace).where(Workspace.name == "Shared Workspace")
        )
        membership = session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.workspace_id == workspace.id,
            )
        )

    assert user is not None
    assert workspace is not None
    assert membership is not None
    assert membership.role == "admin"


# ── Sprint 5 B.6 · 全局异常处理器 ────────────────────────────────────────


def test_value_error_becomes_400_with_structured_error_json():
    """Service 层 `raise ValueError(...)` 应被映射为 400 + 统一 JSON 形状。"""
    client = TestClient(_app_with_error_routes())

    response = client.get("/_test/raise-value-error")

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "bad_request"
    assert body["error"]["message"] == "产品不存在"
    assert body["error"]["path"] == "/_test/raise-value-error"


def test_unhandled_exception_becomes_500_without_leaking_internals():
    """非预期异常不应把 '10.0.0.1:5432' 这种内部细节回传给前端。"""
    client = TestClient(_app_with_error_routes(), raise_server_exceptions=False)

    response = client.get("/_test/raise-runtime-error")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    # 清理后的 message 不含内部 IP / 端口 / 栈信息
    assert "10.0.0.1" not in body["error"]["message"]
    assert "5432" not in body["error"]["message"]
    # 仍暴露异常类型以便前端分类重试，但不含内部字符串
    assert body["error"]["type"] == "RuntimeError"
    assert body["error"]["path"] == "/_test/raise-runtime-error"


# ── Sprint 5 B.7 · Request-ID middleware ─────────────────────────────


def test_request_id_middleware_auto_generates_hex_id():
    """无 X-Request-Id 入参时，后端应生成 UUID4 hex 并回传。"""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    rid = response.headers.get("x-request-id")
    assert rid is not None and len(rid) == 32  # uuid4().hex 定长 32


def test_request_id_middleware_preserves_incoming_header():
    """客户端/代理已带 X-Request-Id 时应沿用，便于跨服务关联日志。"""
    client = TestClient(create_app())

    response = client.get("/health", headers={"X-Request-Id": "trace-abc-123"})

    assert response.status_code == 200
    assert response.headers.get("x-request-id") == "trace-abc-123"


def test_request_id_surfaces_in_unhandled_error_payload():
    """500 响应体应包含 request_id，方便前端 toast 上屏给用户排查用。"""
    client = TestClient(_app_with_error_routes(), raise_server_exceptions=False)

    response = client.get(
        "/_test/raise-runtime-error",
        headers={"X-Request-Id": "test-rid-42"},
    )

    assert response.status_code == 500
    assert response.headers.get("x-request-id") == "test-rid-42"
    body = response.json()
    assert body["error"]["request_id"] == "test-rid-42"
