# src/data/aggregator.md

**Purpose:** 数据聚合模块（搜索词统计、指标计算、报告生成）。

**Last Updated:** 2026-04-25

## Public Surface

- `Aggregator` — 数据聚合器
- `Aggregator.aggregate_search_terms()` — 按维度聚合搜索词数据
- `Aggregator.compute_metrics()` — 计算关键指标（CTR、CPC、转化率等）
- `Aggregator.generate_report()` — 生成聚合报告
- `MetricsResult` — 聚合指标结果数据类

## Key Dependencies

1. **src.data.db** — 读取搜索词数据
2. **pandas** — 数据聚合与计算

## Data Touched

**Reads:**
- `search_terms` — 搜索词数据（metrics）
- `products` — 产品维度

## Used By

- **src.backend.workbench_payload** — 生成分析页面统计
- **src.backend.insights** — 计算洞察数据

## Architecture Notes

- **GroupBy:** 支持按 campaign、term_type、status 等维度聚合
- **Windowing:** 支持时间窗口聚合（日、周、月）
- **Performance:** 使用 pandas 向量化操作，避免循环

## External Dependencies

- **pandas** (~2.x) — 数据聚合
