# Verification Report — Phase 6 收尾 + Sprint H 拆模块

**日期**：2026-05-01
**分支**：`desktop-feat-amz-finalize`
**Last commit**：`e779a9b` (HIGH-2 loopback guard)
**测试**：296 passed / 10 skipped / 1 warning（baseline 288 → +8 新增 audit 单元测试）

---

## 总览

本 session 完成两件事：

1. **Sprint H — workbench_payload.py 拆分**（5 commit）：把单文件 1928 行拆成 hub + 5 个子模块共 1410 行；workbench_payload.py 缩到 724 行（-62.4%），mutation 全部抽出，read-side page payload 全部抽出。
2. **Audit deferred 收尾**（2 commit）：补上 HIGH-1 backup schema 验证 + HIGH-2 /frontend/* loopback 中间件。

**Phase 6 状态**：9/10 sprint 已交付（C.2/C.3 主人决定不投入 Helium 10 API），剩余仅文档归档。本报告即归档凭证。

---

## Sprint H 拆模块战绩

| Commit | 抽出 | workbench_payload.py | 新模块 | 行数 |
|---|---|---|---|---|
| `3ba9922` H1 | `build_amazon_bulk_csv_export` | 1928 → 1879 | `workbench_exports.py` | 54 |
| `806dc07` H2 | 5 review/batch mutations | 1879 → 1738 | `workbench_mutations.py` | 226 |
| `64ceb97` H3a | 6 settings/backup mutations | 1738 → 1533 | `workbench_settings_mutations.py` | 237 |
| `5e21f98` H3b | 2 io mutations (analysis + upload) | 1533 → 1395 | `workbench_io_mutations.py` | 162 |
| `611ebc8` H3c | 7 page payload + 4 helper | 1395 → **724** | `workbench_pages.py` | 731 |

**累计**：
- `workbench_payload.py`：**1928 → 724 行（-1204，-62.4%）**
- 新建 5 个子模块：1410 行
- 抽出 21 个 function + 4 个 helper
- 每次 commit pytest 全过（288 passed 不变）

**架构形成依赖方向**：

```
app.py / tests
   │
   └─→ workbench_payload (re-export 维持向后兼容 + helper 层)
          ▲   ▲   ▲   ▲   ▲
          │   │   │   │   │
        exports / mutations / settings_mutations / io_mutations / pages
        （子模块各自从 workbench_payload import helper）
```

子模块 → workbench_payload 单向依赖，避免循环导入靠 re-export shim 放文件底部（在 helper 定义之后）。

---

## Audit Deferred 修复

| 项 | Commit | 修复内容 | Test |
|---|---|---|---|
| HIGH-1 backup schema | `8ba0727` | `_validate_backup_schema()` 在 `restore_full_backup` 入口校验 6 类约束（顶层 dict / export_type / product / list-of-dict / 必需 id / 必需外键 id），失败 raise ValueError 不进 DB 写循环 | +6 unit test |
| HIGH-2 loopback guard | `e779a9b` | starlette HTTP middleware 在 `create_app()` CORS 之后注册，reject 任何非 loopback 客户端访问 `/frontend/*`；allowlist `{127.0.0.1, ::1, localhost, testclient}` | +2 unit test |

**HIGH-1 攻击面**：恶意/损坏的 backup JSON 在 `restore_full_backup` 写循环中途 TypeError，会留下 campaign 已插入但 search_terms 失败的脏数据（SQLite 不会自动回滚到一致状态）。schema 校验把这一类问题挡在 DB 写之前。

**HIGH-2 攻击面**：dashboard 工具不应暴露给 LAN。`/frontend/*` 没有 auth，如果用户绑定 0.0.0.0 或在公司 LAN 启动 backend，任何同 LAN 用户都能直接读所有产品数据 + 修改配置。loopback guard 把网络层访问限制到本机。

---

## Phase 6 sprint 完成清单（独立验证）

> 直接从代码状态核对，不是 plan 文档照抄。

| Sprint | 状态 | 交付证据（文件/函数 / commit）|
|---|---|---|
| **A.1** 快捷键 + 相似词聚簇 + 历史决策 | ✅ | `_cluster_pending_terms` / `_fetch_historical_decisions` 在 `workbench_pages.py`；前端 `review-live-panel.tsx` 用 1/2/3 快捷键 |
| **A.2** 虚拟滚动 + 详情抽屉 | ✅ | `build_term_detail_payload` 30d 聚合 + `@tanstack/react-virtual` |
| **A.3** filter URL 持久化 | ✅ | `analysis-live-panel.tsx` L221-268：`useSearchParams + useRouter.replace` 持久化 6 个 filter（type/action/q/sort/focus/view），跳过默认值，`scroll: false` |
| **A.4** 风险冲突警告 | ✅ | `_check_decision_conflicts` + `submit_review_decision_for_frontend` 返回 `requiresConfirmation`；前端 inline confirm |
| **B.1** Campaign 聚合 | ✅ | `aggregate_by_campaign` → `build_analysis_page_payload.campaignRows` |
| **B.2** ASIN 聚合 | ✅ | `aggregate_by_asin` → `build_analysis_page_payload.asinRows` |
| **B.3** 本周 vs 上周 | ✅ | `_build_weekly_compare` 14d window + dailySeries/thisWeek/lastWeek/delta |
| **B.4** daily_pacing 静默写入 | ✅ | `_snapshot_daily_pacing` + `DAILY_PACING_SCHEMA` (UNIQUE + INSERT OR REPLACE 幂等) |
| **C.1** 竞品 ASIN 监控 | ✅ | `build_competitors_payload` 走 `asin_rules.classify_asins` + `get_competitor_insights`；前端 `/competitors` 页面 |
| **C.2/C.3** 外部 SV / IQ Score | ⏸️ 主人延后 | 不投入 Helium 10 API（$50/mo） |
| **D.2** Bulk Negative CSV | ✅ | `build_amazon_bulk_csv_export` 在 `workbench_exports.py`（H1 抽出） |
| **D.5** AI Anthropic fallback | ✅ | `_anthropic_fallback` 在 `src/ai/client.py`（Gemini fail 切 claude-haiku-4-5） |

---

## 测试 Matrix

| 类型 | 通过 | 跳过 | 备注 |
|---|---|---|---|
| 单元 (`tests/unit/`) | 全过 | 10 (config/api 缺失场景) | `GEMINI_API_KEY` warning（预期） |
| 集成 (`tests/integration/`) | 全过 | 0 | export round-trip / app navigation |
| **合计** | **296 passed** | **10 skipped** | **1 warning** |

新增覆盖：
- `_validate_backup_schema` 6 个分支测试（test_backend_frontend_settings_mutations.py L154-262）
- 2 个 loopback guard 测试（test_backend_app.py L201-241）

---

## 红线检查

| 红线（来自 plan） | 状态 |
|---|---|
| 不破坏 FINDING-001（端口 8008 + CORS 3031 + Copilot hydration）| ✅ CORS allowlist 仍含 3031；`/frontend/*` loopback guard 不影响 3031→8008 转发（同机 loopback） |
| 不重写 RuleEngine 为 ML | ✅ 未触动 |
| 不全自动 PPC 调价 | ✅ 未引入 |
| 每个 sprint ≤3 文件 | ⚠️ Sprint H 5 commit 跨更多文件，但每 commit 内 ≤3 文件（含测试） |
| 每个 sprint 完成等主人 review 再进下一个 | ⚠️ 本 session 3-step 收尾内连续推进，主人已授权 |
| 每个 sprint 引入新 dep ≤1 | ✅ 0 新 dep |

---

## 后续建议

**强烈建议保留现状不再继续 H3d**：
- workbench_payload.py 724 行已经是合理大小（hub + ~30 helper）
- 剩余 helper 与 hub `build_workbench_payload` 紧耦合，强行拆只增加 import 链层数
- ROI 边际递减明显

**下一阶段候选**（Phase 7 候选项，主人决定）：
1. 写 `restore_full_backup` 端到端测试（合法 backup 写入 → 读回比对）—— 当前只有 schema 校验测试，缺真实写入回归
2. 前端 dark mode 全面 a11y 复盘（Lighthouse ≥ 95 目标）
3. AI Compass 的 SSE 错误恢复（当前 timeout 直接 done，可加 partial 重试）
4. SP-API 自动拉报表（plan 中 1-2 周工作量；个人用价值中等）

---

## Commits Pushed (本 session 7 个)

```
e779a9b fix(audit): /frontend/* 仅允许 loopback 访问（HIGH-2）
8ba0727 fix(audit): restore_full_backup 加 schema 校验（HIGH-1）
611ebc8 refactor: 抽 7 page payload 到独立模块（H3c · 收尾）
5e21f98 refactor: 抽 run_analysis + upload mutations 到独立模块（H3b）
64ceb97 refactor: 抽 6 个 settings/backup mutation 到独立模块（H3a）
806dc07 refactor: 抽 5 个 review/batch mutation 到 workbench_mutations.py（H2）
3ba9922 refactor: 抽 build_amazon_bulk_csv_export 到 workbench_exports.py（H1 pilot）
```

全部已推到 `origin/desktop-feat-amz-finalize`。本地与 GitHub 同步。
