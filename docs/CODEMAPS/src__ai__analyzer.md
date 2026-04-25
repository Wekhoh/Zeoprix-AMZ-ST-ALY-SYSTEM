# src/ai/analyzer.md

**Purpose:** AI 文本分析模块（搜索词相关性、竞品识别等）。

**Last Updated:** 2026-04-25

## Public Surface

- `SearchTermAnalyzer` — 搜索词分析器
- `SearchTermAnalyzer.analyze_relevance()` — 分析搜索词与产品的相关性
- `SearchTermAnalyzer.identify_competitors()` — 识别竞品
- `analyze_search_terms()` — 批量分析搜索词
- `get_analyzer()` — 获取全局 analyzer 实例

## Key Dependencies

1. **src.ai.client** — Claude API 客户端
2. **src.data.db** — 查询产品信息、搜索词

## Data Touched

**Reads:**
- `products` — 产品 ASIN、name、config
- `search_terms` — 搜索词数据

## Used By

- **src.backend.workbench_payload** — 在分析页面生成相关性评分
- **src.analysis.asin_analyzer** — ASIN 分析流程

## Architecture Notes

- **Prompt Engineering:** 使用预定义 prompts 分析搜索词
- **Caching:** 可选缓存分析结果避免重复调用 AI

## External Dependencies

- **anthropic** — Claude API
