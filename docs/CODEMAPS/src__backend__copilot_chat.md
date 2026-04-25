# src/backend/copilot_chat.md

**Purpose:** Copilot 聊天处理逻辑（请求解析、回复生成、流式响应）。

**Last Updated:** 2026-04-25

## Public Surface

- `process_frontend_copilot_turn()` — 处理单次聊天轮次（同步）
- `process_frontend_copilot_turn_stream()` — 处理单次聊天轮次（流式）
- `build_copilot_context()` — 从页面上下文构造 AI prompt
- `CopilotTurn` — 聊天轮次数据类（user_message、ai_response、metadata）

## Key Dependencies

1. **src.ai.copilot** — Copilot 聊天逻辑
2. **src.backend.workbench_payload** — 获取页面上下文
3. **src.data.db** — 读取产品、搜索词上下文

## Data Touched

**Reads:**
- `products` — 产品上下文
- `search_terms` — 搜索词上下文（page_context）
- `rules` — 规则上下文

**Writes:** None（仅读取）

## Used By

- **src.backend.app** — `/copilot/chat` 和 `/copilot/chat-sync` 路由

## Architecture Notes

- **Context-Aware:** 根据 page_key（analysis、settings 等）自适应 prompt
- **Streaming:** 流式响应 SSE（Server-Sent Events）
- **History Management:** 支持多轮对话历史维持连贯性
- **Error Recovery:** 网络中断时支持重新发送

## External Dependencies

- 无额外外部依赖
