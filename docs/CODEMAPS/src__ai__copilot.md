# src/ai/copilot.md

**Purpose:** Copilot 聊天逻辑（多轮对话、工作台上下文感知）。

**Last Updated:** 2026-04-25

## Public Surface

- `CopilotContext` — 上下文对象（page_key、product_id、page_context）
- `CopilotSession` — 多轮对话会话
- `create_copilot_message()` — 生成单条 Copilot 响应
- `stream_copilot_message()` — 流式生成 Copilot 响应
- `format_page_context()` — 将页面上下文格式化为 prompt

## Key Dependencies

1. **src.ai.client** — Claude API 调用
2. **src.backend.workbench_payload** — 获取页面上下文

## Data Touched

**Reads:**
- `products` — 产品信息
- `search_terms` — 搜索词上下文
- `rules` — 规则上下文

## Used By

- **src.backend.copilot_chat** — HTTP 路由处理
- **src.backend.app** — `/copilot/chat` 路由

## Architecture Notes

- **Context Awareness:** 根据 page_key（analysis、settings 等）自适应 prompt
- **Multi-turn:** 支持历史消息，维持对话连贯性
- **Streaming:** async 流式响应，实时推送给前端

## External Dependencies

- **anthropic** — Claude API
