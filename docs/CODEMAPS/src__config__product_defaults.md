# src/config/product_defaults.md

**Purpose:** 产品默认配置模板（关键词、竞品、规则预设等）。

**Last Updated:** 2026-04-25

## Public Surface

- `build_seeded_product_config()` — 生成新产品的默认配置
- `DEFAULT_CORE_KEYWORDS` — 默认核心关键词列表
- `DEFAULT_RELATED_KEYWORDS` — 默认相关关键词列表
- `DEFAULT_COMPETITOR_ASINS` — 默认竞品 ASIN 列表
- `DEFAULT_OWN_VARIANTS` — 默认自有变体 ASIN 列表
- `DEFAULT_RULES` — 默认规则预设

## Key Dependencies

- 无内部依赖

## Data Touched

**None (configuration templates only)**

## Used By

- **src.data.db** — `Database.create_product()` 初始化新产品配置
- **src.config.manager** — 恢复默认配置时使用

## Architecture Notes

- **Seeding:** 创建新产品时自动应用默认配置
- **Customizable:** 可通过环境变量覆盖默认值
- **Extensible:** 易于添加新的默认配置项

## External Dependencies

- 无外部依赖
