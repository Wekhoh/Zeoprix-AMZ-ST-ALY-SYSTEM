# src/config/logger.md

**Purpose:** 日志系统配置（格式化、日志级别、文件输出）。

**Last Updated:** 2026-04-25

## Public Surface

- `get_logger()` — 获取或创建模块级 logger
- `configure_logging()` — 初始化全局日志配置
- `LogConfig` — 日志配置 dataclass（格式、级别、处理器）

## Key Dependencies

1. **src.config.settings** — 读取 log_level 配置
2. **logging** — Python 标准库

## Data Touched

**None (logging only)**

## Used By

- **src.backend.app** — 启动时调用 configure_logging()
- **src.data.db** — 记录慢查询日志
- **所有模块** — 通过 `get_logger(__name__)` 获取 logger

## Architecture Notes

- **Format:** 包含时间戳、日志级别、模块名、消息
- **Handlers:** 支持控制台输出 + 文件输出（可选）
- **Performance:** 默认 INFO 级别，生产环境可降低冗余

## External Dependencies

- **logging** — Python 标准库
