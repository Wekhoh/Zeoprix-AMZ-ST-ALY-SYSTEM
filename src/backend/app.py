"""
FastAPI 后端应用入口。

V1 先提供可部署、可探活的后端骨架，并补最小登录能力。
"""

from __future__ import annotations

import logging
import time as _time_module
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
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
from src.backend.copilot_chat import (
    process_frontend_copilot_turn,
    process_frontend_copilot_turn_stream,
)
from src.backend.insights import (
    generate_and_store_insight,
    get_today_insight,
)
from src.backend.schemas import (
    CopilotChatResponse,
    DailyInsightRow,
    ErrorResponse,
    HealthResponse,
    InsightTodayResponse,
    MetricsResponse,
)
from src.backend.workbench_payload import (
    build_actions_page_payload,
    build_amazon_bulk_csv_export,
    build_analysis_page_payload,
    build_competitors_payload,
    build_review_page_payload,
    build_settings_page_payload,
    build_term_detail_payload,
    build_upload_page_payload,
    build_workbench_payload,
    clear_runtime_for_frontend,
    preview_settings_rule_version_for_frontend,
    restore_settings_rule_version_for_frontend,
    update_settings_config_for_frontend,
    create_execution_batch_for_frontend,
    export_full_backup_for_frontend,
    restore_full_backup_for_frontend,
    run_analysis_for_frontend,
    submit_review_decision_for_frontend,
    upload_files_for_frontend,
    update_execution_batch_for_frontend,
)


APP_TITLE = "AMZ 搜索词分析系统 Backend"
APP_VERSION = "0.1.0"
VALID_WORKSPACE_ROLES = {"admin", "editor", "viewer"}

_LOGGER = logging.getLogger(__name__)


def _error_payload(
    code: str, message: str, path: str, *, extra: dict | None = None
) -> dict:
    """Sprint 5 B.6 · 统一错误响应 body 结构。

    所有未捕获异常都走该函数，保证前端能按同一 JSON 形状解析。
    """
    body: dict = {"error": {"code": code, "message": message, "path": path}}
    if extra:
        body["error"].update(extra)
    return body


# ── Sprint 5 C.1/C.2 · In-memory metrics store ──────────────────────────
# 简单聚合 per-path 请求统计：count / total_ms / max_ms / errors (5xx)。
# 无持久化，进程重启清零。升级 Prometheus 时替换此 dict。
# （import time as _time_module 已提至文件顶层，满足 ruff E402）
_STARTUP_TS = _time_module.time()
_METRICS_STORE: dict[str, dict[str, float]] = {}


def _record_metric(path: str, duration_ms: float, status: int) -> None:
    bucket = _METRICS_STORE.setdefault(
        path,
        {"count": 0.0, "total_ms": 0.0, "max_ms": 0.0, "errors": 0.0},
    )
    bucket["count"] += 1
    bucket["total_ms"] += duration_ms
    if duration_ms > bucket["max_ms"]:
        bucket["max_ms"] = duration_ms
    if status >= 500:
        bucket["errors"] += 1


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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
    # Sprint A.4: 主人在前端 inline-confirm 后传 force=True 跳过冲突检查
    force: bool = False


class FrontendProductRequest(BaseModel):
    product_id: int


class FrontendCopilotMessage(BaseModel):
    role: str
    content: str


class FrontendCopilotChatRequest(BaseModel):
    product_id: int | None = None
    page_key: str
    page_title: str
    user_message: str = Field(..., max_length=4000)
    history: list[FrontendCopilotMessage] = []
    page_context: dict[str, Any] | None = None


class FrontendSettingsConfigUpdateRequest(BaseModel):
    product_id: int
    core_keywords: list[str] = []
    related_keywords: list[str] = []
    competitor_asins: list[str] = []
    own_variants: list[str] = []


class FrontendRuleVersionRestoreRequest(BaseModel):
    product_id: int
    version: int


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
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backend database is not initialized.",
        )
    return session_factory


def _require_admin(current_user: UserResponse) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role is required for this action.",
        )


def _get_current_workspace_context(
    session_factory, user_id: str
) -> tuple[str, str, str]:
    from src.backend.models import Workspace, WorkspaceMembership

    with session_factory() as session:
        membership = session.scalar(
            select(WorkspaceMembership)
            .where(WorkspaceMembership.user_id == user_id)
            .order_by(WorkspaceMembership.created_at.asc())
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Current user does not belong to a workspace.",
            )

        workspace = session.get(Workspace, membership.workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Current workspace was not found.",
            )
        return workspace.id, workspace.name, membership.role


def _serialize_workspace_members(
    session_factory, workspace_id: str
) -> list[WorkspaceMemberResponse]:
    from src.backend.models import User, WorkspaceMembership

    with session_factory() as session:
        rows = session.execute(
            select(User.id, User.email, User.name, WorkspaceMembership.role)
            .join(WorkspaceMembership, WorkspaceMembership.user_id == User.id)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .order_by(WorkspaceMembership.role.asc(), User.email.asc())
        ).all()
    return [
        WorkspaceMemberResponse(
            id=row.id, email=row.email, name=row.name, role=row.role
        )
        for row in rows
    ]


def _upsert_workspace_member(
    session_factory, workspace_id: str, payload: WorkspaceMemberUpsertRequest
) -> WorkspaceMemberResponse:
    from src.backend.models import User, WorkspaceMembership

    normalized_email = payload.email.strip().lower()
    normalized_name = (payload.name or normalized_email.split("@", 1)[0]).strip()
    normalized_role = payload.role.strip().lower()
    normalized_password = payload.password.strip()
    if not normalized_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Member email is required."
        )
    if not normalized_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member password is required.",
        )
    if normalized_role not in VALID_WORKSPACE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported workspace role.",
        )

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
            membership = WorkspaceMembership(
                workspace_id=workspace_id, user_id=user.id, role=normalized_role
            )
            session.add(membership)
        else:
            if membership.role == "admin" and normalized_role != "admin":
                admin_count = (
                    session.scalar(
                        select(func.count())
                        .select_from(WorkspaceMembership)
                        .where(
                            WorkspaceMembership.workspace_id == workspace_id,
                            WorkspaceMembership.role == "admin",
                        )
                    )
                    or 0
                )
                if admin_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="At least one workspace admin must remain assigned.",
                    )
            membership.role = normalized_role

        session.commit()
        session.refresh(user)
        session.refresh(membership)
        return WorkspaceMemberResponse(
            id=user.id, email=user.email, name=user.name, role=membership.role
        )


def _remove_workspace_member(
    session_factory, workspace_id: str, user_id: str
) -> WorkspaceMemberResponse:
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
                detail="Workspace member was not found.",
            )

        if membership.role == "admin":
            admin_count = (
                session.scalar(
                    select(func.count())
                    .select_from(WorkspaceMembership)
                    .where(
                        WorkspaceMembership.workspace_id == workspace_id,
                        WorkspaceMembership.role == "admin",
                    )
                )
                or 0
            )
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one workspace admin must remain assigned.",
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


async def get_current_user(
    request: Request, token: str = Depends(oauth2_scheme)
) -> UserResponse:
    try:
        user = get_current_user_from_token(token, _get_runtime_session_factory(request))
    except AuthConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
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
            "http://127.0.0.1:3031",
            "http://localhost:3031",
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

    # ── Audit HIGH-2: /frontend/* 仅 loopback ─────────────────────────
    # 个人本机 dashboard 工具，/frontend/* 没有 auth 保护。如果用户绑定
    # 0.0.0.0 或在公司局域网启动，攻击面会暴露。这里在 router 之前 reject
    # 任何非 loopback 客户端访问 /frontend/*。其它路径（如 /api/auth/*）
    # 不受限，不影响未来若引入鉴权系统的 LAN 访问。
    #
    # 'testclient' 是 starlette TestClient 的固定 client.host，必须放行
    # 否则 pytest 会全员 403。
    _LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}

    @app.middleware("http")
    async def restrict_frontend_to_loopback(request: Request, call_next):
        if request.url.path.startswith("/frontend/"):
            client = request.client
            host = client.host if client else None
            if host not in _LOOPBACK_HOSTS:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "/frontend/* 仅允许本地 loopback 访问",
                        "clientHost": host,
                    },
                )
        return await call_next(request)

    # ── Sprint 5 B.6 · 统一异常处理 ────────────────────────────────────
    # FastAPI 默认把未捕获异常变成 500 + Python traceback 字符串，
    # 前端只能吃 plain-text 5xx。这里把 service 层 3 种常见异常映射为
    # 结构化 JSON（见 `_error_payload`）。HTTPException 保持默认行为，
    # 已有测试依赖其 `detail` 形状不变。
    # B.7 注：异常路径下 middleware 不会继续执行到 header 设置逻辑，
    # 所以 handler 必须自己把 X-Request-Id 回写到响应 header + body。
    def _build_error_response(
        request: Request,
        status_code: int,
        *,
        code: str,
        message: str,
        **extra_body,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        body_extra: dict = {**extra_body}
        if request_id:
            body_extra["request_id"] = request_id
        response = JSONResponse(
            status_code=status_code,
            content=_error_payload(
                code=code,
                message=message,
                path=request.url.path,
                extra=body_extra or None,
            ),
        )
        if request_id:
            response.headers["X-Request-Id"] = request_id
        return response

    @app.exception_handler(ValueError)
    async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return _build_error_response(
            request,
            status.HTTP_400_BAD_REQUEST,
            code="bad_request",
            message=str(exc) or "Bad request",
        )

    @app.exception_handler(LookupError)
    async def _lookup_error_handler(request: Request, exc: LookupError) -> JSONResponse:
        return _build_error_response(
            request,
            status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=str(exc) or "Resource not found",
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # 记录完整 traceback 到服务端日志，响应体仅返回清理过的消息
        # —— 避免把内部实现细节（SQL / 文件路径）泄露给前端。
        request_id = getattr(request.state, "request_id", None)
        _LOGGER.exception(
            "unhandled exception on %s %s (request_id=%s)",
            request.method,
            request.url.path,
            request_id,
        )
        return _build_error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_error",
            message="服务器内部错误，请稍后重试。",
            type=type(exc).__name__,
        )

    @app.get("/", tags=["system"], response_model=HealthResponse)
    async def read_root() -> dict[str, str]:
        return {
            "service": APP_TITLE,
            "status": "ok",
            "version": APP_VERSION,
        }

    @app.get("/health", tags=["system"], response_model=HealthResponse)
    async def healthcheck() -> dict[str, str]:
        return {
            "service": APP_TITLE,
            "status": "ok",
            "version": APP_VERSION,
        }

    # ── Sprint 5 B.7 · Request-ID 中间件 ───────────────────────────────
    # 每个请求生成 UUID4 并写入 `request.state.request_id`，同时通过
    # `X-Request-Id` 响应头回传。客户端若已带 `X-Request-Id`（支持 CDN /
    # 上游代理透传），沿用原值。便于日志关联 + 前端 error toast 附带
    # request_id 供支持排查。
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "").strip()
        request_id = incoming if incoming else uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response

    # ── Sprint 5 C.1 · HTTP timing middleware ──────────────────────────
    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        start = _time_module.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (_time_module.perf_counter() - start) * 1000
            _record_metric(request.url.path, duration_ms, 500)
            raise
        duration_ms = (_time_module.perf_counter() - start) * 1000
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
        _record_metric(request.url.path, duration_ms, response.status_code)
        return response

    # ── Sprint 5 C.2 · /metrics endpoint ───────────────────────────────
    @app.get("/metrics", tags=["system"], response_model=MetricsResponse)
    async def metrics() -> dict:
        """Return in-memory request metrics accumulated since process start."""
        paths = {}
        for path, bucket in _METRICS_STORE.items():
            count = bucket["count"] or 1
            paths[path] = {
                "count": int(bucket["count"]),
                "avg_ms": round(bucket["total_ms"] / count, 1),
                "max_ms": round(bucket["max_ms"], 1),
                "errors": int(bucket["errors"]),
            }
        return {
            "uptime_seconds": round(_time_module.time() - _STARTUP_TS, 1),
            "paths": paths,
        }

    @app.get(
        "/frontend/workbench",
        tags=["frontend"],
        responses={
            400: {
                "model": ErrorResponse,
                "description": "ValueError from service layer",
            },
            500: {"model": ErrorResponse, "description": "Unhandled server exception"},
        },
    )
    async def read_frontend_workbench(product_id: int | None = None) -> dict:
        """为独立前端壳返回首页/共享壳聚合数据。"""
        return build_workbench_payload(product_id=product_id)

    @app.get("/frontend/upload", tags=["frontend"])
    async def read_frontend_upload(product_id: int | None = None) -> dict:
        return build_upload_page_payload(product_id=product_id)

    @app.get("/frontend/analysis", tags=["frontend"])
    async def read_frontend_analysis(product_id: int | None = None) -> dict:
        return build_analysis_page_payload(product_id=product_id)

    @app.get("/frontend/analysis/term/{term}", tags=["frontend"])
    async def read_frontend_term_detail(
        term: str, product_id: int | None = None, days: int = 30
    ) -> dict:
        """Sprint A.2 — 单 term 30 天详情：日聚合 + 应用过的规则 + 历史决策"""
        return build_term_detail_payload(product_id, term, days=days)

    @app.get("/frontend/actions", tags=["frontend"])
    async def read_frontend_actions(product_id: int | None = None) -> dict:
        return build_actions_page_payload(product_id=product_id)

    @app.get("/frontend/review", tags=["frontend"])
    async def read_frontend_review(product_id: int | None = None) -> dict:
        return build_review_page_payload(product_id=product_id)

    @app.get("/frontend/settings", tags=["frontend"])
    async def read_frontend_settings(product_id: int | None = None) -> dict:
        return build_settings_page_payload(product_id=product_id)

    @app.post("/frontend/upload/run-analysis", tags=["frontend"])
    async def run_frontend_analysis(payload: FrontendProductRequest) -> dict:
        return run_analysis_for_frontend(product_id=payload.product_id)

    @app.post("/frontend/upload/files", tags=["frontend"])
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

    @app.post("/frontend/settings/clear-runtime", tags=["frontend"])
    async def clear_frontend_runtime(payload: FrontendProductRequest) -> dict:
        return clear_runtime_for_frontend(product_id=payload.product_id)

    @app.get("/frontend/settings/full-backup", tags=["frontend"])
    async def export_frontend_full_backup(product_id: int) -> dict:
        return export_full_backup_for_frontend(product_id=product_id)

    @app.post("/frontend/settings/product-config", tags=["frontend"])
    async def update_frontend_settings_config(
        payload: FrontendSettingsConfigUpdateRequest,
    ) -> dict:
        return update_settings_config_for_frontend(
            product_id=payload.product_id,
            core_keywords=payload.core_keywords,
            related_keywords=payload.related_keywords,
            competitor_asins=payload.competitor_asins,
            own_variants=payload.own_variants,
        )

    @app.post("/frontend/settings/rule-versions/restore", tags=["frontend"])
    async def restore_frontend_rule_version(
        payload: FrontendRuleVersionRestoreRequest,
    ) -> dict:
        return restore_settings_rule_version_for_frontend(
            product_id=payload.product_id,
            version=payload.version,
        )

    @app.get("/frontend/settings/rule-versions/{version}", tags=["frontend"])
    async def preview_frontend_rule_version(version: int, product_id: int) -> dict:
        return preview_settings_rule_version_for_frontend(
            product_id=product_id,
            version=version,
        )

    @app.post("/frontend/settings/restore-backup", tags=["frontend"])
    async def restore_frontend_full_backup(
        payload: FrontendRestoreBackupRequest,
    ) -> dict:
        return restore_full_backup_for_frontend(
            product_id=payload.product_id,
            restore_as_new_product=payload.restore_as_new_product,
            backup_data=payload.backup_data,
        )

    @app.post("/frontend/actions/execution-batches", tags=["frontend"])
    async def create_frontend_execution_batch(
        payload: FrontendExecutionBatchCreateRequest,
    ) -> dict:
        return create_execution_batch_for_frontend(
            product_id=payload.product_id,
            batch_type=payload.batch_type,
            draft_note=payload.draft_note,
        )

    @app.patch("/frontend/actions/execution-batches/{batch_id}", tags=["frontend"])
    async def update_frontend_execution_batch(
        batch_id: int, payload: FrontendExecutionBatchUpdateRequest
    ) -> dict:
        return update_execution_batch_for_frontend(
            batch_id=batch_id,
            status=payload.status,
            execution_note=payload.execution_note,
            review_note=payload.review_note,
        )

    @app.get("/frontend/actions/export-bulk-csv", tags=["frontend"])
    async def export_amazon_bulk_csv(product_id: int | None = None) -> Response:
        """Sprint D.2 — 当前产品所有 negative 推荐导出为 Amazon SP Bulk CSV。"""
        from urllib.parse import quote

        result = build_amazon_bulk_csv_export(product_id)
        if result is None:
            raise HTTPException(status_code=404, detail="无可导出否词")
        csv_bytes, file_name = result
        # RFC 5987 — HTTP 头默认 latin-1，含中文必须用 filename*=UTF-8''<percent-encoded>，
        # 同时给 ASCII filename= 作 fallback。
        ascii_fallback = file_name.encode("ascii", "ignore").decode() or "export.csv"
        encoded = quote(file_name, safe="")
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{ascii_fallback}"; '
                    f"filename*=UTF-8''{encoded}"
                ),
            },
        )

    @app.post("/frontend/review/manual-reviews", tags=["frontend"])
    async def create_frontend_review_decision(
        payload: FrontendReviewDecisionRequest,
    ) -> dict:
        return submit_review_decision_for_frontend(
            product_id=payload.product_id,
            term=payload.term,
            term_type=payload.term_type,
            campaign_id=payload.campaign_id,
            relevance=payload.relevance,
            notes=payload.notes,
            force=payload.force,
        )

    @app.post(
        "/frontend/copilot/chat",
        tags=["frontend"],
        response_model=CopilotChatResponse,
    )
    async def chat_frontend_copilot(payload: FrontendCopilotChatRequest) -> dict:
        return process_frontend_copilot_turn(
            product_id=payload.product_id,
            page_key=payload.page_key,
            page_title=payload.page_title,
            user_message=payload.user_message,
            history=[msg.model_dump() for msg in payload.history],
            page_context=payload.page_context,
        )

    @app.post("/frontend/copilot/chat/stream", tags=["frontend"])
    async def chat_frontend_copilot_stream(
        payload: FrontendCopilotChatRequest,
    ) -> StreamingResponse:
        return StreamingResponse(
            process_frontend_copilot_turn_stream(
                product_id=payload.product_id,
                page_key=payload.page_key,
                page_title=payload.page_title,
                user_message=payload.user_message,
                history=[m.model_dump() for m in payload.history],
                page_context=payload.page_context,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/frontend/competitors", tags=["frontend"])
    async def frontend_competitors(product_id: int | None = None) -> dict:
        """Sprint C.1 — 内部竞品 ASIN 监控（实时计算，无 schema migration）。"""
        return build_competitors_payload(product_id)

    @app.get(
        "/frontend/insights/today",
        tags=["frontend"],
        response_model=InsightTodayResponse,
    )
    async def frontend_insights_today(product_id: int | None = None) -> dict:
        """Return today's cached AI insight for a product (or null)."""
        from src.backend.workbench_payload import _get_app_database_path
        from src.data.db import Database

        db_path = _get_app_database_path()
        with Database(str(db_path)) as db:
            today = get_today_insight(db, product_id)
        return {"today": today}

    @app.post(
        "/frontend/insights/generate",
        tags=["frontend"],
        response_model=DailyInsightRow,
    )
    async def frontend_insights_generate(product_id: int | None = None) -> dict:
        """Run analyzer.generate_insights and persist a fresh daily row."""
        from src.backend.workbench_payload import _get_app_database_path
        from src.data.db import Database

        db_path = _get_app_database_path()
        with Database(str(db_path)) as db:
            result = generate_and_store_insight(db, product_id)
        return result

    @app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
    async def login(payload: LoginRequest, request: Request) -> LoginResponse:
        try:
            user = authenticate_user(
                _get_runtime_session_factory(request), payload.email, payload.password
            )
            token = issue_access_token_for_user(user)
        except AuthConfigError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
            ) from exc
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
            ) from exc

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse(**user),
        )

    @app.get("/auth/me", response_model=UserResponse, tags=["auth"])
    async def read_auth_me(
        current_user: UserResponse = Depends(get_current_user),
    ) -> UserResponse:
        return current_user

    @app.get(
        "/workspaces/default", response_model=WorkspaceResponse, tags=["workspaces"]
    )
    async def read_default_workspace(
        request: Request, current_user: UserResponse = Depends(get_current_user)
    ) -> WorkspaceResponse:
        session_factory = _get_runtime_session_factory(request)
        workspace_id, workspace_name, membership_role = _get_current_workspace_context(
            session_factory, current_user.id
        )
        member_count = len(_serialize_workspace_members(session_factory, workspace_id))
        return WorkspaceResponse(
            id=workspace_id,
            name=workspace_name,
            role=membership_role,
            member_count=member_count,
        )

    @app.get(
        "/workspaces/default/members",
        response_model=list[WorkspaceMemberResponse],
        tags=["workspaces"],
    )
    async def list_default_workspace_members(
        request: Request,
        current_user: UserResponse = Depends(get_current_user),
    ) -> list[WorkspaceMemberResponse]:
        session_factory = _get_runtime_session_factory(request)
        workspace_id, _, _ = _get_current_workspace_context(
            session_factory, current_user.id
        )
        return _serialize_workspace_members(session_factory, workspace_id)

    @app.post(
        "/workspaces/default/members",
        response_model=WorkspaceMemberResponse,
        tags=["workspaces"],
    )
    async def upsert_default_workspace_member(
        payload: WorkspaceMemberUpsertRequest,
        request: Request,
        current_user: UserResponse = Depends(get_current_user),
    ) -> WorkspaceMemberResponse:
        _require_admin(current_user)
        session_factory = _get_runtime_session_factory(request)
        workspace_id, _, _ = _get_current_workspace_context(
            session_factory, current_user.id
        )
        return _upsert_workspace_member(session_factory, workspace_id, payload)

    @app.delete(
        "/workspaces/default/members/{member_user_id}",
        response_model=WorkspaceMemberResponse,
        tags=["workspaces"],
    )
    async def delete_default_workspace_member(
        member_user_id: str,
        request: Request,
        current_user: UserResponse = Depends(get_current_user),
    ) -> WorkspaceMemberResponse:
        _require_admin(current_user)
        session_factory = _get_runtime_session_factory(request)
        workspace_id, _, _ = _get_current_workspace_context(
            session_factory, current_user.id
        )
        return _remove_workspace_member(session_factory, workspace_id, member_user_id)

    return app


app = create_app()
