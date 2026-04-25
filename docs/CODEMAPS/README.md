# CODEMAPS Index

**Last Updated:** 2026-04-25

本文档是 AMZ 搜索词分析系统后端 Python 模块的架构导览。每个 codemap 记录了关键模块的职责、公开 API、关键依赖、数据接触、被谁调用等信息。

## Backend Modules (SQLAlchemy)

### Authentication & Workspace Management

| Module | Purpose |
|--------|---------|
| [database.md](src__backend__database.md) | SQLAlchemy 配置、Engine、SessionFactory、schema 初始化 |
| [models.md](src__backend__models.md) | 后端用户、工作区、成员关系 ORM 模型 |
| [auth.md](src__backend__auth.md) | JWT 认证、密码哈希、用户认证 |

### API & Response Handling

| Module | Purpose |
|--------|---------|
| [app.md](src__backend__app.md) | FastAPI 应用入口、所有 REST 路由 |
| [schemas.md](src__backend__schemas.md) | Pydantic 响应 schema（OpenAPI 自动生成） |

### Business Logic & Pages

| Module | Purpose |
|--------|---------|
| [workbench_payload.md](src__backend__workbench_payload.md) | 工作台各页面负载构造（分析、上传、设置、审查） |
| [copilot_chat.md](src__backend__copilot_chat.md) | Copilot 聊天处理（请求解析、流式响应） |
| [insights.md](src__backend__insights.md) | 每日洞察生成与检索 |

## Data Layer (SQLite)

| Module | Purpose |
|--------|---------|
| [db.md](src__data__db.md) | SQLite 数据库操作主类（CRUD、慢查询追踪） |
| [models.md](src__data__models.md) | SQLite 架构定义（表、索引、默认规则） |
| [parser.md](src__data__parser.md) | 文件解析（Excel、CSV） |
| [aggregator.md](src__data__aggregator.md) | 数据聚合与指标计算 |

## Rules Engine

| Module | Purpose |
|--------|---------|
| [engine.md](src__rules__engine.md) | 规则引擎（评估、执行） |
| [asin_rules.md](src__rules__asin_rules.md) | ASIN 规则类型与验证 |
| [keyword_rules.md](src__rules__keyword_rules.md) | 关键词规则类型与匹配 |

## AI & Analysis

| Module | Purpose |
|--------|---------|
| [client.md](src__ai__client.md) | Claude API 客户端（流式支持） |
| [analyzer.md](src__ai__analyzer.md) | 文本分析（相关性、竞品识别） |
| [chat.md](src__ai__chat.md) | 聊天会话管理（历史、多轮） |
| [copilot.md](src__ai__copilot.md) | Copilot 逻辑（上下文感知、流式） |

### Analysis Pipelines

| Module | Purpose |
|--------|---------|
| [asin_analyzer.md](src__analysis__asin_analyzer.md) | ASIN 分析流程（规则+AI） |
| [truth_replay.md](src__analysis__truth_replay.md) | 真值重放验证 |

## Configuration & Export

| Module | Purpose |
|--------|---------|
| [settings.md](src__config__settings.md) | 全局应用设置（API keys、DB URL） |
| [logger.md](src__config__logger.md) | 日志系统配置 |
| [manager.md](src__config__manager.md) | 配置管理（产品级、版本控制） |
| [product_defaults.md](src__config__product_defaults.md) | 产品默认配置模板 |
| [exporter.md](src__export__exporter.md) | 数据导出（Excel、备份、恢复） |

## Services

| Module | Purpose |
|--------|---------|
| [settings_service.md](src__services__settings_service.md) | 工作区设置服务（RBAC、成员管理） |

## Quick Stats

- **25 Python modules** with CODEMAPS
- **7 packages:** backend, data, rules, ai, analysis, config, export, services
- **1,600+ lines** of documentation
- **All generated** from actual source code (non-placeholder content)
- **Last scanned:** 2026-04-25

## How to Use This Index

1. Find your module of interest in the tables above
2. Click the link to open the detailed CODEMAP
3. Each CODEMAP contains:
   - Purpose statement
   - Public API exports (functions, classes)
   - Key dependencies (top-3 imports)
   - Data touched (DB reads/writes)
   - Used by (which other modules call it)
   - Architecture notes

## Key Architecture Patterns

- **Dual Database Strategy:** SQLAlchemy for users/workspaces; SQLite for products/search_terms
- **Slow Query Tracking (Sprint 5 C.3):** db.py logs queries exceeding threshold
- **In-Memory Metrics (Sprint 5 C.2):** app.py accumulates per-path request statistics
- **Pydantic Schemas (Sprint 5 B.8):** Typed responses enable auto-generated OpenAPI docs
- **Context-Aware Copilot:** Chat adapts prompts based on page context

## Related Files

- `../../README.md` — Project overview
- `../../ARCHITECTURE.md` — System design decisions (if exists)
- `../../API.md` — API documentation (if exists)
