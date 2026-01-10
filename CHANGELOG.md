# 变更日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [Unreleased]

### Added
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
