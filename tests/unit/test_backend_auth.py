"""
后端认证基础测试。
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from src.backend.auth import (
    decode_access_token,
    hash_password,
    verify_password,
    create_access_token,
)


def test_hash_password_and_verify_round_trip():
    """密码应被哈希存储，并可正确校验。"""
    password = "S3cure-P@ssword"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_access_token(monkeypatch):
    """JWT 应包含 subject，并可在有效期内正确解码。"""
    monkeypatch.setenv("AMZ_BACKEND_JWT_SECRET", "test-secret-with-at-least-32-bytes")

    token = create_access_token("user-123", expires_delta=timedelta(minutes=15))
    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_decode_access_token_rejects_expired_token(monkeypatch):
    """过期 token 必须被拒绝。"""
    monkeypatch.setenv("AMZ_BACKEND_JWT_SECRET", "test-secret-with-at-least-32-bytes")
    token = create_access_token("user-123", expires_delta=timedelta(seconds=-1))

    with pytest.raises(ValueError, match="expired"):
        decode_access_token(token)
