# src/ai/chat.md

**Purpose:** AI 聊天管理（对话历史、会话状态、多轮对话）。

**Last Updated:** 2026-04-25

## Public Surface

- `ChatSession` — 聊天会话管理
- `ChatSession.add_message()` — 添加消息到历史
- `ChatSession.get_history()` — 获取对话历史
- `ChatSession.clear()` — 清空历史
- `Message` — 单条消息数据类（role、content、timestamp）
- `create_session()` — 创建新会话

## Key Dependencies

1. **src.ai.client** — Claude API 调用
2. 无其他内部依赖

## Data Touched

**None (in-memory session only)**

## Used By

- **src.backend.copilot_chat** — 管理 Copilot 对话历史
- **src.ai.copilot** — 传递历史消息给 AI

## Architecture Notes

- **In-Memory:** 会话存储在内存中（生产环境可扩展至 Redis）
- **TTL:** 支持会话超时自动清理
- **Message Formatting:** 统一格式化消息以适应 Claude API

## External Dependencies

- 无额外外部依赖
