# 变更日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [Unreleased]

### Fixed
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

### Verified (E2E测试 2026-01-11)
- ✅ 首页仪表盘：4个指标卡片（总花费、总订单、整体ACOS、搜索词数）正常显示
- ✅ 首页快速操作：4个按钮全部响应正常，导航跳转正确
- ✅ 侧边栏导航：5个radio选项（首页、文件上传、搜索词分析、操作清单、系统设置）全部工作
- ✅ 文件上传页：产品创建功能正常（测试创建"测试产品" ASIN "B0TEST123"）
- ✅ 搜索词分析页：筛选条件（动作类型、词类型、AI确认状态、搜索关键词）和运行分析按钮正常
- ✅ 操作清单页：3个标签（否词操作、手动投放、操作历史）切换正常，无报错
- ✅ 系统设置页：4个标签全部可切换，规则配置、API设置、模型选择下拉框正常
- ✅ AI助手：展开/收起正常，未配置API时显示正确错误提示
- ✅ 模型选择：下拉框显示5个Gemini模型选项，选择后立即生效

### Added
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
