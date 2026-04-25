# src/analysis/truth_replay.md

**Purpose:** 真值重放模块（验证规则、AI 分析的准确性）。

**Last Updated:** 2026-04-25

## Public Surface

- `TruthReplayer` — 真值重放器（用于测试和验证）
- `TruthReplayer.load_truth_data()` — 加载标注真值数据
- `TruthReplayer.replay()` — 重放分析流程，对比预期与实际结果
- `TruthReplayer.compute_accuracy()` — 计算准确率、精准度、召回率
- `AccuracyMetrics` — 准确性指标数据类

## Key Dependencies

1. **src.data.db** — 读取搜索词、规则配置
2. **src.rules.engine** — 执行规则
3. **src.ai.analyzer** — 执行 AI 分析

## Data Touched

**Reads:**
- `products` — 产品信息
- `search_terms` — 搜索词与标注真值
- `rules` — 规则配置

## Used By

- **scripts/evaluate_product.py** — 模型评估脚本
- **测试套件** — 规则和 AI 模型质量检查

## Architecture Notes

- **Baseline Comparison:** 将实际结果与标注真值对比
- **Metrics Calculation:** 计算 accuracy、precision、recall、F1
- **Report Generation:** 生成详细对比报告，指出差异

## External Dependencies

- 无额外外部依赖
