# src/ai/client.md

**Purpose:** AI 客户端（Claude API 调用、流式支持）。

**Last Updated:** 2026-04-25

## Public Surface

- `ClaudeClient` — Claude API 客户端（Anthropic SDK 包装）
- `ClaudeClient.create_message()` — 创建单条 message（同步）
- `ClaudeClient.create_message_stream()` — 流式 message（async）
- `get_claude_client()` — 获取或创建全局 ClaudeClient 实例

## Key Dependencies

1. **anthropic** — Anthropic Claude SDK
2. **src.config.settings** — API key、model name 配置

## Data Touched

**None (API client only)**

## Used By

- **src.ai.analyzer** — 文本分析
- **src.ai.chat** — 聊天接口
- **src.ai.copilot** — Copilot 功能

## Architecture Notes

- **API Key:** 从 `AMZ_ANTHROPIC_API_KEY` 或 settings 读取
- **Streaming:** 支持 async 流式响应
- **Model:** 默认 "claude-3-sonnet-20240229"（可配置）

## External Dependencies

- **anthropic** — Claude API SDK
