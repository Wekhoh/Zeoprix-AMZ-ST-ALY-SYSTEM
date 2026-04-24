"""Typed response schemas — Sprint 5 · B.8 partial (2026-04-24).

把高频 / 稳定形状的响应体从 `dict[str, Any]` 升级为 Pydantic BaseModel。
好处：

1. **OpenAPI 文档自动带形状**：`/docs` 里每个 endpoint 的 response 都有
   字段级 schema，给前端工程师 / 第三方集成方一个契约。
2. **未来前端 codegen**：`openapi-typescript` 之类工具可以直接产 TS 类型，
   `backend.ts` 不再手写形状。
3. **响应契约漂移可检测**：改 handler 返回 shape 会触发 mypy / runtime
   序列化错误，而不是在前端运行时出 `undefined`。

当前阶段（B.8 partial）只覆盖 3 组高频响应：Health / Metrics / Error。
B.8 后续可按需补 `CopilotEnvelope` / `DailyInsightResponse` / Workbench
payload 等。现有 handler 返回 `dict[str, Any]` 的没动，因为 Pydantic 模
型化它们价值边际递减（前端已固化映射）。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Health / Root ────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """`GET /` 和 `GET /health` 的响应形状。"""

    service: str = Field(..., description="Service name, e.g. APP_TITLE")
    status: str = Field("ok", description="Liveness status; currently 'ok' only")
    version: str = Field(..., description="Semantic version from APP_VERSION")


# ── Metrics ──────────────────────────────────────────────────────────────


class MetricsPathStat(BaseModel):
    """Per-path request metrics bucket（C.2）。"""

    count: int = Field(..., description="Total requests observed since boot")
    avg_ms: float = Field(..., description="Arithmetic mean latency")
    max_ms: float = Field(..., description="Maximum latency observed")
    errors: int = Field(..., description="5xx response count")


class MetricsResponse(BaseModel):
    """`GET /metrics` 整体响应。"""

    uptime_seconds: float = Field(..., description="Seconds since process start")
    paths: dict[str, MetricsPathStat] = Field(
        default_factory=dict,
        description="Per-URL-path metrics; key is the request path",
    )


# ── Error envelope (B.6 / B.7) ───────────────────────────────────────────


class ErrorBody(BaseModel):
    """统一错误响应 body。"""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable message (zh-CN)")
    path: str = Field(..., description="Request path at time of error")
    request_id: str | None = Field(
        None,
        description="B.7 request-id for log correlation; None if middleware skipped",
    )
    type: str | None = Field(
        None,
        description="Python exception type name for 500 responses only",
    )


class ErrorResponse(BaseModel):
    """`{\"error\": {...}}` — 所有 ValueError / LookupError / Exception 的包装。"""

    error: ErrorBody


# ── Daily AI Insights (A.3 · Sprint 4) ───────────────────────────────────


class DailyInsightRow(BaseModel):
    """`daily_insights` 表一行的 JSON 表示。"""

    id: int = Field(..., description="Row primary key")
    product_id: int | None = Field(
        None,
        description="Product being analyzed; None means cross-product (rare)",
    )
    date: str = Field(..., description="ISO date, e.g. '2026-04-24'")
    summary: str = Field(..., description="AI-generated short narrative")
    key_findings: list = Field(
        default_factory=list,
        description="Top insights list, shape determined by analyzer",
    )
    recommendations: list = Field(
        default_factory=list,
        description="Suggested actions list, shape determined by analyzer",
    )
    statistics: dict = Field(
        default_factory=dict,
        description="Raw metrics used to derive the insight",
    )
    created_at: str = Field(..., description="ISO timestamp when row was persisted")


class InsightTodayResponse(BaseModel):
    """`GET /frontend/insights/today` 响应。`today` 为 null 表示当天未生成。"""

    today: DailyInsightRow | None = None
