"""
后端认证接口测试。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.app import create_app


def test_login_and_me_round_trip(monkeypatch):
    """配置 bootstrap admin 后，应可登录并读取当前用户信息。"""
    monkeypatch.setenv('AMZ_BACKEND_JWT_SECRET', 'test-secret-with-at-least-32-bytes')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_EMAIL', 'owner@example.com')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_PASSWORD', 'owner-password')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_NAME', 'Workspace Owner')
    client = TestClient(create_app())

    login_response = client.post('/auth/login', json={'email': 'owner@example.com', 'password': 'owner-password'})

    assert login_response.status_code == 200
    body = login_response.json()
    assert body['token_type'] == 'bearer'
    assert body['user']['email'] == 'owner@example.com'
    assert body['user']['role'] == 'admin'

    me_response = client.get('/auth/me', headers={'Authorization': f"Bearer {body['access_token']}"})

    assert me_response.status_code == 200
    assert me_response.json() == body['user']


def test_login_rejects_wrong_password(monkeypatch):
    """错误密码必须被拒绝。"""
    monkeypatch.setenv('AMZ_BACKEND_JWT_SECRET', 'test-secret-with-at-least-32-bytes')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_EMAIL', 'owner@example.com')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_PASSWORD', 'owner-password')
    client = TestClient(create_app())

    response = client.post('/auth/login', json={'email': 'owner@example.com', 'password': 'wrong-password'})

    assert response.status_code == 401


def test_login_requires_bootstrap_configuration(monkeypatch):
    """未配置 bootstrap admin 时，登录接口应明确报错。"""
    monkeypatch.setenv('AMZ_BACKEND_JWT_SECRET', 'test-secret-with-at-least-32-bytes')
    monkeypatch.delenv('AMZ_BOOTSTRAP_ADMIN_EMAIL', raising=False)
    monkeypatch.delenv('AMZ_BOOTSTRAP_ADMIN_PASSWORD', raising=False)
    monkeypatch.delenv('AMZ_BOOTSTRAP_ADMIN_PASSWORD_HASH', raising=False)
    client = TestClient(create_app())

    response = client.post('/auth/login', json={'email': 'owner@example.com', 'password': 'owner-password'})

    assert response.status_code == 503
