# src/export/exporter.md

**Purpose:** 数据导出模块（Excel、JSON、备份等）。

**Last Updated:** 2026-04-25

## Public Surface

- `Exporter` — 导出器主类
- `Exporter.export_to_excel()` — 导出搜索词到 Excel 工作簿
- `Exporter.export_to_json()` — 导出为 JSON
- `Exporter.create_full_backup()` — 创建完整数据库备份（含产品、搜索词、规则）
- `Exporter.restore_from_backup()` — 从备份恢复数据
- `export_product()` — 便捷函数：导出单个产品

## Key Dependencies

1. **src.data.db** — 读取产品、搜索词数据
2. **openpyxl** — Excel 文件操作
3. **pandas** — 数据处理

## Data Touched

**Reads:**
- `products` — 产品配置
- `search_terms` — 搜索词数据
- `rules` — 规则配置
- `campaigns` — 广告活动

**Writes (backup only):**
- 创建 .backup 或 .zip 文件

## Used By

- **src.backend.workbench_payload** — `/export` 路由处理
- **src.backend.app** — `POST /products/{product_id}/export` 路由

## Architecture Notes

- **Format Support:** Excel (.xlsx)、JSON、SQLite 备份
- **Streaming:** Excel 导出支持大数据集流式写入
- **Backup Structure:** JSON 格式，包含所有表数据 + 元数据

## External Dependencies

- **openpyxl** (~3.x) — Excel 操作
- **pandas** (~2.x) — 数据处理
