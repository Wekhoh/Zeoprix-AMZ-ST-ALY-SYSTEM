# src/backend/workbench_payload.md

**Purpose:** 工作台各页面的负载构造（分析页、上传页、设置页、审查页等）。

**Last Updated:** 2026-04-25

## Public Surface

- `build_workbench_payload()` — 构造完整工作台负载
- `build_analysis_page_payload()` — 分析页面负载（搜索词、规则评估结果）
- `build_upload_page_payload()` — 上传页面负载（上传历史、当前状态）
- `build_settings_page_payload()` — 设置页面负载（产品配置、规则版本）
- `build_review_page_payload()` — 审查页面负载（待审查项）
- `build_actions_page_payload()` — 操作页面负载（可执行动作列表）
- `update_settings_config_for_frontend()` — 处理前端设置更新请求
- `run_analysis_for_frontend()` — 处理前端分析请求
- `upload_files_for_frontend()` — 处理文件上传
- `export_full_backup_for_frontend()` — 处理导出请求
- `restore_full_backup_for_frontend()` — 处理恢复请求
- `clear_runtime_for_frontend()` — 清空运行时数据
- `submit_review_decision_for_frontend()` — 处理审查决策
- `create_execution_batch_for_frontend()` — 创建执行批次
- `update_execution_batch_for_frontend()` — 更新执行批次
- `preview_settings_rule_version_for_frontend()` — 预览规则版本
- `restore_settings_rule_version_for_frontend()` — 恢复规则版本

## Key Dependencies

1. **src.data.db** — 读写产品、搜索词、规则、执行批次
2. **src.rules.engine** — 执行规则评估
3. **src.ai.analyzer** — AI 分析
4. **src.export.exporter** — 导出/导入功能

## Data Touched

**Reads:**
- `products` — 产品信息
- `search_terms` — 搜索词数据
- `rules` — 规则配置
- `execution_batches` — 执行批次历史

**Writes:**
- `products` — 更新配置
- `rules` — 更新规则
- `execution_batches` — 创建/更新批次
- `execution_logs` — 记录执行日志

## Used By

- **src.backend.app** — 所有 `/workbench`、`/analysis`、`/settings` 路由调用此模块

## Architecture Notes

- **Lazy Loading:** 每个页面负载按需加载数据（避免过度查询）
- **Pagination:** 搜索词列表支持分页
- **Context Aggregation:** 将产品配置、规则、搜索词数据聚合成前端可用的负载
- **Error Handling:** 所有操作返回结构化错误响应

## External Dependencies

- 无额外外部依赖
