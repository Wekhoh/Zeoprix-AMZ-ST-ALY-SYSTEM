"""
FastAPI 后端应用入口。

V1 先提供可部署、可探活的后端骨架，并补最小登录能力。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
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
from src.backend.copilot_chat import process_frontend_copilot_turn
from src.backend.workbench_payload import (
    build_actions_page_payload,
    build_analysis_page_payload,
    build_review_page_payload,
    build_settings_page_payload,
    build_upload_page_payload,
    build_workbench_payload,
    clear_runtime_for_frontend,
    create_execution_batch_for_frontend,
    export_full_backup_for_frontend,
    restore_full_backup_for_frontend,
    run_analysis_for_frontend,
    submit_review_decision_for_frontend,
    upload_files_for_frontend,
    update_execution_batch_for_frontend,
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


class FrontendExecutionBatchCreateRequest(BaseModel):
    product_id: int
    batch_type: str
    draft_note: str | None = None


class FrontendExecutionBatchUpdateRequest(BaseModel):
    status: str
    execution_note: str | None = None
    review_note: str | None = None


class FrontendReviewDecisionRequest(BaseModel):
    product_id: int
    term: str
    term_type: str
    campaign_id: int | None = None
    relevance: str
    notes: str | None = None


class FrontendProductRequest(BaseModel):
    product_id: int


class FrontendCopilotMessage(BaseModel):
    role: str
    content: str


class FrontendCopilotChatRequest(BaseModel):
    product_id: int | None = None
    page_key: str
    page_title: str
    user_message: str
    history: list[FrontendCopilotMessage] = []


class FrontendRestoreBackupRequest(BaseModel):
    product_id: int | None = None
    restore_as_new_product: bool = False
    backup_data: dict


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


def _remove_workspace_member(session_factory, workspace_id: str, user_id: str) -> WorkspaceMemberResponse:
    from src.backend.models import User, WorkspaceMembership

    with session_factory() as session:
        membership = session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user_id,
            )
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Workspace member was not found.',
            )

        if membership.role == 'admin':
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

        user = session.get(User, membership.user_id)
        removed_role = membership.role
        session.delete(membership)
        session.commit()

        member_email = user.email if user is not None else user_id
        member_name = user.name if user is not None else member_email
        return WorkspaceMemberResponse(
            id=user_id,
            email=member_email,
            name=member_name,
            role=removed_role,
        )


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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:3003",
            "http://127.0.0.1:3004",
            "http://127.0.0.1:3005",
            "http://127.0.0.1:3006",
            "http://127.0.0.1:3007",
            "http://127.0.0.1:3008",
            "http://127.0.0.1:3009",
            "http://127.0.0.1:3010",
            "http://127.0.0.1:3011",
            "http://127.0.0.1:3012",
            "http://127.0.0.1:3013",
            "http://127.0.0.1:3014",
            "http://127.0.0.1:3015",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://localhost:3004",
            "http://localhost:3005",
            "http://localhost:3006",
            "http://localhost:3007",
            "http://localhost:3008",
            "http://localhost:3009",
            "http://localhost:3010",
            "http://localhost:3011",
            "http://localhost:3012",
            "http://localhost:3013",
            "http://localhost:3014",
            "http://localhost:3015",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

    @app.get('/frontend/workbench', tags=['frontend'])
    async def read_frontend_workbench(product_id: int | None = None) -> dict:
        """为独立前端壳返回首页/共享壳聚合数据。"""
        return build_workbench_payload(product_id=product_id)

    @app.get('/frontend/upload', tags=['frontend'])
    async def read_frontend_upload(product_id: int | None = None) -> dict:
        return build_upload_page_payload(product_id=product_id)

    @app.get('/frontend/analysis', tags=['frontend'])
    async def read_frontend_analysis(product_id: int | None = None) -> dict:
        return build_analysis_page_payload(product_id=product_id)

    @app.get('/frontend/actions', tags=['frontend'])
    async def read_frontend_actions(product_id: int | None = None) -> dict:
        return build_actions_page_payload(product_id=product_id)

    @app.get('/frontend/review', tags=['frontend'])
    async def read_frontend_review(product_id: int | None = None) -> dict:
        return build_review_page_payload(product_id=product_id)

    @app.get('/frontend/settings', tags=['frontend'])
    async def read_frontend_settings(product_id: int | None = None) -> dict:
        return build_settings_page_payload(product_id=product_id)

    @app.post('/frontend/upload/run-analysis', tags=['frontend'])
    async def run_frontend_analysis(payload: FrontendProductRequest) -> dict:
        return run_analysis_for_frontend(product_id=payload.product_id)

    @app.post('/frontend/upload/files', tags=['frontend'])
    async def upload_frontend_files(
        product_id: int = Form(...),
        auto_analyze: bool = Form(True),
        files: list[UploadFile] = File(...),
    ) -> dict:
        return upload_files_for_frontend(
            product_id=product_id,
            files=files,
            auto_analyze=auto_analyze,
        )

    @app.post('/frontend/settings/clear-runtime', tags=['frontend'])
    async def clear_frontend_runtime(payload: FrontendProductRequest) -> dict:
        return clear_runtime_for_frontend(product_id=payload.product_id)

    @app.get('/frontend/settings/full-backup', tags=['frontend'])
    async def export_frontend_full_backup(product_id: int) -> dict:
        return export_full_backup_for_frontend(product_id=product_id)

    @app.post('/frontend/settings/restore-backup', tags=['frontend'])
    async def restore_frontend_full_backup(payload: FrontendRestoreBackupRequest) -> dict:
        return restore_full_backup_for_frontend(
            product_id=payload.product_id,
            restore_as_new_product=payload.restore_as_new_product,
            backup_data=payload.backup_data,
        )

    @app.post('/frontend/actions/execution-batches', tags=['frontend'])
    async def create_frontend_execution_batch(payload: FrontendExecutionBatchCreateRequest) -> dict:
        return create_execution_batch_for_frontend(
            product_id=payload.product_id,
            batch_type=payload.batch_type,
            draft_note=payload.draft_note,
        )

    @app.patch('/frontend/actions/execution-batches/{batch_id}', tags=['frontend'])
    async def update_frontend_execution_batch(batch_id: int, payload: FrontendExecutionBatchUpdateRequest) -> dict:
        return update_execution_batch_for_frontend(
            batch_id=batch_id,
            status=payload.status,
            execution_note=payload.execution_note,
            review_note=payload.review_note,
        )

    @app.post('/frontend/review/manual-reviews', tags=['frontend'])
    async def create_frontend_review_decision(payload: FrontendReviewDecisionRequest) -> dict:
        return submit_review_decision_for_frontend(
            product_id=payload.product_id,
            term=payload.term,
            term_type=payload.term_type,
            campaign_id=payload.campaign_id,
            relevance=payload.relevance,
            notes=payload.notes,
        )

    @app.post('/frontend/copilot/chat', tags=['frontend'])
    async def chat_frontend_copilot(payload: FrontendCopilotChatRequest) -> dict:
        return process_frontend_copilot_turn(
            product_id=payload.product_id,
            page_key=payload.page_key,
            page_title=payload.page_title,
            user_message=payload.user_message,
            history=[msg.model_dump() for msg in payload.history],
        )

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

    @app.delete('/workspaces/default/members/{member_user_id}', response_model=WorkspaceMemberResponse, tags=['workspaces'])
    async def delete_default_workspace_member(
        member_user_id: str,
        request: Request,
        current_user: UserResponse = Depends(get_current_user),
    ) -> WorkspaceMemberResponse:
        _require_admin(current_user)
        session_factory = _get_runtime_session_factory(request)
        workspace_id, _, _ = _get_current_workspace_context(session_factory, current_user.id)
        return _remove_workspace_member(session_factory, workspace_id, member_user_id)

    return app


app = create_app()

