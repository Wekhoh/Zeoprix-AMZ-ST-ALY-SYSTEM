# src/config/settings.md

**Purpose:** 应用全局设置（API keys、数据库 URL、日志级别等）。

**Last Updated:** 2026-04-25

## Public Surface

- `Settings` — Pydantic BaseSettings 类
- `get_settings()` — 获取全局 Settings 实例（单例）
- 字段：
  - `anthropic_api_key` — Claude API key（环境变量 AMZ_ANTHROPIC_API_KEY）
  - `backend_database_url` — 后端数据库 URL
  - `data_database_path` — SQLite 数据库路径
  - `log_level` — 日志级别（DEBUG/INFO/WARNING/ERROR）
  - `debug_mode` — 调试模式开关

## Key Dependencies

- **pydantic-settings** — 配置管理

## Data Touched

**None (configuration only)**

## Used By

- **src.backend.app** — 读取 log_level、debug_mode 等
- **src.ai.client** — 读取 anthropic_api_key
- **src.config.logger** — 读取 log_level
- **任何需要配置的模块**

## Architecture Notes

- **Environment Variables:** 所有配置项均可通过环境变量覆盖
- **Validation:** Pydantic 自动验证类型和值范围
- **Singleton:** `get_settings()` 缓存全局实例，避免重复初始化

## External Dependencies

- **pydantic-settings** — 配置管理
