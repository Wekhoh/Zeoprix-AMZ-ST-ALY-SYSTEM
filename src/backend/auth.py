"""
后端认证基础工具。

V1 先提供密码哈希、JWT access token，以及 bootstrap admin 认证逻辑，
后续再接数据库用户模型与 refresh token。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from typing import Any

import bcrypt
import jwt


JWT_ALGORITHM = 'HS256'
DEFAULT_ACCESS_TOKEN_MINUTES = 30


class AuthConfigError(RuntimeError):
    """认证配置缺失。"""


class AuthenticationError(ValueError):
    """认证失败。"""


UserPayload = dict[str, str]


def _get_jwt_secret() -> str:
    secret = os.getenv('AMZ_BACKEND_JWT_SECRET', '').strip()
    if not secret:
        raise AuthConfigError('AMZ_BACKEND_JWT_SECRET is required for token operations.')
    return secret


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码。"""
    encoded = password.encode('utf-8')
    hashed = bcrypt.hashpw(encoded, bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def _get_bootstrap_user() -> UserPayload | None:
    email = os.getenv('AMZ_BOOTSTRAP_ADMIN_EMAIL', '').strip().lower()
    name = os.getenv('AMZ_BOOTSTRAP_ADMIN_NAME', 'Workspace Admin').strip() or 'Workspace Admin'
    password_hash = os.getenv('AMZ_BOOTSTRAP_ADMIN_PASSWORD_HASH', '').strip()
    password_plain = os.getenv('AMZ_BOOTSTRAP_ADMIN_PASSWORD', '')
    if not email:
        return None
    if not password_hash and not password_plain:
        return None
    if not password_hash:
        password_hash = hash_password(password_plain)
    return {
        'id': 'bootstrap-admin',
        'email': email,
        'name': name,
        'role': 'admin',
        'password_hash': password_hash,
    }


def authenticate_bootstrap_user(email: str, password: str) -> UserPayload:
    """认证 bootstrap admin 用户。"""
    user = _get_bootstrap_user()
    if user is None:
        raise AuthConfigError('Bootstrap admin is not configured.')
    if user['email'] != email.strip().lower() or not verify_password(password, user['password_hash']):
        raise AuthenticationError('Incorrect email or password.')
    return {key: value for key, value in user.items() if key != 'password_hash'}


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """创建 access token。"""
    lifetime = expires_delta or timedelta(minutes=DEFAULT_ACCESS_TOKEN_MINUTES)
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        'sub': subject,
        'type': 'access',
        'iat': now,
        'exp': now + lifetime,
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def issue_access_token_for_user(user: UserPayload, expires_delta: timedelta | None = None) -> str:
    """为用户签发 access token。"""
    return create_access_token(user['id'], expires_delta=expires_delta)


def decode_access_token(token: str) -> dict[str, Any]:
    """解码并校验 access token。"""
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError('access token expired') from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError('invalid access token') from exc

    if payload.get('type') != 'access' or not payload.get('sub'):
        raise AuthenticationError('invalid access token payload')
    return payload


def get_current_user_from_token(token: str) -> UserPayload:
    """根据 token 返回当前用户。"""
    payload = decode_access_token(token)
    user = _get_bootstrap_user()
    if user is None:
        raise AuthConfigError('Bootstrap admin is not configured.')
    if payload['sub'] != user['id']:
        raise AuthenticationError('unknown user in token')
    return {key: value for key, value in user.items() if key != 'password_hash'}
