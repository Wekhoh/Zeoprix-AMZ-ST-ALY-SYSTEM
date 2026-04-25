# src/config/manager.md

**Purpose:** 配置管理（产品级配置、规则配置、设置持久化）。

**Last Updated:** 2026-04-25

## Public Surface

- `ConfigManager` — 配置管理器
- `ConfigManager.load()` — 加载配置（从 DB 或文件）
- `ConfigManager.save()` — 保存配置
- `ConfigManager.get()` — 获取配置值
- `ConfigManager.set()` — 设置配置值
- `ConfigManager.reset_to_defaults()` — 恢复默认配置

## Key Dependencies

1. **src.data.db** — 持久化存储
2. **src.config.product_defaults** — 默认配置模板

## Data Touched

**Reads/Writes:**
- `products` — product.config JSON 字段（产品级配置）
- `rule_versions` — 规则配置版本

## Used By

- **src.backend.workbench_payload** — 读取产品配置
- **src.backend.app** — 处理设置更新请求

## Architecture Notes

- **Hierarchical:** 全局默认 → 产品级配置 → 用户覆盖
- **Versioning:** 支持配置版本控制与回滚
- **Validation:** 配置更改前进行类型和值验证

## External Dependencies

- 无额外外部依赖
