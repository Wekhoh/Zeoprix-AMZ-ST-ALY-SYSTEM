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
