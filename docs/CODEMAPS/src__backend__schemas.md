# src/backend/schemas.md

**Purpose:** Pydantic 响应 schema（类型化、OpenAPI 文档自动生成）。

**Last Updated:** 2026-04-25

## Public Surface

- `HealthResponse` — 健康检查响应（service、status、version）
- `MetricsPathStat` — 单条路由指标（count、avg_ms、max_ms、errors）
- `MetricsResponse` — `/metrics` 响应（uptime_seconds、paths）
- `ErrorResponse` — 错误响应（code、message、path、details）
- `CopilotChatResponse` — Copilot 聊天响应（role、content、metadata）
- `DailyInsightRow` — 每日洞察行（insight、timestamp）
- `InsightTodayResponse` — 今日洞察响应（insights、generated_at）

## Key Dependencies

- **pydantic** — 数据验证框架

## Data Touched

**None (schema definition only)**

## Used By

- **src.backend.app** — 所有路由处理函数返回类型注解
- **FastAPI** — 自动生成 OpenAPI 文档

## Architecture Notes

- **OpenAPI Integration:** Pydantic 模型自动转换为 OpenAPI schema
- **Type Safety:** 所有响应字段都有类型检查和序列化
- **Partial Coverage (Sprint 5 B.8):** 目前仅覆盖 Health/Metrics/Error，后续可补充其他页面响应

## External Dependencies

- **pydantic** (~2.x) — 数据验证
