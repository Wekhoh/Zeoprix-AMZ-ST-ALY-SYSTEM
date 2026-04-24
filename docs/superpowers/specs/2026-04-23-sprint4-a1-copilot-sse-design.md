# Sprint 4 · A1 — Copilot SSE 流式响应 · Design Spec

**Date:** 2026-04-23
**Owner:** jackl
**Status:** Draft (awaiting user review)
**Parent:** 子项目 A — Sprint 4 AI 深度集成

---

## 1. Context

Zeoprix AMZ-ST 的 Copilot 当前使用 **一次性同步响应**：前端 `POST /frontend/copilot/chat` → 后端 `process_frontend_copilot_turn` 同步调 `ChatAssistant.process_message` → Gemini `send_message` 一次返回完整文本 → 后端包 envelope → 前端整体渲染。

体感问题：Gemini 3 Flash Preview 典型首字延迟 ≈3-4s，用户按 Enter 后对话面板长时间"空转"，然后文本一次性蹦出，缺少"AI 正在思考/写作"的反馈。

Sprint 4 原 plan 的 A1 目标是把首字延迟降到 **≤ 0.8s**（Gemini TTFT ≈ 0.5-0.8s），并让剩余文本以打字机形式流出。

## 2. Goals

- 新增 `POST /frontend/copilot/chat/stream` SSE 端点，返回 typed SSE frames
- 前端 `CopilotPanel.sendMessage` 改走流式端点，实时追加文本到 assistant 气泡
- **首字延迟 ≤ 0.8s**（Chrome Performance tab 实测）
- 切页 / 关窗时 AbortController 主动中止流，释放后端连接与 token 额度
- 保留老 `/chat` 端点作为 fallback + 环境变量开关 `NEXT_PUBLIC_COPILOT_STREAM_ENABLED`

## 3. Non-Goals

- ❌ **不做** A2 ASIN / 关键词 hyperlink（单独 mini-sprint）
- ❌ **不做** A3 每日 AI 洞察（单独 mini-sprint）
- ❌ **不做** Copilot 多轮会话持久化（对话历史仍由前端 sessionStorage 管理，后端无状态）
- ❌ **不做** 前端 vitest / E2E 测试（放子项目 D 统一做）
- ❌ **不做** `src/app.py` Streamlit legacy 清理（放子项目 B）

## 4. Architecture

```
Frontend (CopilotPanel)
  └─ streamCopilotChat(payload, {onDelta, onEnvelope, onError, signal})
       │  POST /frontend/copilot/chat/stream
       ▼
Backend (FastAPI)
  └─ copilot_chat_stream() → StreamingResponse(media_type="text/event-stream")
       └─ process_frontend_copilot_turn_stream(**payload)
            │  async generator yielding SSE-formatted bytes
            ▼
         ChatAssistant.process_message_stream(prompt)
            │  async generator yielding (frame_type, payload) tuples
            ▼
         GeminiClient.generate_stream(prompt, system_instruction, ...)
            │  async generator wrapping google-genai
            ▼
         client.models.generate_content_stream(...)
```

**Frame 序列**（service-side envelope）：
```
event 1:   data: {"type":"context","contextLabel":"当前页面 / 最近分析"}
event 2…N: data: {"type":"delta","text":"..."}
event N+1: data: {"type":"envelope","followUpPrompts":[...],"recommendedNextActions":[...],"actionLinks":[...],"warning":null}
event N+2: data: {"type":"done"}
```

错误路径：任何点失败 → `data: {"type":"error","message":"..."}` → 紧跟 `data: {"type":"done"}`

## 5. Components

### 5.1 Backend

**File:** `src/ai/client.py` — 新增方法

```python
async def generate_stream(
    self,
    prompt: str,
    *,
    system_instruction: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = 2048,
) -> AsyncIterator[str]:
    """
    Stream text chunks from Gemini.

    Wraps google-genai client.models.generate_content_stream(...).
    Yields string chunks incrementally. Relies on SDK built-in retry (max 3).
    """
```

**File:** `src/ai/chat.py` — 新增 `ChatAssistant` 方法

```python
FrameType = Literal["context", "delta", "envelope", "error"]

async def process_message_stream(
    self,
    message: str,
    *,
    context_label: str | None = None,
) -> AsyncIterator[tuple[FrameType, Any]]:
    """
    Stream Copilot turn as typed frames.

    Flow:
    1. yield ("context", context_label)
    2. build enhanced prompt (data context injection — existing logic reused)
    3. accumulate full text while yielding ("delta", chunk) per Gemini chunk
    4. post-process (intent, guided options) → yield ("envelope", {...})
    5. on exception at any step → yield ("error", {"message": str(exc)})
    """
```

**File:** `src/backend/copilot_chat.py` — 新增 async generator

```python
async def process_frontend_copilot_turn_stream(
    *,
    product_id: int | None,
    page_key: str,
    page_title: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
    page_context: dict[str, Any] | None = None,
) -> AsyncIterator[bytes]:
    """
    Produce SSE frame bytes: 'data: {json}\\n\\n'.

    Wraps ChatAssistant.process_message_stream. Applies 45s asyncio.wait_for cap.
    On asyncio.CancelledError (client disconnect) logs and returns cleanly.
    """
```

**File:** `src/backend/app.py` — 新增路由

```python
@app.post("/frontend/copilot/chat/stream", tags=["copilot"])
async def copilot_chat_stream(payload: CopilotChatRequest) -> StreamingResponse:
    return StreamingResponse(
        process_frontend_copilot_turn_stream(**payload.model_dump()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

（复用已有的 `CopilotChatRequest` Pydantic model；若不存在则在此 sprint 一并新增。）

### 5.2 Frontend

**New file:** `frontend/src/lib/copilot-stream.ts`

```typescript
export type CopilotFrame =
  | { type: "context"; contextLabel: string | null }
  | { type: "delta"; text: string }
  | { type: "envelope"; followUpPrompts: string[]; recommendedNextActions: string[]; actionLinks: ActionLink[]; warning: string | null }
  | { type: "error"; message: string }
  | { type: "done" };

export async function streamCopilotChat(
  payload: CopilotChatPayload,
  handlers: {
    onContext?: (label: string | null) => void;
    onDelta: (text: string) => void;
    onEnvelope: (env: EnvelopeFrame) => void;
    onError: (message: string) => void;
    signal?: AbortSignal;
  },
): Promise<void>;
```

实现细节：
- `fetch(url, { method: "POST", body, signal })` → `response.body.getReader()` + `TextDecoder`
- 按 `\n\n` 切分 event，再取 `data:` 行解析 JSON
- 每个 frame dispatch 到对应 handler

**Modified file:** `frontend/src/components/copilot-panel.tsx`

- `sendMessage` 从 `fetch(/chat).json()` 改为调 `streamCopilotChat(..., {onDelta, onEnvelope, onError, signal})`
- 新增 `useRef<AbortController | null>` + `useEffect` cleanup 触发 `abort()`
- 新增 `streamEnabled` const 读 `process.env.NEXT_PUBLIC_COPILOT_STREAM_ENABLED !== "0"`；false 时走老 `/chat` path（保留目前代码作 else 分支）

## 6. Data Flow

```
User types "为什么 ACOS 高？" + Enter
  ↓
sendMessage(trimmed)
  ├─ setMessages(prev => [...prev, {role:"user", content}, {role:"assistant", content:""}])
  ├─ setPending(true)
  ├─ abortRef.current = new AbortController()
  ├─ streamEnabled ? streamCopilotChat(...) : oldFetch(...)
  │
  ├─ onContext(label)   → setContextLabel(label)
  ├─ onDelta(text)      → setMessages(prev => patch last assistant content += text)
  │                        (React 批更新，UI 每 16ms 重绘，视觉打字机)
  ├─ onEnvelope(env)    → setPrompts / setRecommendedActions / setActionLinks / setWarning
  ├─ onError(msg)       → setWarning(msg) + fetch old /chat once (silent fallback)
  └─ finally            → setPending(false), abortRef.current = null

Component unmount OR clearConversation()
  ↓
abortRef.current?.abort() → fetch promise rejects with AbortError
  ↓
Backend async generator sees asyncio.CancelledError → logger.info + return
```

## 7. Error Handling

| 场景 | 行为 |
|---|---|
| Gemini API 瞬时失败 | google-genai SDK 内部 retry 最多 3 次（已有） |
| Gemini 最终失败 | `process_message_stream` catch Exception → yield `("error", {...})`；前端 onError 回退到老 `/chat` 重试一次 |
| 后端 handler 其他异常（DB / context build） | 同上（generator 捕获并 yield error frame） |
| 客户端断连（切页 / 关窗） | `StreamingResponse` 通过 `asyncio.CancelledError` 通知；generator `try/finally` 捕获 + logger.info("client disconnect") + return |
| 流总时长 > 45s | `asyncio.wait_for(..., timeout=45)` 包裹单次 Gemini 调用；超时 → yield `("error", {"message":"响应超时"})` |
| 前端 AbortController 触发 | `reader.read()` 抛 `AbortError`；`streamCopilotChat` catch 并 return（不触发 onError，主动取消） |

## 8. Config / Rollout

**Env vars（`.env.production`）：**

```bash
NEXT_PUBLIC_COPILOT_STREAM_ENABLED=1   # 默认 on；设 0 走老 /chat
```

**回滚路径：**
- 任何流式问题 → `NEXT_PUBLIC_COPILOT_STREAM_ENABLED=0` → 重建 → 自动走老 `/chat`（老 endpoint 不删）
- 彻底回滚 → git revert commit，代码回到 Sprint 3 状态

## 9. Observability

**Backend 日志（`src/backend/copilot_chat.py`）：**
```python
logger.info(f"SSE started product={product_id} page={page_key} msg_len={len(user_message)}")
logger.info(f"SSE completed product={product_id} page={page_key} chunks={n} chars={total_chars} duration_ms={ms}")
logger.warning(f"SSE error product={product_id} page={page_key} err={exc}")
logger.info(f"SSE cancelled product={product_id} page={page_key} chunks_so_far={n}")
```

**Frontend（dev-only）：**
```typescript
if (process.env.NODE_ENV === "development") {
  console.debug("[copilot-stream]", frame.type, frame);
}
```

## 10. Testing

### Backend pytest（3 条新）

**File:** `tests/backend/test_copilot_chat_stream.py`

1. `test_copilot_chat_stream_returns_sse_frames`
   - Mock `GeminiClient.generate_stream` yield 3 chunks
   - POST `/frontend/copilot/chat/stream`
   - 断言 response body 按 `\n\n` 切出 frames：1×context + 3×delta + 1×envelope + 1×done
   - 每个 frame 是 `data: {...}` 格式
2. `test_copilot_chat_stream_envelope_last`
   - 断言 envelope frame 一定在 done 之前
   - 断言 envelope payload 含 `followUpPrompts / recommendedNextActions / actionLinks`
3. `test_copilot_chat_stream_error_frame`
   - Mock Gemini 抛 RuntimeError
   - 断言首个非 context frame 是 `{type:"error"}` + 紧跟 `{type:"done"}`
   - 断言 response status 仍 200（SSE 错误在 body 内，不用 HTTP 5xx）

### 手动验证

- Chrome DevTools Network 选中 `/chat/stream` → EventStream tab 看 frame 序列
- Performance tab 测 `fetchStart → first data frame` 延迟 ≤ 0.8s
- 对话中切到 /upload → 后端日志看到 `SSE cancelled` + `chunks_so_far=N`

## 11. Acceptance Criteria（硬标准）

- [ ] `DEBUG=true pytest -q` ≥ 395 passed（原 392 + 3 新 SSE 测）
- [ ] `npm run build` 成功
- [ ] Chrome DevTools EventStream 显示正确 frame 序列
- [ ] 首字延迟 ≤ 0.8s（Performance tab 实测）
- [ ] 切页触发 AbortController，后端日志出现 `SSE cancelled`
- [ ] 老 `/chat` endpoint 不变，`NEXT_PUBLIC_COPILOT_STREAM_ENABLED=0` 成功回退
- [ ] 前端打字机效果流畅（无明显闪烁 / 跳动）
- [ ] Copilot 回复里的 followUpPrompts / actionLinks / warning 在流结束时正常出现
- [ ] git status clean，主人决定 commit 时机

## 12. Risks & Mitigations

| 风险 | 影响 | 应对 |
|---|---|---|
| google-genai SDK `generate_content_stream` 在 1.56 版本签名不稳 | 后端 generate_stream 构造不出 | 实施前用 Context7 MCP / pip show 确认版本 + API docs |
| Next.js 16 Turbopack dev server 对 SSE 代理不稳 | 开发环境看不到流 | 绕过 dev server，直接访问后端 8008；或 prod build 验证 |
| React 19 批量更新导致 delta 聚合过慢 | 打字机感闪烁 | 实测若明显则加 `flushSync` 或 rAF 刷新 |
| OneDrive 锁 `.next` 导致 rebuild 失败 | 构建 hang | 用 `start.ps1 -ForceRebuild` 绕过 |
| 后端 `asyncio.CancelledError` 捕获不当导致 coroutine 泄漏 | 内存 / 连接池耗尽 | generator 严格 `try/finally` + 日志 |
| 45s timeout 触发后用户体验不好 | 偶发断流 | Gemini 最长实测 ≈25s，预留 buffer；超时文案"响应太长，请简化问题重试" |

## 13. Out of Scope（为后续 mini-sprint 留接口）

- **A2 Hyperlink**：`envelope.message` 字段将来加 markdown 渲染；本 sprint 保持 plain text 即可
- **A3 Daily Insights**：未来新表 `daily_insights` + `/frontend/insights/*` endpoints；和 Copilot 流式解耦
- **多用户并发限流**：当前单用户单产品无需，未来多租户再加 semaphore
- **流式缓存**：同样 prompt 二次请求不缓存，下一轮性能 sprint 再考虑

## 14. References

- `src/ai/chat.py::ChatAssistant.process_message` — 非流式 baseline
- `src/ai/client.py::GeminiClient.generate` — 非流式 Gemini 封装
- `src/backend/copilot_chat.py::process_frontend_copilot_turn` — 现 handler
- `frontend/src/components/copilot-panel.tsx::sendMessage` — 现前端逻辑
- Parent plan：`C:\Users\jackl\.claude\plans\https-github-com-wekhoh-zeoprix-amz-st-a-tender-donut.md` Sprint 4 章节
