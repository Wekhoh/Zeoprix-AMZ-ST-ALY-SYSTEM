"""
后端认证基础工具。

V1 提供密码哈希、JWT access token，以及基于数据库用户的最小登录能力。
bootstrap admin 仍通过环境变量定义，但启动时会先落库，再由认证逻辑统一从数据库读取。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from typing import Any

import bcrypt
import jwt
from sqlalchemy import func, select

from src.backend.database import SessionFactory


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
    """兼容保留：直接认证环境变量中的 bootstrap admin。"""
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


def _build_user_payload(session_factory: SessionFactory, *, user_id: str | None = None, email: str | None = None) -> UserPayload | None:
    from src.backend.models import User, WorkspaceMembership

    with session_factory() as session:
        user = None
        if user_id:
            user = session.get(User, user_id)
        elif email:
            normalized_email = email.strip().lower()
            user = session.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            return None

        membership = session.scalar(
            select(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id).order_by(WorkspaceMembership.created_at.asc())
        )
        role = membership.role if membership is not None else 'viewer'
        return {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': role,
        }


def authenticate_user(session_factory: SessionFactory | None, email: str, password: str) -> UserPayload:
    """优先认证数据库中的用户；无用户时再返回明确配置错误。"""
    if session_factory is None:
        return authenticate_bootstrap_user(email, password)

    from src.backend.models import User

    normalized_email = email.strip().lower()
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == normalized_email))
        user_count = session.scalar(select(func.count()).select_from(User)) or 0
        if user is None:
            if user_count == 0:
                raise AuthConfigError('No backend users are configured yet.')
            raise AuthenticationError('Incorrect email or password.')
        if not verify_password(password, user.password_hash):
            raise AuthenticationError('Incorrect email or password.')

    payload = _build_user_payload(session_factory, user_id=user.id)
    if payload is None:
        raise AuthenticationError('unknown user in token')
    return payload


def get_current_user_from_token(token: str, session_factory: SessionFactory | None = None) -> UserPayload:
    """根据 token 返回当前用户。"""
    payload = decode_access_token(token)
    if session_factory is not None:
        user = _build_user_payload(session_factory, user_id=payload['sub'])
        if user is None:
            raise AuthenticationError('unknown user in token')
        return user

    user = _get_bootstrap_user()
    if user is None:
        raise AuthConfigError('Bootstrap admin is not configured.')
    if payload['sub'] != user['id']:
        raise AuthenticationError('unknown user in token')
    return {key: value for key, value in user.items() if key != 'password_hash'}
