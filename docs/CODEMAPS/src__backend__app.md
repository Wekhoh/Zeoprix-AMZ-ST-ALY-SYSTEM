# src/backend/app.md

**Purpose:** FastAPI 后端应用入口，提供身份认证、工作区管理、产品分析、AI Copilot、导入/导出等 REST API。

**Last Updated:** 2026-04-25

## Public Surface

- `create_app()` — 创建并配置 FastAPI 应用（CORS、HTTPS redirect、错误处理、路由）
- `LoginRequest`, `LoginResponse`, `UserResponse` — 认证请求/响应模型
- `WorkspaceResponse`, `WorkspaceMemberResponse`, `WorkspaceMemberUpsertRequest` — 工作区模型
- `FrontendExecutionBatchCreateRequest`, `FrontendExecutionBatchUpdateRequest` — 执行批次请求
- `FrontendReviewDecisionRequest` — 审查决策请求
- `FrontendCopilotChatRequest` — Copilot 聊天请求
- `FrontendSettingsConfigUpdateRequest` — 设置更新请求
- `FrontendRuleVersionRestoreRequest`, `FrontendRestoreBackupRequest` — 版本恢复请求
- `oauth2_scheme` — OAuth2 密码流程依赖
- `_error_payload()` — 统一错误响应 JSON 构造
- `_record_metric()` — 记录单次请求指标（延迟、状态码）
- `get_current_user()` — FastAPI 依赖，从 JWT token 解析当前用户

## Key Dependencies

1. **src.backend.database** — 数据库连接、SessionFactory、schema 初始化
2. **src.backend.workbench_payload** — 工作台页面负载构造（分析、上传、设置等）
3. **src.backend.insights** — 生成和检索每日洞察

## Data Touched

**Backend Schema (SQLAlchemy models in src/backend/models):**
- `users` — 用户账户（email、password_hash、created_at）
- `workspaces` — 工作区（name、created_at）
- `workspace_memberships` — 工作区成员关系（role：admin/editor/viewer）

**Data Schema (SQLite in src/data):**
- `products` — 产品配置（间接通过 workbench_payload）
- `search_terms` — 搜索词数据（间接通过 workbench_payload）
- `rules` — 规则引擎规则（间接通过 workbench_payload）

## Used By

- Frontend HTTP 客户端 (`src/frontend/`)
- E2E 测试 (`tests/`)

## Architecture Notes

- **Lifespan:** 启动时初始化 SQLAlchemy engine & session_factory
- **Auth:** JWT token + dependency 注入 → `get_current_user()` → UserResponse
- **Metrics:** 内存中按路径累计请求统计（无持久化）
- **Error handling:** 所有异常统一走 `_error_payload()` 返回标准 JSON 形状
- **CORS:** 允许 localhost:3000（前端开发）

## External Dependencies

- **fastapi** (~0.104.1) — REST 框架
- **sqlalchemy** (~2.0) — ORM
- **pydantic** (~2.x) — 数据验证
- **bcrypt** (~4.x) — 密码哈希
- **pyjwt** (~2.x) — JWT token
