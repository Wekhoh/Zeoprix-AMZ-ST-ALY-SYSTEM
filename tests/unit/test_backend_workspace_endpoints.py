"""
后端工作区成员接口测试。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.app import create_app


def _bootstrap_backend(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv('AMZ_BACKEND_DATABASE_URL', f"sqlite:///{(tmp_path / 'backend-workspace.db').as_posix()}")
    monkeypatch.setenv('AMZ_BACKEND_JWT_SECRET', 'test-secret-with-at-least-32-bytes')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_EMAIL', 'owner@example.com')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_PASSWORD', 'owner-password')
    monkeypatch.setenv('AMZ_BOOTSTRAP_ADMIN_NAME', 'Workspace Owner')


def _login(client: TestClient, email: str, password: str) -> tuple[str, dict]:
    response = client.post('/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    body = response.json()
    return body['access_token'], body['user']


def test_admin_can_create_member_and_new_member_can_log_in(monkeypatch, tmp_path):
    """管理员应能创建成员，且新成员应能直接使用新密码登录。"""
    _bootstrap_backend(monkeypatch, tmp_path)

    with TestClient(create_app()) as client:
        owner_token, owner = _login(client, 'owner@example.com', 'owner-password')
        workspace_response = client.get('/workspaces/default', headers={'Authorization': f'Bearer {owner_token}'})
        assert workspace_response.status_code == 200
        assert workspace_response.json()['member_count'] == 1
        assert workspace_response.json()['role'] == 'admin'

        create_member_response = client.post(
            '/workspaces/default/members',
            json={
                'email': 'teammate@example.com',
                'name': 'Teammate',
                'password': 'teammate-password',
                'role': 'editor',
            },
            headers={'Authorization': f'Bearer {owner_token}'},
        )
        assert create_member_response.status_code == 200
        assert create_member_response.json()['email'] == 'teammate@example.com'
        assert create_member_response.json()['role'] == 'editor'

        members_response = client.get('/workspaces/default/members', headers={'Authorization': f'Bearer {owner_token}'})
        assert members_response.status_code == 200
        members = members_response.json()
        assert [member['email'] for member in members] == ['owner@example.com', 'teammate@example.com']

        teammate_token, teammate = _login(client, 'teammate@example.com', 'teammate-password')
        assert teammate['role'] == 'editor'

        teammate_workspace = client.get('/workspaces/default', headers={'Authorization': f'Bearer {teammate_token}'})
        assert teammate_workspace.status_code == 200
        assert teammate_workspace.json()['member_count'] == 2
        assert teammate_workspace.json()['role'] == 'editor'
        assert owner['role'] == 'admin'


def test_non_admin_cannot_create_members(monkeypatch, tmp_path):
    """非管理员不可通过 API 添加工作区成员。"""
    _bootstrap_backend(monkeypatch, tmp_path)

    with TestClient(create_app()) as client:
        owner_token, _ = _login(client, 'owner@example.com', 'owner-password')
        client.post(
            '/workspaces/default/members',
            json={
                'email': 'viewer@example.com',
                'name': 'Viewer',
                'password': 'viewer-password',
                'role': 'viewer',
            },
            headers={'Authorization': f'Bearer {owner_token}'},
        )

        viewer_token, viewer = _login(client, 'viewer@example.com', 'viewer-password')
        assert viewer['role'] == 'viewer'

        forbidden_response = client.post(
            '/workspaces/default/members',
            json={
                'email': 'blocked@example.com',
                'name': 'Blocked',
                'password': 'blocked-password',
                'role': 'viewer',
            },
            headers={'Authorization': f'Bearer {viewer_token}'},
        )

    assert forbidden_response.status_code == 403


def test_member_endpoint_protects_last_admin_role(monkeypatch, tmp_path):
    """成员 API 不应允许把当前工作区最后一个管理员降级。"""
    _bootstrap_backend(monkeypatch, tmp_path)

    with TestClient(create_app()) as client:
        owner_token, _ = _login(client, 'owner@example.com', 'owner-password')
        demote_response = client.post(
            '/workspaces/default/members',
            json={
                'email': 'owner@example.com',
                'name': 'Workspace Owner',
                'password': 'owner-password',
                'role': 'viewer',
            },
            headers={'Authorization': f'Bearer {owner_token}'},
        )

    assert demote_response.status_code == 400
    assert 'At least one workspace admin must remain assigned.' in demote_response.json()['detail']
