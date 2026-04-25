# src/rules/engine.md

**Purpose:** 规则引擎（评估搜索词是否匹配规则条件、执行动作）。

**Last Updated:** 2026-04-25

## Public Surface

- `RuleEngine` — 规则引擎主类
- `RuleEngine.load_rules()` — 从数据库加载规则
- `RuleEngine.evaluate()` — 评估单条搜索词是否匹配规则
- `RuleEngine.execute()` — 批量评估搜索词
- `RuleResult` — 规则评估结果（matched_rules、actions）
- `execute_rules()` — 便捷函数：加载规则 + 批量评估

## Key Dependencies

1. **src.data.db** — 读取规则配置
2. **src.rules.asin_rules** — ASIN 规则类型
3. **src.rules.keyword_rules** — 关键词规则类型

## Data Touched

**Reads:**
- `rules` — 规则配置（enabled、conditions、actions）
- `products` — 产品配置上下文

## Used By

- **src.backend.workbench_payload** — 在分析页面执行规则评估
- **src.analysis.asin_analyzer** — 执行规则流程

## Architecture Notes

- **Lazy Loading:** 规则按需加载，缓存在内存
- **Condition Evaluation:** 支持多条件 AND/OR 逻辑
- **Action Execution:** 根据规则类型执行对应动作（标记、分类等）

## External Dependencies

- 无外部依赖
