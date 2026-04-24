# Architecture

**Last updated:** 2026-04-24
**Scope:** 后端分层 + 前端组件树 + 数据流 + 技术栈 + Streamlit legacy 状态

本文档是新成员 onboarding + 后续重构（B.3/B.5）+ E2E 测试作者（D.5+）的架构底稿。

---

## 1 · 技术栈

| 层 | 技术 | 版本 / 备注 |
|---|---|---|
| 后端框架 | FastAPI + Uvicorn | Python 3.11，`create_app()` factory |
| 数据库 | SQLite 3 | `data/db/app.db` 主业务，`data/db/backend_app.db` auth |
| ORM（auth） | SQLAlchemy 2 | 仅 User / Workspace / Membership |
| ORM（业务） | 无 | 自写 `src/data/db.py::Database` 直接 sqlite3 |
| AI | google-genai | Gemini 3 Flash Preview（`gemini-2.5-flash`）|
| 前端框架 | Next.js 16 | App Router + Turbopack + React 19 |
| 样式 | Tailwind CSS 4 | `@theme inline` tokens，Amazon Ads palette |
| 前端字体 | Geist Sans + Geist Mono | via `next/font/google` |
| 图标 | lucide-react | |
| 前后端协议 | REST + SSE | `/frontend/*` 路由，Copilot 流式走 SSE |
| 测试 | pytest + pytest-cov | 前端无测试框架（D.5/D.8 待建） |
| CI | GitHub Actions | `.github/workflows/ci.yml` pytest + frontend build |

---

## 2 · 仓库结构（精简）

```
AMZ搜索词分析系统/
├── frontend/                       # Next.js 16 应用
│   ├── src/
│   │   ├── app/                    # App Router routes
│   │   │   ├── layout.tsx          # 根布局 + ThemeProvider + WebVitals
│   │   │   ├── error.tsx           # 根错误边界 (C.5)
│   │   │   ├── page.tsx            # /  工作台
│   │   │   ├── upload/page.tsx     # /upload
│   │   │   ├── analysis/page.tsx   # /analysis
│   │   │   ├── review/page.tsx     # /review
│   │   │   ├── actions/page.tsx    # /actions
│   │   │   ├── settings/page.tsx   # /settings
│   │   │   └── demo/page.tsx       # DS 陈列页
│   │   ├── components/
│   │   │   ├── dashboard-shell.tsx # 52px banner + sidebar(collapsible) + aside Copilot(collapsible)
│   │   │   ├── copilot-panel.tsx   # Seller Assistant 风 chat UI
│   │   │   ├── copilot-rich-text.tsx  # ASIN/关键词 hyperlink renderer (A2)
│   │   │   ├── daily-insights-card.tsx # 今日 AI 洞察卡 (A3)
│   │   │   ├── web-vitals-tracker.tsx  # Core Web Vitals 采集 (C.4)
│   │   │   ├── workbench-sections.tsx  # 首页 metric cards + insight cards + OperationsStream
│   │   │   ├── <page>-live-panel.tsx   # 每页状态 + 视觉外壳（6 页各一）
│   │   │   ├── <page>-mutation-panel.tsx # 每页表单/交互（6 页各一）
│   │   │   └── ui/                 # 通用原语：card/button/input/badge/toast/skeleton 等
│   │   └── lib/
│   │       ├── backend.ts          # BACKEND_BASE_URL + fetch helpers
│   │       ├── copilot-stream.ts   # SSE 客户端 (A1)
│   │       └── mock-data.ts        # 占位数据结构（向后兼容）
│   ├── tsconfig.json               # strict mode
│   ├── package.json
│   └── .env.production             # NEXT_PUBLIC_BACKEND_BASE_URL 等
│
├── src/                            # Python 后端 + AI + 数据层
│   ├── backend/                    # FastAPI 层
│   │   ├── app.py                  # create_app() 工厂 + 所有 HTTP routes + CORS
│   │   ├── auth.py                 # JWT + bootstrap admin + login handler
│   │   ├── database.py             # SQLAlchemy engine / SessionFactory（仅 auth 用）
│   │   ├── models.py               # User / Workspace / Membership ORM
│   │   ├── copilot_chat.py         # process_frontend_copilot_turn (+_stream for SSE)
│   │   ├── insights.py             # Daily insights service (A3)
│   │   └── workbench_payload.py    # 6 页 payload builder（入口汇总）
│   ├── services/                   # B.2 新建：服务层（解耦 ui.pages）
│   │   └── settings_service.py     # 4 函数 re-export（body 待 B.5 搬家）
│   ├── ai/
│   │   ├── client.py               # GeminiClient 封装（生成 + 流式）
│   │   ├── chat.py                 # ChatAssistant 多轮 + 流式 (A1)
│   │   ├── analyzer.py             # AIAnalyzer.generate_insights (A3)
│   │   ├── copilot.py              # 上下文包装 / envelope 构造
│   │   └── prompts.py              # 提示模板
│   ├── analysis/                   # 规则前的数据处理
│   │   ├── truth_replay.py         # 执行效果评估
│   │   └── asin_analyzer.py        # 按 ASIN 聚合分析
│   ├── data/
│   │   ├── db.py                   # Database(sqlite3) 主业务 DB wrapper
│   │   ├── models.py               # 表 schema + 默认规则
│   │   └── parser.py               # CSV/Excel 文件解析
│   ├── rules/
│   │   ├── engine.py               # analyze_search_terms(+_cached) 规则引擎入口
│   │   ├── asin_rules.py           # ASIN 规则
│   │   └── keyword_rules.py        # 关键词规则
│   ├── config/
│   │   ├── settings.py             # env 设置
│   │   ├── logger.py               # 统一 logger
│   │   └── manager.py              # 配置文件管理
│   ├── export/                     # 报表导出
│   └── ui/pages/                   # ⚠️ Streamlit legacy（B.5 待删）
│       ├── home.py upload.py analysis.py review.py actions.py settings.py
│       ├── settings_data.py        # B.2 shim：4 函数被 services/settings_service re-export
│       └── settings_rules.py       # 4% 覆盖率，B.9 待删
│
├── data/                           # 运行时数据
│   ├── db/app.db                   # 主业务 SQLite
│   ├── db/backend_app.db           # auth SQLite
│   └── exports/                    # 导出的 Excel 报表
│
├── tests/
│   ├── unit/                       # pytest unit tests (400+)
│   │   ├── test_backend_frontend_*.py  # FastAPI routes
│   │   ├── test_backend_frontend_copilot_stream.py  # SSE (A1 + D.4)
│   │   ├── test_backend_frontend_insights.py        # Daily insights (A3)
│   │   ├── test_ai_client.py       # GeminiClient (D.3)
│   │   ├── test_engine_*.py        # 规则引擎
│   │   └── ...
│   └── integration/                # 端到端
│
├── scripts/                        # 运维 / 工具
│   ├── profile_backend_startup.py  # C.7 冷启 profile
│   └── import_test_data.py         # 导入验收数据
│
├── docs/
│   ├── ARCHITECTURE.md             # 本文件
│   ├── ENGINEERING_BACKLOG.md      # B/C/D/E 子项目 backlog
│   ├── PRD.md / Plan.md / Task.md  # 产品 / 计划 / 任务历史文档
│   └── OPS_WORKBENCH_USER_GUIDE.md
│
├── .github/
│   ├── workflows/ci.yml            # E.2 CI
│   └── dependabot.yml              # E.7
│
├── CHANGELOG.md
├── CONTRIBUTING.md
├── start.ps1                       # Windows 一键启动（backend:8008 + frontend:3031）
├── requirements.txt
└── pytest.ini
```

---

## 3 · 后端分层

```
┌──────────────────────────────────────────────────────────┐
│                  HTTP Layer (FastAPI)                    │
│  src/backend/app.py::create_app()                        │
│  ├─ CORS middleware                                      │
│  ├─ timing middleware (C.1)                              │
│  ├─ /metrics (C.2)                                       │
│  ├─ /frontend/{workbench,upload,analysis,review,...}     │
│  ├─ /frontend/copilot/chat      (sync)                   │
│  ├─ /frontend/copilot/chat/stream (SSE)                  │
│  └─ /frontend/insights/{today,generate}                  │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│              Handler / Payload Layer                     │
│  src/backend/workbench_payload.py                        │
│  ├─ build_workbench_payload / build_*_page_payload       │
│  ├─ run_analysis_for_frontend                            │
│  ├─ create_execution_batch_for_frontend                  │
│  └─ upload_files_for_frontend / etc                      │
│                                                           │
│  src/backend/copilot_chat.py                             │
│  ├─ process_frontend_copilot_turn (sync)                 │
│  └─ process_frontend_copilot_turn_stream (async SSE)     │
│                                                           │
│  src/backend/insights.py                                 │
│  └─ get_today_insight / generate_and_store_insight       │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│                   Service Layer                          │
│  src/services/settings_service.py                        │
│    ← re-exports 4 fns from ui/pages/settings_data (shim) │
│    Future: body 搬家 + 新增 workbench_service /          │
│              analysis_service / review_service ...       │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│                Business Logic Layer                      │
│  src/rules/engine.py        → 规则引擎                   │
│  src/analysis/truth_replay  → 执行效果评估               │
│  src/ai/analyzer.py         → AI 洞察                    │
│  src/ai/chat.py             → Copilot 对话 / 流式        │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│                  Data Access Layer                       │
│  src/data/db.py::Database (sqlite3)                      │
│  src/data/parser.py (CSV/Excel)                          │
│  src/backend/database.py (SQLAlchemy, auth only)         │
└──────────────────────────────────────────────────────────┘
```

**关键原则：**
- HTTP Layer **不直接**访问 DB —— 经由 Handler/Payload 层。
- Handler Layer 目前对 business logic 层直接调用；**Service Layer 正在建设中**（B.2 shim → B.3 workbench_service → 逐步收口）。
- 未来 goal：Handler 只做"解析 request → 调 service → 组装 response"，不含业务逻辑。

---

## 4 · 前端分层

```
┌──────────────────────────────────────────────────────────┐
│  app/layout.tsx  (Root)                                  │
│  ├─ ThemeProvider (light/dark)                           │
│  ├─ ToastProvider                                        │
│  ├─ WebVitalsTracker (C.4)                               │
│  └─ CommandPalette                                       │
└──────────────────────────────────────────────────────────┘

     app/error.tsx  ← 根 Error Boundary (C.5)

┌──────────────────────────────────────────────────────────┐
│  app/{route}/page.tsx  (Server Component)                │
│  ├─ fetch payload from /frontend/{route}                 │
│  └─ <DashboardShell title subtitle productId aiCard>     │
│        └─ <{Route}LivePanel payload={...} />             │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  DashboardShell  (shared for all 6 routes + /demo)       │
│  ├─ Top navy banner (52px, zeoprix / ADS badge)          │
│  ├─ Left sidebar (collapsible 220px ↔ 60px)              │
│  ├─ Main content = {children}                            │
│  └─ Right aside Copilot (collapsible 360px ↔ 44px)       │
│        └─ <CopilotPanel> (SSE + ASIN hyperlink)          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  {Route}LivePanel  (Client Component，视觉外壳)          │
│  ├─ Local state + derived UI                             │
│  ├─ <MetricCards> + <TabPills> + <Filter>                │
│  └─ <{Route}MutationPanel> (表单 / 交互)                 │
└──────────────────────────────────────────────────────────┘
```

**State 约定：**
- 服务端 payload 以 prop 传入 LivePanel
- LivePanel 用 `useState` + `useEffect` 维护衍生状态
- MutationPanel 接回调 `onComplete` 把 mutation 结果反写 LivePanel 状态
- Copilot 会话持久化到 sessionStorage（key = `zeoprix-copilot:{pid}:{pageKey}`）
- Sidebar / Copilot 折叠状态持久化到 localStorage

---

## 5 · 关键数据流

### 5.1 首页工作台加载

```
Browser → GET /  (Next Server)
           │
           ├─ page.tsx 调用 getWorkbenchPayload()
           │       │
           │       └─ fetch /frontend/workbench?product_id=
           │             │
           │             ▼ (FastAPI)
           │         build_workbench_payload()
           │             │
           │             ├─ analyze_search_terms_cached() → rule engine
           │             ├─ get_execution_batch_effect_preview() → truth_replay
           │             └─ compose payload {stats, topActions, trendCards, ...}
           │
           └─ Render <DashboardShell><WorkbenchOverview payload />
```

### 5.2 Copilot SSE 流式对话

```
User types → sendMessage()
           │
           ├─ append empty assistant bubble
           ├─ AbortController.new()
           │
           └─ streamCopilotChat() → fetch POST /frontend/copilot/chat/stream
                 │
                 ▼ (FastAPI StreamingResponse)
             process_frontend_copilot_turn_stream()  async generator
                 │
                 ├─ context_pack = build_ai_context_pack(db)
                 ├─ ChatAssistant.process_message_stream()
                 │       │
                 │       ├─ yield ("context", label)
                 │       ├─ async for chunk in generate_stream():  (Gemini)
                 │       │      yield ("delta", text)
                 │       └─ yield ("envelope", {followUpPrompts, recs, ...})
                 │
                 └─ formatter yields bytes:
                     data: {"type":"context",...}\n\n
                     data: {"type":"delta","text":"..."}\n\n
                     ... (many)
                     data: {"type":"envelope",...}\n\n
                     data: {"type":"done"}\n\n
                 │
                 ▼ (Browser)
             fetch.getReader() → TextDecoder → split('\n\n')
                 │
                 ├─ onDelta → append to assistant bubble (打字机效果)
                 ├─ onEnvelope → update followUpPrompts / actionLinks
                 └─ onError → fallback to old /chat endpoint
```

### 5.3 每日 AI 洞察生成

```
User clicks "生成今日摘要" → POST /frontend/insights/generate?product_id=N
                                    │
                                    ▼
                        generate_and_store_insight()
                                    │
                        ├─ ensure_daily_insights_schema (CREATE IF NOT EXISTS)
                        ├─ analyze_search_terms_cached(db, product_id)
                        ├─ AIAnalyzer.generate_insights(results, product_context)
                        │       │
                        │       └─ Gemini 3 Flash (JSON prompt)
                        │
                        └─ INSERT INTO daily_insights + return row
                                    │
                                    ▼
                            DailyInsightsCard UI updates state
```

---

## 6 · 外部依赖

| 服务 | 用途 | 可用性要求 |
|---|---|---|
| Google Gemini API | Copilot 对话 / insights 生成 | GEMINI_API_KEY 必填，否则 AI 功能降级 |
| 本地 SQLite | 业务数据 | 无网络依赖 |
| OneDrive 同步 | 桌面用户的项目目录 | 不推荐，OneDrive 锁 .next 导致 rebuild 失败（已踩坑） |

---

## 7 · 已知遗留债务

### Streamlit Legacy（计划 B.5 删除）

`src/app.py` + `src/ui/pages/*` 约 **4400 行** Python 是旧 Streamlit 单体 UI 的遗留：

- 运行时：start.ps1 已不再启动 Streamlit，进程上无依赖。
- import 依赖：backend 经 **B.2 shim** 已完全解耦（`src.services.settings_service` 唯一桥梁）。
- 覆盖率：`settings_rules.py` 4%，`settings_data.py` 30%（除 4 个 backend-used 函数外其他都是 Streamlit UI）。
- 测试依赖：`tests/integration/test_app_navigation.py` + 若干 unit test 还 import `src.ui.pages.*`；删除时需一并清理。

**B.5 删除清单：**
1. 搬 `settings_data.py` 里 4 函数 body 到 `src/services/settings_service.py`
2. 删 `src/app.py`（Streamlit entry）
3. 删 `src/ui/pages/**/*`
4. 删 `src/ui/` 根目录 `__init__.py / styles.py / utils.py`
5. 删对应 tests：`test_app_navigation.py` / 若干其他
6. 预计 bundle / 冷启时间下降、覆盖率上升（pytest total 从 57% → ~75%+）

### 其他

- **冷启慢 (C.7 profile)**：`google-genai` import 占 3.14s。lazy-init 可省 80% 冷启时间。
- **Pydantic 部分宽松**：handler 返回 `dict[str, Any]` 居多，未用 response_model 严格化（见 B.8）。
- **前端无测试**：D.5/D.8 Playwright + vitest 尚未建立。

---

## 8 · 本文档 How-to-update

- 架构发生影响跨层（Service 层扩容 / 模块重组 / 新外部依赖）时更新本文档
- 新 route / page → 更新 §3 §4 图示
- 新 endpoint → 更新 §5 关键数据流
- 债务清理 → 移除 §7 对应条目
