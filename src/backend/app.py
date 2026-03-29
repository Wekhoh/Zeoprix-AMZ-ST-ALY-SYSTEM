"""
FastAPI 后端应用入口。

V1 先提供可部署、可探活的后端骨架，并补最小登录能力。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from src.backend.auth import (
    AuthConfigError,
    AuthenticationError,
    authenticate_bootstrap_user,
    get_current_user_from_token,
    issue_access_token_for_user,
)
from src.backend.database import (
    create_engine_for_url,
    create_session_factory,
    get_backend_database_url,
    init_backend_schema,
)


APP_TITLE = 'AMZ 搜索词分析系统 Backend'
APP_VERSION = '0.1.0'

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化后端 schema 与 bootstrap 数据。"""
    runtime_engine = create_engine_for_url(get_backend_database_url())
    runtime_session_factory = create_session_factory(runtime_engine)
    init_backend_schema(runtime_engine, runtime_session_factory)
    app.state.engine = runtime_engine
    app.state.session_factory = runtime_session_factory
    yield
    runtime_engine.dispose()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    try:
        user = get_current_user_from_token(token)
    except AuthConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={'WWW-Authenticate': 'Bearer'},
        ) from exc
    return UserResponse(**user)


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        lifespan=lifespan,
    )

    @app.get('/', tags=['system'])
    async def read_root() -> dict[str, str]:
        return {
            'service': APP_TITLE,
            'status': 'ok',
            'version': APP_VERSION,
        }

    @app.get('/health', tags=['system'])
    async def healthcheck() -> dict[str, str]:
        return {
            'service': APP_TITLE,
            'status': 'ok',
            'version': APP_VERSION,
        }

    @app.post('/auth/login', response_model=LoginResponse, tags=['auth'])
    async def login(payload: LoginRequest) -> LoginResponse:
        try:
            user = authenticate_bootstrap_user(payload.email, payload.password)
            token = issue_access_token_for_user(user)
        except AuthConfigError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except AuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

        return LoginResponse(
            access_token=token,
            token_type='bearer',
            user=UserResponse(**user),
        )

    @app.get('/auth/me', response_model=UserResponse, tags=['auth'])
    async def read_auth_me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        return current_user

    return app


app = create_app()

