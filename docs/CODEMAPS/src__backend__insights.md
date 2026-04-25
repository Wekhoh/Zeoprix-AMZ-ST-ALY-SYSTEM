# src/backend/insights.md

**Purpose:** 每日洞察生成和检索（AI 驱动的产品分析摘要）。

**Last Updated:** 2026-04-25

## Public Surface

- `generate_and_store_insight()` — 生成今日洞察并存储
- `get_today_insight()` — 检索今日洞察
- `get_insight_history()` — 获取洞察历史
- `InsightData` — 洞察数据类（title、description、metrics、timestamp）

## Key Dependencies

1. **src.ai.analyzer** — 生成洞察文本
2. **src.data.db** — 存储洞察
3. **src.backend.workbench_payload** — 获取产品上下文

## Data Touched

**Reads:**
- `products` — 产品信息
- `search_terms` — 搜索词统计

**Writes:**
- `insights` 表（如存在）— 存储生成的洞察

## Used By

- **src.backend.app** — `GET /insights/today` 路由

## Architecture Notes

- **Caching:** 每日首次请求生成并缓存，后续请求直接返回
- **AI-Powered:** 使用 Claude 生成自然语言摘要
- **Scheduling:** 可集成 APScheduler 实现定时生成

## External Dependencies

- 无额外外部依赖
