# 变更日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [Unreleased]

### Added
- **[SPRINT-5]** 工程化基石 (2026-04-24):
  - `docs/ENGINEERING_BACKLOG.md` — B/C/D/E 4 子项目可执行 backlog
  - `docs/ARCHITECTURE.md` — 368 行架构概览（后端分层图 / 前端组件树 / 3 条数据流 / Streamlit legacy 债务）(E.3)
  - `.github/workflows/ci.yml` — 后端 pytest + 前端 build/typecheck 双 job CI
  - `.github/dependabot.yml` — 每周 pip/npm 扫描 + 每月 github-actions
  - `pytest.ini` — `--tb=short` + DeprecationWarning filter
  - 后端 `GET /metrics` endpoint + HTTP timing middleware (C.1+C.2)
  - `X-Response-Time-Ms` response header 注入所有 HTTP 请求
  - **B.6** 全局 exception handler：ValueError→400 / LookupError→404 / Exception→500 统一 `{error:{code,message,path}}` JSON
  - **B.7** Request-ID 中间件：UUID4 hex 或沿用上游 `X-Request-Id`；错误响应 body 和 header 都带 `request_id` 便于排查
  - **C.3** SQLite 慢查询追踪：`execute()` / `executemany()` 每次测时，阈值 `AMZ_DB_SLOW_QUERY_MS`（默认 100ms）触发 WARNING 日志 + `get_slow_query_stats()` 聚合
  - **D.4 完结** SSE timeout / client-cancel 路径测试（timeout → error+done 帧；CancelledError 传播保留）
- **[SPRINT-4-A3]** 每日 AI 洞察 (2026-04-24):
  - 新表 `daily_insights`（CREATE IF NOT EXISTS schema + product_id+date 索引）
  - `GET /frontend/insights/today?product_id=N` + `POST /frontend/insights/generate?product_id=N`
  - 工作台新增"今日 AI 洞察"卡：summary + key_findings + recommendations + "生成今日摘要"橙色按钮
  - 4 pytest 覆盖（空库 / 生成 / 读回 / product_id 隔离）
- **[SPRINT-4-A2]** Copilot ASIN / 关键词 hyperlink (2026-04-23):
  - `CopilotRichText` 组件：手写 regex tokenizer（B0 + 8 alnum → /review?focus=；反引号 → /analysis?focus=）
  - 无依赖新增，bundle 增量 < 2KB
- **[SPRINT-4-A1]** Copilot SSE 流式响应 (2026-04-23):
  - `GeminiClient.generate_stream()` 包 google-genai `generate_content_stream`
  - `ChatAssistant.process_message_stream()` 产 typed frames: context → delta → envelope → done
  - `POST /frontend/copilot/chat/stream` FastAPI `StreamingResponse` endpoint
  - `frontend/src/lib/copilot-stream.ts` SSE 客户端（fetch reader + TextDecoder + AbortController）
  - Copilot 面板流式输出 + 45s timeout cap + 切页自动中止 + 环境变量 fallback `NEXT_PUBLIC_COPILOT_STREAM_ENABLED`
  - 首字延迟 ≈4s → ≤0.8s
  - 6 pytest 覆盖 4 层（client / chat / SSE formatter / endpoint）
- **[SPRINT-4-UX]** 右侧 Copilot 可折叠 (2026-04-24):
  - 参照 sidebar 模式：360px ↔ 44px，左边缘浮动小圆按钮切换，localStorage 持久化

### Changed
- **[REL-001]** 运营工作台交付文档 (2026-04-11):
  - 新增 `docs/RELEASE_NOTES_2026-04-11.md`，总结首页工作台、AI 融合、执行闭环与备份恢复能力
  - 新增 `docs/OPS_WORKBENCH_USER_GUIDE.md`，面向真实亚马逊运营梳理日常使用路径与复盘节奏
- **[TEST-004]** 恢复验收环境的固定配置模板与回归测试 (2026-03-21):
  - 新增 `data/fixtures/acceptance_product_config.json` 作为真实 6 CSV 恢复时的产品配置模板
  - 新增 `tests/integration/test_import_test_data.py`，覆盖配置注入与边界词对齐场景
- **[DOC-002]** 数据计数说明文档 (2026-01-16 Ralph Loop #6):
  - 在 `SYSTEM_WORKFLOW.md` 添加"数据计数说明"章节
  - 解释461条原始记录 vs 316条唯一搜索词的差异
  - 明确 search_terms 表和 manual_reviews 表的关系

### Changed
- **[OPS-001]** 首页升级为运营工作台 + 执行闭环收口 (2026-04-11):
  - 首页新增当前工作状态、今日最优先 3 个动作、近 30 天趋势概览、搜索词结构概览、最近执行效果
  - 操作清单新增 `execution_batches` 执行批次，支持生成批次、标记已执行、保存复盘备注
  - 最近执行效果支持基于 baseline snapshot 和 latest snapshot 的前后对比，并输出 verdict 与 Top changes
  - 数据管理中的完整备份 / 恢复已覆盖 execution_batches、analysis snapshots、manual_reviews 等关键产品资产
- **[CORE-002]** 恢复链路与规则对齐收口 (2026-03-21):
  - `scripts/import_test_data.py` 支持恢复时自动注入验收配置，避免空 `products.config` 导致规则环境失真
  - `src/rules/engine.py` 增加 `weak_exact_keywords` 识别，并为“评估类规则”增加强相关保护，避免强相关词被泛化规则抢走
  - 验收模板补充 `weak_exact_keywords`、`weak_category_keywords`、核心词/相关词修正，用于贴近 workbook 的真实判断口径
- **[DOC-005]** 文档同步（以代码+数据库为准）:
  - 更新 README/PRD/Design/SYSTEM_WORKFLOW/RULE_ALIGNMENT_REPORT/CAMPAIGN_ANALYSIS_PLAN/TROUBLESHOOTING/Plan/Task
  - 修正文档中 T43 迁移脚本“缺失”描述为已存在；AI分歧/洞察未接入 UI 仍为现状
  - 补充规则阈值与导出说明，修正文档中的SQL示例
- **[DOC-003]** 文档与规则对齐修订 (2026-01-18):
  - 更新 README/PRD/Design/ADR/Plan/Task/RULE_ALIGNMENT_REPORT 与当前代码/数据库一致
  - RULE_ALIGNMENT_REPORT: 默认规则数量与对齐统计更新（72.9% 对齐）
  - T29 标记为待实现，进度统计同步调整
- **[DOC-004]** 文档与代码/数据库同步 (2026-01-18):
  - `docs/Design.md`：补充 manual_reviews 表与 ER 图，修正 Database/Gemini/AI/Chat 接口说明，补齐 logger.py 目录项
  - `docs/CAMPAIGN_ANALYSIS_PLAN.md`：更新数据库统计（analysis_results=632）

### Verified
- **[REL-002]** 成熟化版本发布前回归 (2026-04-11):
  - `pytest -q` → 379 passed, 10 skipped, 2 warnings
  - `scripts/evaluate_product.py ...` → objective 99.50 / llm avg 97.00 / total 98.50
  - 真实浏览器走查确认首页已展示“当前工作状态 / 今日最优先 3 个动作 / 近 30 天趋势概览 / 搜索词结构概览 / 最近执行效果”
- **[TEST-005]** 当前本地回归口径 (2026-03-21):
  - `DEBUG=true pytest -q` → 189 passed, 10 skipped, 3 warnings
  - 真实 6 CSV 恢复烟测：`search_terms=461`，`analysis_results=316`
  - mismatch 对齐率从 `56/71 = 78.9%` 提升至 `64/71 = 90.1%`
- **[TEST-002]** 边缘案例测试 (2026-01-16 Ralph Loop #7):
  - 空DataFrame处理 ✅
  - 最小必须列 ✅
  - 特殊字符 ✅
  - 全零值 ✅
  - 超大值 ✅
  - ASIN类型 ✅
  - Unicode中文 ✅
  - 负值 ✅

- **[PERF-001]** 性能验证 (2026-01-16 Ralph Loop #8):
  - 规则引擎：~24,000条/秒，线性扩展 O(n)
  - 数据库查询：所有查询 < 5ms
  - 461条记录处理时间 < 0.02秒

### Fixed
- **[BUG-005]** 导出/审核/动作类型语义漂移修复 (2026-03-21):
  - `src/data/models.py` 为 `ActionType` 增加动作族判断，兼容新旧 `negative` / `manual` 语义
  - `src/export/exporter.py` 与 `src/ai/chat.py` 改为使用动作族判断，恢复否词/手动词导出与聊天查询结果
  - `src/ui/pages/review.py` 与 `src/data/db.py` 修正 `reviewed` / pending 语义，并让 `save_analysis_result_by_term()` 使用确定性映射
  - `analyze_mismatches.py` 支持空数据库与显式参数，不再因空数据集崩溃
- **[BUG-004]** 导出功能数据不完整修复 (2026-01-16 Ralph Loop #13):
  - **问题**：导出功能使用`db.get_analysis_results()`读取数据库，但数据库只有68.5%覆盖率（316/461）
  - **根因**：`save_analysis_result_by_term`使用`LIMIT 1`，同词跨活动只保存第一条
  - **影响**：导出数据缺少145条搜索词（核心词如"neck pillow"等）
  - **修复**：`export_results()`改为使用`analyze_search_terms()`实时计算
  - **结果**：导出数据与UI显示一致，覆盖100%（316条唯一词）
  - **涉及文件**：`src/ui/pages/analysis.py`

- **[BUG-003]** 相关性映射与规则排除修复 (2026-01-16 Ralph Loop #11):
  - 修复`strong_core`未映射到`strong`进行规则匹配的问题
  - 在`_match_rule()`中添加`RelevanceLevel.to_category()`调用
  - 添加`relevance_not`条件支持，允许规则排除特定相关性
  - 更新"低转化高花费"规则，添加`relevance_not: strong`条件
  - 修复后"neck pillow"正确匹配"强相关有单"规则（置信度100%）

- **[TEST-003]** 数据同步一致性验证 (2026-01-16 Ralph Loop #11):
  - 相关性审核→搜索词分析 ✅
  - 相关性审核→首页仪表盘 ✅
  - 相关性审核→操作清单 ✅
  - 关键词库→规则引擎判断 ✅
  - 规则配置→分析结果 ✅
  - 产品切换→全局数据 ✅

- **[LINT-002]** 代码质量修复 (2026-01-15 Ralph Loop #3):
  - `db.py:1214` - 添加缺失的logger导入（潜在运行时错误）
  - `client.py:303` - 移除未使用的变量 `assistant_msg`
  - `asin_analyzer.py:356` - 使用 `observe_actions` 变量使逻辑更明确
  - `review.py:8` - 移除未使用的导入 `RelevanceSuggestion`
  - 141测试全部通过

- **[CORE-001]** 核心词配置与ASIN审核分离 (2026-01-15 Ralph Loop #1):
  - 修复核心词配置缺失问题（添加travel, pillow, neck等核心词）
  - ASIN审核UI分离：ASIN显示"竞争力评估"（可竞争/不可竞争/待观察）
  - 关键词显示"相关性标记"（5个等级）
  - 移除100条审核限制，改为500条
  - 修复规则引擎相关性逻辑

### Added
- **[DOC-001]** 系统工作流文档 (2026-01-15 Ralph Loop #1):
  - 创建 `docs/SYSTEM_WORKFLOW.md` 详细说明系统分析流程
  - 包含规则引擎工作原理、相关性检测优先级、动作类型说明
  - 覆盖所有页面功能说明和最佳实践

- **[BUG-003]** 相关性审核上传后显示0待审核项修复 (2026-01-15)：
  - **问题**：CSV上传分析后，相关性审核页面显示0条待审核，新词未进入审核队列
  - **根因**：`upload.py`的`run_analysis()`只将分析结果保存到`analysis_results`表，未创建`manual_reviews`记录
  - **修复**：在`run_analysis()`分析结果保存后，遍历所有结果，为`needs_review=True`或`relevance`为`pending/None`的词创建`manual_reviews`记录
  - **涉及文件**：`src/ui/pages/upload.py`
  - **验证**：上传32条搜索词CSV后，相关性审核页面正确显示"待审核总数: 32，关键词: 32"

- **[BUG-002]** 清空数据后相关性审核残留修复 (2026-01-15)：
  - **问题**：系统设置"清空所有搜索词数据"后，相关性审核页面仍显示316条待审核项
  - **根因**：清空逻辑未删除`manual_reviews`表数据
  - **修复**：在`settings.py`清空逻辑中添加`DELETE FROM manual_reviews WHERE product_id = ?`
  - **验证**：清空后相关性审核页面正确显示0条待审核

- **[UI-020]** 移除所有UI emoji (2026-01-15)：
  - **用户反馈**：不需要emoji装饰
  - **涉及文件**：`review.py`(27处)、`home.py`(2处)、`settings.py`(1处)
  - **替换策略**：
    - 标题emoji直接删除（如🔍相关性审核→相关性审核）
    - 词类型标识改为文字标签（🔤→[K]关键词，📦→[A] ASIN）
    - 按钮emoji直接删除（如🤖获取AI建议→获取AI建议）

### Added
- **[UI-019]** 按ASIN分析模式 (2026-01-14)：
  - **新增分析模式**: 在分析模式选择器中添加"按ASIN模式"，与"汇总模式"、"按活动模式"并列
  - **ASIN标识提取**: 从广告活动名称自动提取ASIN标识（如"BLK-1.2bid" → "BLK"）
  - **ASIN级别聚合**: `aggregate_by_asin_term()` 方法按 (ASIN标识, 搜索词, 词类型) 聚合数据
  - **ASIN级别分析**: `analyze_search_terms_by_asin()` 函数返回 `ASINAnalysisResult` 结果
  - **UI功能**:
    - ASIN筛选器（多选）
    - 统计卡片（唯一搜索词、ASIN变体、建议否定、自动保留/否定/观察）
    - 结果表格（搜索词、ASIN、类型、触发规则、主动作、自动处理、点击、订单、CVR）
    - 按ASIN对比视图（跨ASIN共同词汇的表现对比）
    - 导出功能（按ASIN分析结果、否定清单）
  - **100%对齐验证**: ASIN级别分析与用户手动标记完全对齐（61/61 = 100%）
  - **文件变更**: `src/ui/pages/analysis.py`, `src/rules/engine.py`, `src/data/aggregator.py`

- **[UI-017]** 人工审核勾选功能 (2026-01-14)：
  - **搜索词分析页面**：新增"已审核"列，支持勾选确认分析结果
  - **实时统计更新**：已审核数量实时显示在统计卡片（如 "0/205"）
  - **数据持久化**：审核状态保存到`manual_reviews`数据库表
  - **批量操作**：支持全选/清除已审核项
  - **导出功能**：仅导出已审核的关键词
  - **文件变更**：`src/ui/pages/analysis.py`, `src/data/db.py`

- **[DATA-001]** 数据一致性修复 (2026-01-14)：
  - **问题**：首页、操作清单、AI聊天使用`analysis_results`表旧数据，与搜索词分析页面不同步
  - **修复**：统一使用`analyze_search_terms()`实时分析
  - **action_type修复**：从`== "negative"`改为`.startswith("negative")`匹配`negative_exact`/`negative_phrase`
  - **影响页面**：首页(home.py)、操作清单(actions.py)、AI聊天(chat.py)
  - **验证**：首页205词需否定，179词待AI确认，与分析页面完全一致

- **[UI-018]** 按活动模式UI实现 (2026-01-14)：
  - **分析模式切换**：汇总模式 / 按活动模式 单选按钮
  - **按活动统计卡片**：唯一搜索词、涉及活动、自动保留、自动否定、继续观察、已审核
  - **表格显示**：搜索词、广告活动、类型、触发规则、主动作
  - **筛选功能**：动作类型、自动处理、词类型、搜索关键词

### Fixed
- **[LINT-001]** 代码质量修复 (2026-01-14)：
  - 移除`actions.py`未使用的`AnalysisResult`导入
  - 移除`analysis.py`未使用的`CampaignAnalysisResult`导入
  - 113个测试用例全部通过

- **[CAMPAIGN-001]** 按广告活动分析功能 (2026-01-13)：
  - **目标**: 同一关键词在不同活动中可有不同分析建议
  - **核心功能**:
    - `CampaignAnalysisResult` 数据类 - 保留活动维度的分析结果
    - `analyze_by_campaign()` 方法 - 按活动分别应用规则
    - `aggregate_by_campaign_term()` 方法 - 按活动+关键词聚合数据
    - `_determine_auto_action()` 方法 - 决定自动活动处理方式
  - **auto_action 决策逻辑**:
    - 规则指定 WITH_NEG → 直接返回 negate
    - 规则指定 NO_NEG → 直接返回 keep
    - 纯手动动作根据表现计算:
      - CVR >= 10% 且 orders >= 1 → keep (保留)
      - clicks >= 20 且 orders = 0 → negate (否定)
      - 其他 → observe (观察)
  - **代码审查修复**:
    - W1: 规则指定策略时直接遵循，不被表现覆盖
    - W2: campaign_id 空值验证，防止错误聚合
  - **测试验证**:
    - 新增 8 个单元测试 (TestCampaignAnalysis)
    - 集成测试: 461条记录，93个词出现在多个活动
    - neck pillow 在 5 个活动中验证成功
  - **文件变更**:
    - `src/rules/engine.py` - CampaignAnalysisResult, analyze_by_campaign
    - `src/data/aggregator.py` - aggregate_by_campaign_term
    - `tests/unit/test_sprint3.py` - TestCampaignAnalysis
    - `scripts/test_campaign_analysis.py` - 集成测试脚本
    - `docs/CAMPAIGN_ANALYSIS_PLAN.md` - 实施计划文档

- **[RULE-003]** 重新应用规则功能 (2026-01-13)：
  - **目标**: 规则变更后能立即重新应用到现有数据
  - **新增功能** (`src/ui/pages/settings.py`):
    - `reapply_rules_to_data()` 函数 - 重新应用规则到所有搜索词数据
    - "🔄 重新应用规则" 按钮 - 触发规则重新应用
    - 确认对话框 - 警告用户操作将覆盖之前的分析结果
  - **实现细节**:
    - 获取产品的所有搜索词数据 (DataFrame格式)
    - 自动计算派生指标 (CTR, CPC, CVR, ROAS)
    - 调用 RuleEngine.analyze() 重新分析
    - 通过 db.save_analysis_result_by_term() 更新分析结果
  - **E2E验证结果** (Claude in Chrome 2026-01-13):
    - ✅ 单规则变更验证: 禁用P40规则后重新应用
      - 基准: 需要否定205, 待AI确认166
      - 禁用P40后: 需要否定205, 待AI确认454 (+288)
    - ✅ 多规则变更验证: 启用P40 + P10阈值从$10改为$15
      - 结果: 需要否定205, 待AI确认742
    - ✅ 证实规则变更确实影响分析结果

- **[RULE-002]** 自定义规则管理系统 (2026-01-13)：
  - **目标**: 允许用户自定义增删改规则，支持更多分析指标
  - **数据库扩展** (`src/data/db.py`):
    - `get_all_rules()` - 获取所有规则（含禁用规则）
    - `create_rule()` - 创建新规则
    - `update_rule()` - 更新规则属性
    - `delete_rule()` - 删除规则
    - `toggle_rule()` - 切换规则启用/禁用状态
    - `reset_rules_to_default()` - 重置为默认规则
    - `create_rule_version()` - 创建规则版本快照
  - **规则引擎扩展** (`src/rules/engine.py`):
    - 新增条件支持:
      - `impressions_min`/`impressions_max` - 曝光量范围
      - `ctr_min`/`ctr_max` - 点击率(CTR)范围
      - `cpc_min`/`cpc_max` - 单次点击成本(CPC)范围
      - `sales_min`/`sales_max` - 销售额范围
      - `roas_min`/`roas_max` - 广告投资回报率范围
    - 自动计算派生指标（如CTR、CPC、ROAS）
  - **UI规则管理界面** (`src/ui/pages/settings.py`):
    - 新增"规则管理"Tab页
    - 规则列表展示：优先级、名称、条件摘要、动作、操作按钮
    - 添加新规则表单：
      - 基础配置：名称、动作、类型、优先级、全局/产品级
      - 条件配置4列布局：
        - 基础指标：花费、订单、点击、曝光
        - 效率指标：ACOS、CVR、CTR、CPC
        - 销售指标：销售额、ROAS
        - 特殊条件：相关性等级、自家变体ASIN、竞品ASIN、需AI判断
    - 编辑/禁用/删除规则功能
    - 重置为默认规则按钮
    - 规则统计卡片（启用规则数/总数）
  - **E2E验证** (Claude in Chrome 2026-01-13):
    - ✅ 规则管理Tab正常显示
    - ✅ 创建规则"高曝光低点击率"（曝光>=1000, CTR<=0.01）成功
    - ✅ 新规则显示在列表中：P50 高曝光低点击率
    - ✅ 启用规则计数从5/5更新为6/6
    - ✅ 条件摘要正确显示新指标

- **[RULE-001]** 规则对齐 - 用户否词逻辑自动化 (2026-01-13)：
  - **目标**: 将用户手动分析的107条否词决策逻辑对齐到系统规则引擎
  - **Phase 1 - 数据模型扩展** (`src/data/models.py`):
    - 新增 `NegativeType` 枚举: EXACT(否定精准), PHRASE(否定词组)
    - 新增 `ManualType` 枚举: EXACT(手动精准), PRODUCT(手动商品定位)
    - 新增 `RelevanceLevel` 枚举: STRONG/WEAK/IRRELEVANT/GENERIC/CAR
    - 新增 `ActionType` 枚举: 细分动作类型 (negative_exact, manual_product等)
    - 更新 `DEFAULT_RULES`: 16条规则覆盖关键词/ASIN多场景
  - **Phase 2 - 规则引擎扩展** (`src/rules/engine.py`):
    - `_match_rule()` 新增条件支持:
      - `clicks_min`/`clicks_max` - 点击数范围
      - `cvr_min`/`cvr_max` - 转化率范围 (自动计算)
      - `relevance` - 相关性等级匹配
      - `is_own_variant` - 自家变体ASIN识别
    - 新增 `_get_term_relevance()` 方法 - 基于关键词库判断相关性
    - `_get_action_type()` 细分动作类型:
      - 否定: negative_exact / negative_phrase
      - 手动: manual_exact / manual_product
      - 观察: observe / continue_observe / evaluate
    - 新增过滤方法: `get_negative_exact_keywords()`, `get_negative_phrase_keywords()`, `get_manual_exact_keywords()`, `get_manual_product_keywords()`
  - **Phase 4 - UI配置界面** (`src/ui/pages/settings.py`):
    - 新增第5个Tab "关键词库":
      - 不相关词库 (irrelevant_keywords)
      - 弱相关类目词库 (weak_category_keywords)
      - 太泛的词库 (generic_keywords)
      - 汽车相关词库 (car_keywords)
      - 自家变体ASIN (own_variants)
    - "规则配置"扩展:
      - 新品期模式开关 (is_new_product)
      - 样本量阈值: min_clicks_for_analysis(20), min_clicks_for_asin_neg(6), high_spend_no_order($20)
      - CVR阈值: good_cvr(10%), bad_cvr(5%)
    - `get_default_config()` 包含所有新默认值
  - **Phase 5 - 测试修复**:
    - `test_sprint3.py`: 更新断言适配新规则动作名
    - `test_sprint5.py`: 修正测试数据格式 (item dict vs nested data)
    - 单元测试结果: 82 passed, 10 skipped (API key), 0 failed
  - **Phase 5 - E2E验证** (Claude in Chrome 2026-01-13):
    - ✅ 系统设置页5个Tab正常显示：规则配置、关键词库、产品配置、API设置、数据管理
    - ✅ 规则配置Tab：新品期模式开关、样本量阈值(20/6/$20)、CVR阈值(10%/5%)
    - ✅ 关键词库Tab：5个词库输入区（不相关/弱相关/太泛/汽车/自家变体）
    - ✅ 关键词库说明正确显示规则映射（不相关→否定精准，弱相关→否定词组等）
    - ✅ 当前配置统计卡片（4种颜色区分：蓝/绿/琥珀/紫）
    - ✅ 首页仪表盘数据正常（166个词待AI确认，规则分布图表）

### Fixed
- **[UI-016]** AI助手弹出框修复 (2026-01-13)：
  - **输入框焦点样式**: 移除蓝色焦点边框线，改为纯净无边框设计
  - **发送按钮样式**: 改为蓝色背景 + 白色箭头图标，与整体深蓝主题一致
  - **快捷问题按钮**: 确保4个快捷问题（分析ACOS、优化建议、否词分析、投放建议）完整显示
  - **Hover对比度**: 优化按钮hover状态文字对比度，确保可读性
  - **CSS选择器修复**: 使用 `[data-testid="stChatInput"]` 精确定位Streamlit聊天输入组件
  - 修改文件：`src/app.py` (AI助手CSS样式)

- **[UI-015]** Premium UI修复 - 页面空白问题解决 (2026-01-12)：
  - **根本原因**：`.stApp` 容器 height 为 0px，导致所有内容被裁剪不可见
  - **诊断过程**：
    - 使用 `read_page` 确认 DOM 内容存在
    - 使用 JavaScript 检查计算样式发现 `.stApp { height: 0px; overflow: hidden }`
  - **修复方案**：
    - `.stApp` 添加 `min-height: 100vh !important; height: auto !important; overflow: visible !important`
    - 移除 `background-attachment: fixed` 避免与 Streamlit 内部样式冲突
  - **动画优化**：
    - 移除 `animation: ... backwards` 避免元素在动画前 opacity:0
    - 简化主内容区入场动画，设置 `opacity: 1` 确保可见性
    - 指标卡片动画从 `both` 改为 `forwards`
  - **标题样式简化**：
    - 移除 h1 的渐变文字效果（`-webkit-text-fill-color: transparent`）避免兼容性问题
    - 改用纯色 `var(--primary-900)`

### Changed
- **[UI-014]** 入场动画与微交互增强 (2026-01-12)：
  - **关键帧动画定义** (`styles.py`):
    - `fadeInUp` - 元素从下方淡入上升
    - `fadeIn` - 简单淡入效果
    - `slideInLeft` - 从左侧滑入
    - `pulse` - 呼吸脉冲效果
    - `shimmer` - 骨架屏加载闪烁
    - `glowPulse` - 聚焦时光晕脉冲
  - **指标卡片入场动画**:
    - 4张卡片依次入场（延迟0.1s/0.2s/0.3s/0.4s）
    - Hover时触发pulse呼吸效果
    - Hover时数字变为accent蓝色
  - **表格交互增强**:
    - 行悬停背景色变化 + 微右移动画
    - 平滑过渡效果 0.15s
  - **按钮点击反馈**:
    - `:active` 状态下移+缩小效果
  - **消息提示入场**:
    - Alert组件slideInLeft动画
  - **Tab切换动画**:
    - 内容面板fadeIn过渡
  - **输入框聚焦增强**:
    - glowPulse光晕动画
  - **滚动条美化**:
    - 自定义宽度8px
    - 圆角设计
    - Hover深色效果
  - **无障碍增强**:
    - `focus-visible` 蓝色轮廓
    - 平滑滚动 `scroll-behavior: smooth`

- **[UI-013]** 指标卡片CSS修复 + 快速操作按钮增强 + 数据管理功能 (2026-01-12)：
  - **指标卡片彩色条纹CSS修复**:
    - 问题：所有卡片都显示蓝色，而不是不同颜色（蓝/绿/琥珀/紫）
    - 根因：CSS选择器 `[data-testid="column"]` 不匹配Streamlit实际DOM `[data-testid="stColumn"]`
    - 诊断：使用JavaScript DOM检查确认选择器问题
    - 修复：更新选择器并添加 `!important` 确保优先级
    - 结果：4个指标卡片现在正确显示不同颜色（蓝色/绿色/琥珀色/紫色）
  - **快速操作按钮样式增强**:
    - 添加左侧蓝色强调条（4px渐变线）
    - Hover效果：光晕+微上浮
    - 背景渐变装饰
    - 使用CSS伪元素 `::before` 实现装饰效果
  - **数据管理功能增强** (`settings.py`):
    - 新增"导出规则配置"按钮 - 导出JSON格式规则配置
    - 新增"导出完整数据备份"按钮 - 导出产品完整数据（配置+活动+统计）
    - 新增"导入规则配置"文件上传器 - 从JSON恢复规则配置
    - 新增 `export_full_backup()` 函数处理完整备份
  - **分析页面批量操作增强** (`analysis.py`):
    - 新增"批量确认所有建议"按钮 - 将所有待确认项设为已确认（confidence=1.0）
    - 新增"导出全部结果"按钮 - 导出CSV格式分析结果
    - 更新 `export_results()` 函数支持 "all" 类型导出

- **[UI-012]** AI助手对话框重新设计 + 弃用警告修复 (2026-01-12)：
  - **AI助手对话框重新设计**:
    - 问题：标题"AI助手"黑色字体在蓝色背景上不协调
    - 问题：内容文字太贴近边缘，缺少内边距
    - 修复：使用内联样式强制白色标题字体 `color:#FFFFFF !important`
    - 增强：更精致的阴影 `0 8px 32px rgba(0,0,0,0.15)`
    - 增强：圆角增大至 16px
    - 增强：快捷问题按钮hover效果 - 微上浮+阴影
    - 增强：输入框focus状态蓝色轮廓 + 光晕
    - 增强：清除对话按钮hover变红色警告
    - 增强：Info消息使用天蓝色渐变背景
  - **Streamlit弃用警告修复**:
    - 问题：`use_container_width` 将在 2025-12-31 后移除
    - 修复：全部替换为新参数 `width="stretch"` 或 `width="content"`
    - 涉及文件：`app.py`, `home.py`, `upload.py`, `analysis.py`, `actions.py`, `settings.py`, `ai_chatbox.py`
    - 共修复 29 处弃用警告
  - **配色统一**:
    - `ai_chatbox.py` 中紫色渐变 `#667eea/#764ba2` 改为深蓝 `#2563EB/#1D4ED8`

- **[UI-011]** 创意设计增强与侧边栏修复 (2026-01-12)：
  - **侧边栏选中状态修复**:
    - 问题：选中状态文字不可见（白色文字在白色容器背景上）
    - 修复：添加CSS规则强制文字容器背景透明
    - 增强：选中状态使用高饱和蓝色渐变 `#2563EB → #1D4ED8`
    - Radio圆点改为白色填充，深蓝色内点
  - **创意动画系统**:
    - `@keyframes fadeInUp` - 内容入场上滑渐现
    - `@keyframes slideInLeft` - 侧边栏左侧滑入
    - 指标卡片交错入场动画（延迟递增 0.05s/卡片）
  - **自定义滚动条**:
    - 渐变滚动条轨道 `primary-300 → primary-400`
    - 圆角设计 + hover加深效果
  - **表格增强**:
    - 交替行色 `nth-child(even)` 浅灰背景
    - Hover行微缩放 `scale(1.005)` + 阴影
    - 悬浮行高亮 `accent-lighter` 背景
  - **卡片光效**:
    - Hover时斜向光带滑过效果 `translateX(-100%) → 100%`
    - 使用 `skewX(-15deg)` 创造动感
  - **装饰性背景**:
    - 主内容区右上角蓝色径向渐变装饰
    - 侧边栏底部渐变遮罩
  - **可访问性增强**:
    - `focus-visible` 蓝色轮廓 + 偏移
    - 禁用状态统一灰度样式
    - 文字选中高亮蓝色
  - **其他增强**:
    - 下载按钮绿色渐变主题
    - 数字输入框+/-按钮hover效果
    - 工具提示深色背景样式
    - 链接下划线hover动画
  - **验证**: Claude in Chrome全页面检查通过

- **[UI-010]** 深度UI优化 - 设计系统增强 (2026-01-12)：
  - **Streamlit主题配置**: 新建 `.streamlit/config.toml` 设置品牌蓝主色
    - `primaryColor = "#2563EB"` 修复Radio按钮圆点从红色改为蓝色
    - 统一背景色、文字色、字体配置
  - **侧边栏样式优化**:
    - 渐变背景 `linear-gradient(180deg, #F1F3F5 → #F1F5F9)`
    - 品牌标题蓝色 + 下划线装饰
    - Radio选中状态: 蓝色背景高亮 + 阴影效果
  - **指标卡片增强**:
    - 渐变背景 + 内阴影提升质感
    - Hover效果: 蓝色顶栏渐变显现
    - 数值渐变色 `linear-gradient(#0F172A → #2563EB)`
  - **警告/消息样式改进**:
    - Warning: 柔和琥珀色渐变 `#FFFBEB → #FEF3C7`
    - Info: 品牌蓝渐变 `#EFF6FF → #DBEAFE`
    - Success: 翠绿渐变 `#ECFDF5 → #D1FAE5`
  - **按钮层次系统**:
    - Primary: 蓝色渐变背景 + hover加深
    - Secondary: 透明背景 + 蓝色边框
  - **标题视觉层次**:
    - H1: 左侧4px蓝色accent条
    - H2: 深灰色 + 底部边框
  - **验证**: Claude in Chrome确认所有优化生效

- **[UI-009]** 现代SaaS风格UI重构 (2026-01-12)：
  - **设计方向**: Notion/Linear风格，深蓝色系，完全移除emoji
  - **配色替换**: AI助手从橙红渐变(#ff6b6b/#ee5a24)改为深蓝渐变(#2563EB/#1D4ED8)
  - **Emoji移除**: 共移除50+处emoji，覆盖所有UI页面
    - `app.py`: 移除popover、标题、快捷问题、消息中的emoji
    - `home.py`: 移除12处 (📊⚠️🔴🟢🤖✅🚀📤📋🔍⚙️📈)
    - `upload.py`: 移除12处，数字步骤改为纯文字 (1., 2., 3., 4.)
    - `analysis.py`: 移除12处 (🔍🔧🔴🟢🟡🔵📊🤖📥📋✅)
    - `actions.py`: 移除Tab和按钮中的emoji
    - `settings.py`: 移除19处 (⚙️📏📦🔑📊🔴🟢🔵💾✅🔄📜🗑️⚠️)
    - `ai_chatbox.py`: 移除🤖，改为纯文字"AI"
    - `chat.py`: 移除欢迎消息中的👋
    - `utils.py`: 错误toast图标从❌改为"error"字符串
  - **CSS优化**: 简化浮动AI按钮样式，移除脉冲动画
  - **设计系统**: `src/ui/styles.py` 提供统一CSS变量

- **[UI-008]** AI助手改为侧边栏弹出对话框 (2026-01-11)：
  - 用户反馈参考Amazon Seller Assistant的设计
  - 侧边栏底部显示醒目的"🤖 AI助手"按钮（橙红渐变色）
  - 点击按钮弹出 `st.popover` 对话框面板
  - 对话框顶部有渐变色标题栏
  - 4个快捷问题按钮（蓝色边框圆角按钮，2列布局）
  - 220px滚动消息区域，支持多轮对话
  - 底部输入框和清除对话按钮
- **[UI-007]** AI助手移至侧边栏 (2026-01-11)：
  - 用户反馈浮动按钮不够显眼，改为侧边栏 `st.expander` 展开式
  - 橙红色渐变标题栏，更加醒目
  - 点击"🤖 AI助手 - 点击展开"即可使用
  - 保留4个快捷问题按钮、对话历史、自定义输入功能
  - 展开时有淡红色背景，视觉区分明显
- **[UI-006]** AI助手改为浮动弹出对话框模式 (2026-01-11)：
  - 使用 `st.popover` 实现类似Amazon Seller Assistant的弹出式对话框
  - 底部浮动🤖按钮点击展开对话框
  - 4个快捷问题按钮（分析ACOS、优化建议、否词分析、投放建议）
  - 支持对话历史显示和自定义输入
  - 清除对话功能
  - CSS样式优化：渐变色主题、圆角按钮、阴影效果
- **[UI-005]** 修复侧边栏导航状态同步问题 (2026-01-11)：
  - `st.radio` 的 `key` 参数会覆盖 session_state，导致按钮导航后radio不同步
  - 改用 `index=current_index` 参数动态计算当前选中项
  - 删除冗余的 `key="nav_radio"` 参数

### Improved (代码质量)
- **[CODE-001]** AI对话上下文保持 (2026-01-11)：
  - ChatAssistant实例现在使用 `assistant_key` 持久化到 session_state
  - 保持多轮对话上下文，避免每条消息都重建实例
- **[CODE-002]** 敏感错误信息保护：
  - 异常信息不再直接暴露给用户
  - 使用通用错误提示 + `exc_info=True` 记录完整堆栈
- **[CODE-003]** 聊天历史记录限制：
  - 添加 MAX_CHAT_HISTORY=50 限制
  - 防止长时间会话内存无限增长
- **[CODE-004]** 数据库初始化错误处理：
  - 添加 try-except 包装
  - 初始化失败时显示用户友好错误并停止应用

### Fixed
- **[DB-001]** 修复产品信息保存功能 (2026-01-11)：
  - 根因：`update_product()` 方法在OneDrive同步目录下使用WAL模式导致数据库锁
  - 修复：移除WAL模式，保留30秒超时设置
  - 产品名称、品类、核心关键词、竞品ASIN现在可以正常保存
  - 关键词和竞品ASIN存储在`config` JSON字段中
- **[UI-001]** 修复 API Key 显示逻辑：使用 `is_api_configured` 属性检查，避免默认值误判为已配置
- **[UI-002]** 修复首页快速操作按钮无响应：
  - 使用 `nav_page` 统一导航状态
  - 按钮点击时删除 `nav_radio` session_state，确保 `st.radio` 使用新的 index
  - 端到端测试验证4个按钮（上传新数据、分析搜索词、查看操作清单、系统设置）全部正常工作
- **[UI-003]** 统一百分比格式为2位小数：ACOS、置信度等指标统一使用 `.2%` 格式
  - `ui/pages/home.py`, `ui/pages/analysis.py`, `ui/pages/actions.py`
  - `ai/analyzer.py`, `ai/chat.py`
  - `export/exporter.py`
- **[UI-004]** 修复操作历史页面查询错误 `no such column: product_id`：
  - `action_plans` 表没有 `product_id` 列，需通过 JOIN 关联获取
  - `actions.py`: 修改查询通过 `action_plans → analysis_results → search_terms → campaigns` 获取 product_id
  - `settings.py`: 修复产品删除时 action_plans 的级联删除查询

### Verified (E2E测试 2026-01-13) - 使用 Claude in Chrome 自动化验证

**规则管理CRUD完整验证 (2026-01-13)**:
- ✅ **编辑规则**: P10规则花费阈值从$10.0修改为$15.0，保存成功
- ✅ **禁用/启用规则**: P40规则切换状态，计数器正确显示5/6↔6/6
- ✅ **删除规则**: 创建测试规则后删除，确认对话框正常工作
- ✅ **添加规则**: 创建"高曝光低点击率"规则（曝光>=1000, CTR<=0.01）
- ✅ **规则变更影响分析结果**:
  - 单规则变更: 禁用P40后待AI确认从166→454
  - 多规则变更: 启用P40+修改P10后待AI确认变为742
  - 证实规则CRUD操作能正确影响分析引擎输出

**新增验证 (2026-01-13)**:
- ✅ **AI助手弹出框**: Claude in Chrome端到端验证
  - 4个快捷问题按钮完整显示且可点击
  - 输入框无蓝色焦点边框，样式干净
  - 发送按钮蓝色背景+白色箭头，与主题一致
  - Hover状态文字对比度清晰可读
- ✅ **批量文件上传**: 成功上传6个CSV文件，每个创建独立活动
- ✅ **清空数据功能**: 数据管理页面"清空所有搜索词数据"按钮正常工作
  - 验证前：461搜索词记录 / 316分析结果 / 6广告活动
  - 验证后：0搜索词记录 / 0分析结果 / 0广告活动
  - 产品配置保留正确

---

### Verified (E2E测试 2026-01-11) - 使用 Claude in Chrome 自动化验证

**测试环境**: Claude in Chrome 浏览器自动化 + Ralph Loop 迭代测试

#### 核心功能测试 (全部通过 ✅)
- ✅ **首页仪表盘**: 4个指标卡片（总花费、总订单、整体ACOS、搜索词数）正常显示
- ✅ **首页快速操作**: 4个按钮全部响应正常
  - 📤 上传新数据 → 文件上传页 ✓
  - 🔍 分析搜索词 → 搜索词分析页 ✓
  - 📋 查看操作清单 → 操作清单页 ✓
  - ⚙️ 系统设置 → 系统设置页 ✓
- ✅ **侧边栏导航**: 5个radio选项全部工作，状态同步正确
- ✅ **文件上传页**: 产品创建功能正常（测试: "测试产品", ASIN: "B0TEST123"）
- ✅ **搜索词分析页**: 筛选条件和运行分析按钮正常
- ✅ **操作清单页**: 完整验证通过
  - 3个标签（否词操作/手动投放/操作历史）切换正常
  - 产品名"旅行枕"正确显示（验证产品修改功能）
  - 否词数据表格显示正确（精确否定/短语否定分类）
  - 导出否词Excel功能正常，生成文件 `否词表_20260111_215449.xlsx` ✓
  - 复制到亚马逊后台文本框可用
  - 操作历史查询无报错（JOIN查询修复有效）
- ✅ **系统设置页**: 完整验证通过
  - 4个标签（规则配置/产品配置/API设置/数据管理）全部可切换
  - 规则配置数值调整正常
  - **产品信息保存功能修复验证**: 成功将"测试产品"改名为"旅行枕"，品类改为"旅行用品" ✓
  - API设置显示5个Gemini模型选项，切换立即生效 ✓
  - 数据管理统计信息显示正确
- ✅ **AI助手**: 浮动弹出对话框模式正常工作
  - 🤖按钮点击展开对话框 ✓
  - 快捷问题按钮（分析ACOS等）响应正常 ✓
  - 自定义输入功能正常 ✓
  - AI响应正确显示（ACOS分析、高花费词建议）✓
  - 清除对话功能可用 ✓
- ✅ **模型选择**: 下拉框显示5个Gemini模型选项，选择后立即生效

#### 已修复问题确认
- ✅ **[DB-001]** 产品信息保存: WAL模式移除后保存正常，无"database is locked"错误
- ✅ **[UI-001]** API Key显示: 未配置时正确显示"❌ 未配置"错误提示
- ✅ **[UI-002]** 快速操作按钮: 4个按钮全部正常导航
- ✅ **[UI-004]** 操作历史查询: JOIN查询正确，无`product_id`列错误

#### 发现的注意事项 (非阻塞)
- ⚠️ 快速操作按钮导航后，侧边栏radio视觉上不同步（功能正常，仅视觉问题）
- ⚠️ API Key未配置时，AI助手对话会触发多次重试（预期行为）
- ✅ ~~Streamlit Deprecation Warning: `use_container_width` 参数~~ - **已修复** [UI-012]

### Added
- **[FEATURE-002]** 批量文件上传功能 (2026-01-13)：
  - 支持同时选择多个CSV/Excel文件上传
  - 每个文件自动创建独立的广告活动（文件名作为活动名称）
  - 多文件预览使用Tabs布局显示
  - 批量导入进度条显示实时进度
  - 汇总统计（总搜索词数、花费、订单、点击）
  - 修改文件：`src/ui/pages/upload.py`

- **[FEATURE]** 动态模型选择功能：
  - 在系统设置页面添加模型下拉选择框
  - 支持 Gemini 2.5 Flash/Pro/Flash Lite 和 Gemini 3 Flash/Pro (预览版)
  - 无需重启应用，实时切换生效
  - `AVAILABLE_GEMINI_MODELS` 常量便于后续扩展

### Fixed (历史)
- 修复 start.bat 编码问题：中文字符导致Windows CMD解析失败，改为纯英文内容
- 修复 app.py 属性名错误：`settings.db_path` → `settings.database_path`
- 修复 app.py 方法名错误：`db.get_products()` → `db.get_all_products()`
- 修复 ModuleNotFoundError：start.bat 自动设置 PYTHONPATH
- **[BLOCKER]** 修复 chat.py AI助手数据库查询错误：`search_terms` 表无 `product_id` 列，需通过 `campaigns` 表 JOIN 关联
- **[BLOCKER]** 修复 db.py SQL注入漏洞：`get_table_count()` 方法添加白名单验证
- **[BLOCKER]** 修复 aggregator.py 除零产生Infinity问题：添加 `.replace([np.inf, -np.inf], 0)` 处理
- **[CRITICAL]** 修复 parser.py 百分比转换逻辑缺陷：正确处理带`%`符号的字符串（如"0.5%"→0.005）
- **[CRITICAL]** 增强 engine.py 规则引擎安全性：添加debug日志和空条件规则检查
- **[CRITICAL]** 修复敏感错误信息暴露：创建 `ui/utils.py` 的 `safe_error()` 函数，所有UI异常使用通用友好消息

### Improved
- **[MIN-002]** client.py 对话历史滑动窗口：添加 `max_history_turns` 参数（默认20轮），自动裁剪超限历史
- **[MIN-004]** parser.py 错误消息增强：CSV/Excel解析失败时提供详细上下文（编码尝试、文件名、建议操作）
- **[MIN-007]** analysis.py 批量操作进度反馈：AI分析时显示进度条和当前处理关键词
- **[MIN-011]** asin_rules.py 魔法字符串常量化：ASIN_PREFIX、阈值、洞察数量等抽取为模块常量
- **[NIT-004]** 使用 isort 规范化所有 src/ 目录下的 import 顺序
- **[DOC]** 修正 README.md 项目结构中的文件名错误（keyword_rules.py, asin_rules.py, manager.py, utils.py）

### Added
- **Sprint 5: UI与导出**
  - T29-T30: 报告导出器（ReportExporter类，否词表/手动词表/分析报告导出，Excel/CSV格式）
  - T31-T32: Streamlit主应用（app.py入口，侧边栏导航，Session State管理，AI助手集成）
  - T33: 首页仪表盘（关键指标卡片，待处理项统计，快速操作入口，规则统计图表）
  - T34: 文件上传页（产品选择/创建，CSV/Excel上传，数据预览，自动分析）
  - T35: 搜索词分析页（多维筛选，结果表格，批量AI分析，导出功能，详情面板）
  - T36: 操作清单页（否词操作/手动投放分类，复制列表，Excel/CSV导出，操作历史）
  - T37: 系统设置页（规则阈值配置，产品信息管理，API设置，数据管理，配置版本回滚）
  - Sprint 5单元测试（35个测试用例，100%通过）

- **Sprint 4: AI集成**
  - T24: Gemini API客户端（GeminiClient类，generate/chat方法，超时重试）
  - T25-T26: AI分析器（相关性判断、分歧解决、批量分析、竞品ASIN分析）
  - T27-T28: AI对话助手（多轮对话、意图检测、引导式选项、数据库集成）
  - Sprint 4单元测试（7个通过，10个需API Key跳过）

- **Sprint 3: 分析引擎**
  - T14: 规则引擎核心（RuleEngine类，优先级规则匹配，分析结果生成）
  - T15-T19: 关键词规则模块（高花费零转化、低转化高花费、高转化、低相关性、分歧处理）
  - T20: ASIN规则模块（ASIN格式验证、竞品分析、ASIN分类）
  - T21-T23: 配置版本管理（ConfigManager类，版本快照、回滚、版本对比）
  - Sprint 3单元测试（16个测试用例，100%通过）

- **Sprint 2: 数据处理**
  - T05-T07: 文件解析器（CSV/Excel，多编码支持，列名映射，数据清洗）
  - T09-T13: 数据聚合器（ASIN层/活动层/匹配类型层/关键词层，跨活动对比）
  - Sprint 2单元测试（13个测试用例，100%通过）

- **Sprint 1: 基础设施**
  - T01: 数据库Schema定义（7个表：products, campaigns, search_terms, rules, rule_versions, analysis_results, action_plans）
  - T02: 数据库操作模块（Database类，支持CRUD操作、事务、批量插入）
  - T03: 应用配置模块（Settings类，从.env加载配置）
  - T04: 日志系统（统一日志格式和级别控制）
  - Sprint 1单元测试（11个测试用例，100%通过）

## [0.1.0] - 2026-01-10

### Added
- 项目初始化
- PRD.md 产品需求文档
- Design.md 技术设计文档
- ADR架构决策文档（4个）
- Plan.md 开发计划
- Task.md 任务清单（41个任务）
