# Engineering Backlog

**Last updated:** 2026-04-24
**Scope:** 子项目 B / C / D / E （Sprint 4 以后的持续工程化工作）

本文档按 ROI + blast radius 排序列出 4 大方向的具体可执行条目。每条含：
状态标记、改动面、估时、前置依赖。每次 session 推进 1–3 条高优先项后再回看。

---

## 状态图例

- ✅ 已完成
- 🟢 低风险 · Quick win（≤ 1h，隔离性强，可独立落地）
- 🟡 中风险（1–3h，跨模块或需小幅重构）
- 🔴 高风险（> 3h，需正式 spec → plan → 实施流程）
- 🔒 阻塞（等待前置项）

---

## B · 后端架构 + 代码质量审计

**目标：** 清理 Streamlit legacy、厘清 service 边界、统一错误处理、结构化日志。

| ID | 标题 | 状态 | 改动面 | 估时 |
|---|---|---|---|---|
| B1 | 审计 `src/ui/pages/*` 在 backend 的依赖链 | 🟢 | 仅 grep/分析，无改动 | 30m |
| B2 | 抽取 `src/ui/pages/settings_data.py` 业务逻辑到 `src/services/settings_service.py` | ✅ 9d852eb | workbench_payload + 新 service 层 | 2h |
| B3 | 抽取 `src/ui/pages/home.py` 业务到 `src/services/workbench_service.py` | ✅ 已生效 | backend 已通过 `workbench_payload.py` 平行实现完全解耦 home.py | - |
| B4 | 验证 `src/app.py` Streamlit 入口在 backend runtime 不被引用 | ✅ 已审计 | 唯一残留引用（`settings_service.py`）已在 f2717e9 改为惰性包装消除 | 15m |
| B5 | 删 `src/app.py` + `src/ui/pages/` + `src/ui/components/` + `src/ui/styles.py/utils.py` | ✅ bf372dd/b2e81a1/cc629b7/c943cfd/18a88f5（5 步完成） | ~9000 行遗留删除 + 4 test 文件整理 | 3h |
| B6 | FastAPI 全局 exception handler 统一 HTTPException 结构（避免 fastapi-global-exception-handler-gotcha） | ✅ 436ff49 | 1 文件 + 2 tests | 30m |
| B7 | 结构化日志（JSON formatter + request-id 中间件） | ✅ 8e2fda6 + 8e562df | 中间件 + opt-in JSON formatter (AMZ_LOG_JSON) + 6 tests | 1.5h |
| B8 | Pydantic 严格化（所有 `dict[str, Any]` 返回体替换为 BaseModel） | 🟡 部分 acbf6de + 4807409 + d7d0db4 | 已覆盖 Health/Metrics/Error/Insights/CopilotEnvelope 9 schema；Workbench payload 等大 dict 未动 | 3h |
| B9 | 删 `src/ui/pages/settings_rules.py`（只 4% 覆盖率，最脏） | ✅ 随 B5 一起删（18a88f5） | 随 src/ui/ 整包删除 | 30m |

**建议路径：** B1 → B2 → B3 → B4 → B5（清理链）；并行 B6 → B7 → B8。

---

## C · 可观测性 + 性能基线

**目标：** 后端 metrics、前端 Web Vitals、慢查询追踪、性能预算。

| ID | 标题 | 状态 | 改动面 | 估时 |
|---|---|---|---|---|
| C1 | 后端 request-timing 中间件（log 每个 API p50/p95） | ✅ | `src/backend/app.py` middleware | 45m |
| C2 | 新 endpoint `GET /metrics`（Prometheus-style 或简单 JSON） | ✅ | 1 endpoint | 45m |
| C3 | SQLite 慢查询追踪（执行时间超阈值记录 + 聚合统计） | ✅ 1c417a8 | `src/data/db.py` + 7 tests | 1h |
| C4 | 前端 Web Vitals 埋点（`onCLS` / `onINP` / `onLCP` + console 或 beacon） | ✅ 4216a25 | `frontend/src/app/layout.tsx` | 45m |
| C5 | 前端 Sentry-lite error boundary 每页 | ✅ 78f2273 | 6 页 + `frontend/src/app/error.tsx` | 1.5h |
| C6 | 性能预算记录（backend 冷启时间 baseline + CI check，3000ms 天花板） | ✅ a92b874 | `.github/workflows/ci.yml` 新 `perf-budget` job | 1h |
| C7 | 后端启动时间 profile（识别最慢 import） | ✅ 2de51aa | 一次性脚本 | 30m |
| C7 续 | 冷启动优化：google.genai + streamlit 惰性化（7770ms → 1037ms，-87%） | ✅ 6547bf6 · f2717e9 | 2 文件 | 1h |

**建议路径：** C1 + C2 并行（都在 app.py） → C4 → C3 → C5 → C6。

---

## D · 测试完整度

**目标：** Playwright E2E 覆盖 6 页关键路径、前端 vitest 补齐、后端覆盖 85%+。

| ID | 标题 | 状态 | 改动面 | 估时 |
|---|---|---|---|---|
| D1 | Baseline coverage report（402 passed / 57% total）归档 | ✅ | `coverage.xml` 已生成于项目根 | - |
| D2 | `pytest.ini` 加 coverage config + 阈值（backend ≥ 85%） | ✅ | 1 文件 | 15m |
| D3 | 提升 `src/ai/client.py` 覆盖率从 34% → 70%（加 generate/generate_json 的错误路径测试） | ✅ 2f6d826 | 新增 unit test | 1.5h |
| D4 | 提升 `src/backend/copilot_chat.py` 从 58% → 80%（SSE error + cancel 路径） | ✅ f83e2c9（error/outer exception 路径完成；timeout/cancel 延后） | 新增 unit test | 1.5h |
| D5 | Playwright 初始化（`npm i -D @playwright/test` + `playwright.config.ts`） | 🟢 | frontend/ 新 config | 45m |
| D6 | E2E smoke：首页加载 + 6 tab 跳转 + Copilot 发消息 + 流式响应 | 🔴 🔒(D5) | 6 tests | 3h |
| D7 | E2E 关键路径：upload → analysis → review → actions → export | 🔴 🔒(D5) | 5 tests | 4h |
| D8 | Frontend vitest 初始化 + 3-5 smoke（`copilot-rich-text` / `copilot-stream` SSE parser 单测） | 🟡 | 新 config + tests | 2h |

**建议路径：** D2 → D3 → D4（pytest 加固）；D5 → D8（vitest 补齐）；D6 + D7 放最后（大工程）。

---

## E · 工程化 + 文档

**目标：** CI/CD、Architecture 文档、新成员 onboarding、CODEMAPS。

| ID | 标题 | 状态 | 改动面 | 估时 |
|---|---|---|---|---|
| E1 | `docs/ENGINEERING_BACKLOG.md`（本文档） | ✅ | 1 文件 | - |
| E2 | `.github/workflows/ci.yml`（pytest + frontend build + type-check） | ✅ | 1 文件 | 30m |
| E3 | `docs/ARCHITECTURE.md`（后端分层 + 前端 component tree + 数据流） | ✅ 8558bed | 1 文件（368 行） | 1.5h |
| E4 | `docs/CODEMAPS/` 按模块自动生成 (use doc-updater skill 或手写) | 🟡 | 多文件 | 2h |
| E5 | `CONTRIBUTING.md` + 开发者 setup 指南 | ✅ a795df7 | 1 文件 | 30m |
| E6 | `CHANGELOG.md` 从 Sprint 1 倒推整理 | ✅ b22a60e | 1 文件 | 1h |
| E7 | Dependabot config（后端 + 前端每周扫 security） | ✅ | `.github/dependabot.yml` | 15m |
| E8 | Pre-commit hooks（black / ruff / prettier / tsc） | 🟡 需定偏好 | `.pre-commit-config.yaml` | 1h |

**建议路径：** E1（已完）→ E2 → E5 → E6 → E3 → E4 → E7 → E8。

---

## Session 进度（截至 2026-04-24 续推）

**已完成（19/32 ≈ 59%）：** B2 · B6 · C1 · C2 · C3 · C4 · C5 · C7 · D1 · D2 · D3 · D4（主要路径）· E1 · E2 · E3 · E5 · E6 · E7 · A1-A3（Sprint 4 流式 + hyperlink + 每日洞察）· UX（Copilot 可折叠）

**剩余未做：**
- **B3** workbench_service 抽取（2h）
- **B4** src/app.py backend runtime 引用审计（15m · quick win）
- **B5** Streamlit legacy 整体删除（🔴 blocked by B3 + test_app_navigation.py 耦合）
- **B7** 结构化日志 JSON + request-id（1.5h）
- **B8** Pydantic 严格化（🔴 3h · 多 handler）
- **B9** 删 settings_rules.py（🔒 由 B2 解锁，需整合 coverage gate）
- **C6** 性能预算 CI check（1h · 需先 C1/C4 baseline 数据）
- **D4 残留** timeout + cancel 路径（SSE 深入）
- **D5 + D6 + D7** Playwright E2E 全量（🔴 3-7h · 大工程）
- **D8** vitest frontend unit（需定 test runner 偏好）
- **E4** CODEMAPS（2h · 可用 doc-updater agent）
- **E8** pre-commit hooks（需定 linter 组合偏好）

**下一步 ROI 排序（主人可挑）：**
1. **B4**（15m）→ 快速审计，为 B5 铺路
2. **B7**（1.5h）→ 结构化日志，与 C1 完美搭配
3. **E4**（2h）→ 纯文档，可并行 agent 生成
4. **D4 残留**（1h）→ SSE 鲁棒性收尾

---

## 维护约定

- 每完成一条 → 状态改 ✅ + 写下 commit SHA 引用
- 新识别到的债务 → 加入对应子项目末尾 + 评估风险级别
- 每月 review 一次（删已完成/失效条目，重排优先级）
