# src/data/parser.md

**Purpose:** 数据解析器（Excel 导入、CSV 解析等）。

**Last Updated:** 2026-04-25

## Public Surface

- `ExcelParser` — Excel 工作簿解析器
- `ExcelParser.parse_search_terms()` — 解析搜索词工作表
- `ExcelParser.parse_campaigns()` — 解析广告活动工作表
- `CsvParser` — CSV 文件解析器
- `parse_upload_file()` — 便捷函数：自动判断文件类型并解析

## Key Dependencies

1. **openpyxl** — Excel 文件操作
2. **pandas** — CSV 和数据处理
3. **src.rules.asin_rules** — ASIN 验证

## Data Touched

**None (parsing only, no writes)**

## Used By

- **src.backend.workbench_payload** — `upload_files_for_frontend()` 处理文件上传
- **src.backend.app** — `POST /products/{product_id}/upload` 路由

## Architecture Notes

- **Format Support:** Excel (.xlsx)、CSV (.csv)
- **Validation:** 解析时进行数据验证（ASIN 格式、数据类型）
- **Error Reporting:** 详细错误信息指示问题行列
- **Streaming:** 支持大文件流式处理（避免全量加载到内存）

## External Dependencies

- **openpyxl** (~3.x) — Excel 操作
- **pandas** (~2.x) — CSV 处理
