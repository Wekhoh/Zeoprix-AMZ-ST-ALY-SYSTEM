# src/rules/asin_rules.md

**Purpose:** ASIN 规则类型定义（ASIN 验证、ASIN 相关规则）。

**Last Updated:** 2026-04-25

## Public Surface

- `is_valid_asin()` — 验证 ASIN 格式（10 字符字母数字）
- `AsincRule` — ASIN 规则类型
- `AsincRuleCondition` — ASIN 规则条件（如：own_asin、competitor_asin）
- `AsincRuleAction` — ASIN 规则动作（如：flag、exclude）

## Key Dependencies

- 无内部依赖

## Data Touched

**None (rule definition only)**

## Used By

- **src.rules.engine** — 评估时检查 ASIN 规则类型
- **src.data.db** — 创建规则时验证 ASIN 格式

## Architecture Notes

- **ASIN Format:** 10 字符，允许 A-Z 0-9
- **Rules:** 支持 own_asin、competitor_asin、category 等条件

## External Dependencies

- 无外部依赖
