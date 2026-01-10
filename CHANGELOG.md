# 变更日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [Unreleased]

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
