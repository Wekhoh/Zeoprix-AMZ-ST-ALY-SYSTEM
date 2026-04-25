# src/analysis/asin_analyzer.md

**Purpose:** ASIN 分析流程（综合搜索词、规则、AI 分析）。

**Last Updated:** 2026-04-25

## Public Surface

- `AsinAnalyzer` — ASIN 分析器
- `AsinAnalyzer.analyze()` — 执行完整分析流程（加载搜索词 → 执行规则 → AI 分析 → 保存结果）
- `AsinAnalyzer.generate_report()` — 生成分析报告
- `analyze_product()` — 便捷函数：分析单个产品

## Key Dependencies

1. **src.data.db** — 读写产品、搜索词、执行批次
2. **src.rules.engine** — 执行规则评估
3. **src.ai.analyzer** — AI 文本分析

## Data Touched

**Reads:**
- `products` — 产品信息
- `search_terms` — 搜索词数据
- `rules` — 规则配置

**Writes:**
- `execution_batches` — 记录分析执行状态
- `execution_logs` — 记录执行日志

## Used By

- **src.backend.workbench_payload** — 触发分析、查询结果
- **scripts/** — 批量分析脚本

## Architecture Notes

- **Pipeline:** load_search_terms → apply_rules → ai_analysis → store_results
- **Async Support:** 支持异步批量分析
- **Progress Tracking:** 通过 execution_batch 记录进度

## External Dependencies

- 无额外外部依赖
