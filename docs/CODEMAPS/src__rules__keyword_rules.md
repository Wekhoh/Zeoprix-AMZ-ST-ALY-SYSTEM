# src/rules/keyword_rules.md

**Purpose:** 关键词规则类型定义（关键词匹配、分类等）。

**Last Updated:** 2026-04-25

## Public Surface

- `KeywordRule` — 关键词规则类型
- `KeywordRuleCondition` — 关键词规则条件（如：contains、exact_match、regex）
- `KeywordRuleAction` — 关键词规则动作（如：tag、adjust_bid）
- `match_keyword()` — 关键词匹配函数（支持 contains、exact、regex）

## Key Dependencies

- 无内部依赖

## Data Touched

**None (rule definition only)**

## Used By

- **src.rules.engine** — 评估时检查关键词规则类型
- **src.backend.workbench_payload** — 显示关键词规则

## Architecture Notes

- **Match Types:** contains（子字符串）、exact（完全匹配）、regex（正则表达式）
- **Case Sensitivity:** 可配置
- **Performance:** 预编译正则以避免重复编译

## External Dependencies

- 无外部依赖
