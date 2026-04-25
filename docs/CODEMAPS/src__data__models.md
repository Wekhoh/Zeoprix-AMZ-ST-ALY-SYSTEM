# src/data/models.md

**Purpose:** SQLite 数据库架构定义（表、索引、默认规则）。

**Last Updated:** 2026-04-25

## Public Surface

- `ALL_SCHEMAS` — 字典，定义所有 SQLite 表的 CREATE TABLE 语句（products、search_terms、rules、campaigns 等）
- `DEFAULT_RULES` — 默认规则列表（asin_rules、keyword_rules）
- `INDEXES` — 索引定义字典（product_id、campaign_id、term 等常用索引）

## Key Dependencies

1. **src.rules.asin_rules** — ASIN 规则类型定义
2. **src.rules.keyword_rules** — 关键词规则类型定义

## Data Touched

**Schema Definition (no runtime writes):**
- 定义表结构：products、search_terms、rules、rule_versions、campaigns、strategy_profiles、execution_batches、execution_logs 等

## Used By

- **src.data.db** — `Database.init_schema()` 遍历 ALL_SCHEMAS 创建表
- **Database 初始化时** — ALL_SCHEMAS 用于 CREATE TABLE IF NOT EXISTS

## Architecture Notes

- **Schema Storage:** 纯数据定义，无 SQL 执行逻辑
- **JSON Fields:** product.config、strategy_profiles 等使用 TEXT 存储 JSON
- **Indexes:** 定义在 INDEXES 中，供 Database._migrate_schema() 创建

## External Dependencies

- 无外部依赖（纯数据定义）
