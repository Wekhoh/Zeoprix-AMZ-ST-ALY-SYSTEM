"""
FastAPI 后端应用入口。

V1 先提供可部署、可探活的后端骨架，并补最小登录能力。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import func, select

from src.backend.auth import (
    AuthConfigError,
    AuthenticationError,
    authenticate_user,
    get_current_user_from_token,
    hash_password,
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
VALID_WORKSPACE_ROLES = {'admin', 'editor', 'viewer'}

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


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    role: str
    member_count: int


class WorkspaceMemberResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str


class WorkspaceMemberUpsertRequest(BaseModel):
    email: str
    password: str
    role: str
    name: str | None = None


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


def _get_runtime_session_factory(request: Request):
    session_factory = getattr(request.app.state, 'session_factory', None)
    if session_factory is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Backend database is not initialized.')
    return session_factory


def _require_admin(current_user: UserResponse) -> None:
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin role is required for this action.')


def _get_current_workspace_context(session_factory, user_id: str) -> tuple[str, str, str]:
    from src.backend.models import Workspace, WorkspaceMembership

    with session_factory() as session:
        membership = session.scalar(
            select(WorkspaceMembership)
            .where(WorkspaceMembership.user_id == user_id)
            .order_by(WorkspaceMembership.created_at.asc())
        )
        if membership is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Current user does not belong to a workspace.')

        workspace = session.get(Workspace, membership.workspace_id)
        if workspace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Current workspace was not found.')
        return workspace.id, workspace.name, membership.role


def _serialize_workspace_members(session_factory, workspace_id: str) -> list[WorkspaceMemberResponse]:
    from src.backend.models import User, WorkspaceMembership

    with session_factory() as session:
        rows = session.execute(
            select(User.id, User.email, User.name, WorkspaceMembership.role)
            .join(WorkspaceMembership, WorkspaceMembership.user_id == User.id)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .order_by(WorkspaceMembership.role.asc(), User.email.asc())
        ).all()
    return [WorkspaceMemberResponse(id=row.id, email=row.email, name=row.name, role=row.role) for row in rows]


def _upsert_workspace_member(session_factory, workspace_id: str, payload: WorkspaceMemberUpsertRequest) -> WorkspaceMemberResponse:
    from src.backend.models import User, WorkspaceMembership

    normalized_email = payload.email.strip().lower()
    normalized_name = (payload.name or normalized_email.split('@', 1)[0]).strip()
    normalized_role = payload.role.strip().lower()
    normalized_password = payload.password.strip()
    if not normalized_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Member email is required.')
    if not normalized_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Member password is required.')
    if normalized_role not in VALID_WORKSPACE_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported workspace role.')

    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            user = User(
                email=normalized_email,
                name=normalized_name,
                password_hash=hash_password(normalized_password),
            )
            session.add(user)
            session.flush()
        else:
            user.name = normalized_name
            user.password_hash = hash_password(normalized_password)

        membership = session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user.id,
            )
        )
        if membership is None:
            membership = WorkspaceMembership(workspace_id=workspace_id, user_id=user.id, role=normalized_role)
            session.add(membership)
        else:
            if membership.role == 'admin' and normalized_role != 'admin':
                admin_count = session.scalar(
                    select(func.count()).select_from(WorkspaceMembership).where(
                        WorkspaceMembership.workspace_id == workspace_id,
                        WorkspaceMembership.role == 'admin',
                    )
                ) or 0
                if admin_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='At least one workspace admin must remain assigned.',
                    )
            membership.role = normalized_role

        session.commit()
        session.refresh(user)
        session.refresh(membership)
        return WorkspaceMemberResponse(id=user.id, email=user.email, name=user.name, role=membership.role)


async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> UserResponse:
    try:
        user = get_current_user_from_token(token, _get_runtime_session_factory(request))
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
    async def login(payload: LoginRequest, request: Request) -> LoginResponse:
        try:
            user = authenticate_user(_get_runtime_session_factory(request), payload.email, payload.password)
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

    @app.get('/workspaces/default', response_model=WorkspaceResponse, tags=['workspaces'])
    async def read_default_workspace(request: Request, current_user: UserResponse = Depends(get_current_user)) -> WorkspaceResponse:
        session_factory = _get_runtime_session_factory(request)
        workspace_id, workspace_name, membership_role = _get_current_workspace_context(session_factory, current_user.id)
        member_count = len(_serialize_workspace_members(session_factory, workspace_id))
        return WorkspaceResponse(id=workspace_id, name=workspace_name, role=membership_role, member_count=member_count)

    @app.get('/workspaces/default/members', response_model=list[WorkspaceMemberResponse], tags=['workspaces'])
    async def list_default_workspace_members(
        request: Request,
        current_user: UserResponse = Depends(get_current_user),
    ) -> list[WorkspaceMemberResponse]:
        session_factory = _get_runtime_session_factory(request)
        workspace_id, _, _ = _get_current_workspace_context(session_factory, current_user.id)
        return _serialize_workspace_members(session_factory, workspace_id)

    @app.post('/workspaces/default/members', response_model=WorkspaceMemberResponse, tags=['workspaces'])
    async def upsert_default_workspace_member(
        payload: WorkspaceMemberUpsertRequest,
        request: Request,
        current_user: UserResponse = Depends(get_current_user),
    ) -> WorkspaceMemberResponse:
        _require_admin(current_user)
        session_factory = _get_runtime_session_factory(request)
        workspace_id, _, _ = _get_current_workspace_context(session_factory, current_user.id)
        return _upsert_workspace_member(session_factory, workspace_id, payload)

    return app


app = create_app()

