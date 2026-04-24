# Sprint 4 · A1 Copilot SSE Streaming — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Copilot 从一次性同步响应改为 SSE 流式输出，首字延迟从 ≈4s 降到 ≤0.8s，用户切页触发 AbortController 主动中止流。

**Architecture:** 后端新增 `POST /frontend/copilot/chat/stream` → `text/event-stream` with typed frames (`context` → N×`delta` → `envelope` → `done`)；前端 `fetch` + `getReader` 实时 append 到 assistant 气泡。老 `/chat` 端点保留作 fallback + env flag 开关。

**Tech Stack:** Python 3.11 + FastAPI + google-genai 1.56 streaming / Next.js 16 + React 19 + fetch Streams API / pytest（现 harness）/ `tests/unit/test_backend_frontend_copilot_stream.py`（新）

**Spec:** `docs/superpowers/specs/2026-04-23-sprint4-a1-copilot-sse-design.md`

**Files Touched (8 files, 5 modify + 3 new):**

| File | Action | Responsibility |
|---|---|---|
| `src/ai/client.py` | Modify | Add `GeminiClient.generate_stream()` async generator wrapping google-genai `generate_content_stream` |
| `src/ai/chat.py` | Modify | Add `ChatAssistant.process_message_stream()` yielding typed frames |
| `src/backend/copilot_chat.py` | Modify | Add `process_frontend_copilot_turn_stream()` async generator formatting frames as SSE bytes |
| `src/backend/app.py` | Modify | Add `POST /frontend/copilot/chat/stream` route |
| `tests/unit/test_backend_frontend_copilot_stream.py` | Create | 5 pytest cases (per-layer + endpoint integration) |
| `frontend/src/lib/copilot-stream.ts` | Create | `streamCopilotChat()` helper with fetch reader + SSE parser + AbortController |
| `frontend/src/components/copilot-panel.tsx` | Modify | `sendMessage` uses streamCopilotChat; AbortController ref + unmount cleanup; env-flag fallback |
| `frontend/.env.production` | Modify | Add `NEXT_PUBLIC_COPILOT_STREAM_ENABLED=1` |

---

## Task 1: Backend — `GeminiClient.generate_stream()`

**Files:**
- Modify: `src/ai/client.py`
- Test: `tests/unit/test_backend_frontend_copilot_stream.py`

- [ ] **Step 1: Verify google-genai streaming API**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && python -c "from google import genai; c = genai.Client(api_key='x'); help(c.models.generate_content_stream)" 2>&1 | head -30`

Expected: signature prints including `model`, `contents`, `config`. Returns `Iterator[GenerateContentResponse]` with `.text` on each chunk.

If method missing or different signature, use Context7 MCP for latest genai streaming docs before continuing.

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_backend_frontend_copilot_stream.py`:

```python
"""Tests for A1 SSE streaming (Sprint 4)."""
from __future__ import annotations

import json
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from src.ai.client import GeminiClient


class _FakeChunk:
    def __init__(self, text: str) -> None:
        self.text = text


def _fake_stream(chunks: list[str]) -> Iterator[_FakeChunk]:
    return iter(_FakeChunk(t) for t in chunks)


@pytest.mark.asyncio
async def test_gemini_client_generate_stream_yields_text_chunks():
    client = GeminiClient(api_key="test-key", model="gemini-2.5-flash")
    with patch.object(
        client.client.models,
        "generate_content_stream",
        return_value=_fake_stream(["Hello", " ", "world"]),
    ):
        out = []
        async for chunk in client.generate_stream("prompt"):
            out.append(chunk)
        assert out == ["Hello", " ", "world"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true python -m pytest tests/unit/test_backend_frontend_copilot_stream.py::test_gemini_client_generate_stream_yields_text_chunks -xvs 2>&1 | tail -20`

Expected: FAIL with `AttributeError: 'GeminiClient' object has no attribute 'generate_stream'`

- [ ] **Step 4: Add `generate_stream` to `src/ai/client.py`**

Add at end of `GeminiClient` class:

```python
    async def generate_stream(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
    ):
        """
        Stream text chunks from Gemini.

        Wraps google-genai client.models.generate_content_stream. Yields
        incremental text chunks; sleeps(0) between chunks so FastAPI can
        flush and honor cancellation.
        """
        import asyncio

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        try:
            stream = self.client.models.generate_content_stream(
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            logger.error(f"Gemini generate_content_stream failed: {exc}")
            raise

        for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yield text
                await asyncio.sleep(0)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true python -m pytest tests/unit/test_backend_frontend_copilot_stream.py::test_gemini_client_generate_stream_yields_text_chunks -xvs 2>&1 | tail -15`

Expected: `1 passed`

- [ ] **Step 6: Commit**

```bash
git add src/ai/client.py tests/unit/test_backend_frontend_copilot_stream.py
git commit -m "feat(ai): add GeminiClient.generate_stream for SSE streaming"
```

---

## Task 2: Backend — `ChatAssistant.process_message_stream()`

**Files:**
- Modify: `src/ai/chat.py`
- Test: `tests/unit/test_backend_frontend_copilot_stream.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_backend_frontend_copilot_stream.py`:

```python
# Project uses sync tests; pytest-asyncio NOT installed. Use asyncio.run.

def test_chat_assistant_process_message_stream_frame_order():
    from src.ai.chat import ChatAssistant

    mock_client = MagicMock(spec=GeminiClient)

    async def fake_stream(*args, **kwargs):
        for text in ["Hello", " world"]:
            yield text

    mock_client.generate_stream = fake_stream
    mock_client.create_chat = MagicMock()

    assistant = ChatAssistant(client=mock_client, db=None, product_id=None)

    async def run():
        frames = []
        async for frame_type, payload in assistant.process_message_stream(
            "什么是 ACOS?", context_label="当前页面"
        ):
            frames.append((frame_type, payload))
        return frames

    frames = asyncio.run(run())

    types_only = [f[0] for f in frames]
    assert types_only[0] == "context"
    assert frames[0][1] == "当前页面"
    delta_frames = [f for f in frames if f[0] == "delta"]
    assert [f[1] for f in delta_frames] == ["Hello", " world"]
    envelope_frames = [f for f in frames if f[0] == "envelope"]
    assert len(envelope_frames) == 1
    env = envelope_frames[0][1]
    assert env["message"] == "Hello world"
    assert "followUpPrompts" in env
    assert "recommendedNextActions" in env
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true python -m pytest tests/unit/test_backend_frontend_copilot_stream.py::test_chat_assistant_process_message_stream_frame_order -xvs 2>&1 | tail -15`

Expected: FAIL with `AttributeError: 'ChatAssistant' object has no attribute 'process_message_stream'`

- [ ] **Step 3: Add method to `src/ai/chat.py`**

Add to `ChatAssistant` class (after existing `process_message`):

```python
    async def process_message_stream(
        self,
        message: str,
        *,
        context_label: str | None = None,
        include_data: bool = True,
    ):
        """
        Stream Copilot turn as typed frames.

        Yields tuples (frame_type, payload) where frame_type ∈
        {"context", "delta", "envelope", "error"}.
        """
        yield ("context", context_label)

        intent = self._detect_intent(message)
        data_context = ""
        if include_data and self.db and self.product_id:
            data_context = self._get_relevant_data(intent, message)

        enhanced_message = message
        if data_context:
            enhanced_message = (
                f"用户问题：{message}\n\n相关数据：\n{data_context}\n\n"
                "请基于以上数据回答用户问题。"
            )

        full_text = ""
        try:
            async for chunk in self.client.generate_stream(
                enhanced_message,
                system_instruction=self.SYSTEM_PROMPT,
            ):
                full_text += chunk
                yield ("delta", chunk)
        except Exception as exc:
            logger.error(f"process_message_stream failed: {exc}")
            yield ("error", {"message": f"AI 助手当前不可用：{exc}"})
            return

        options = self._generate_options(intent, full_text)
        follow_ups = [opt.description or opt.label for opt in options][:3]
        recommended = [opt.label for opt in options][:3]

        yield (
            "envelope",
            {
                "message": full_text,
                "followUpPrompts": follow_ups,
                "recommendedNextActions": recommended,
                "warning": None,
                "intent": intent,
            },
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true python -m pytest tests/unit/test_backend_frontend_copilot_stream.py::test_chat_assistant_process_message_stream_frame_order -xvs 2>&1 | tail -15`

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/ai/chat.py tests/unit/test_backend_frontend_copilot_stream.py
git commit -m "feat(ai): add ChatAssistant.process_message_stream for SSE frames"
```

---

## Task 3: Backend — `process_frontend_copilot_turn_stream()` SSE byte formatter

**Files:**
- Modify: `src/backend/copilot_chat.py`
- Test: `tests/unit/test_backend_frontend_copilot_stream.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_backend_frontend_copilot_stream.py`:

```python
# Sync wrapper via asyncio.run (pytest-asyncio not installed).

def test_copilot_chat_stream_formats_sse_bytes(tmp_path, monkeypatch):
    from src.backend import copilot_chat as cc

    async def fake_stream(*args, **kwargs):
        yield ("context", "测试页面")
        yield ("delta", "Hello")
        yield ("delta", " world")
        yield (
            "envelope",
            {
                "message": "Hello world",
                "followUpPrompts": ["p1"],
                "recommendedNextActions": ["a1"],
                "warning": None,
                "intent": "general",
            },
        )

    mock_assistant = MagicMock()
    mock_assistant.process_message_stream = fake_stream

    monkeypatch.setattr(cc, "get_chat_assistant", lambda **kwargs: mock_assistant)
    monkeypatch.setattr(cc, "_get_app_database_path", lambda: tmp_path / "test.db")
    (tmp_path / "test.db").write_bytes(b"")
    monkeypatch.setattr(
        cc, "build_ai_context_pack",
        lambda *a, **k: MagicMock(context_label="测试页面", warning=None),
    )

    async def run():
        buf = b""
        async for piece in cc.process_frontend_copilot_turn_stream(
            product_id=None,
            page_key="workbench",
            page_title="工作台",
            user_message="test",
        ):
            buf += piece
        return buf

    out_bytes = asyncio.run(run())
    body = out_bytes.decode("utf-8")
    events = [e for e in body.split("\n\n") if e.strip()]
    frame_types = []
    for evt in events:
        line = evt.strip()
        assert line.startswith("data: ")
        payload = json.loads(line[len("data: "):])
        frame_types.append(payload["type"])

    assert frame_types[0] == "context"
    assert "delta" in frame_types
    assert frame_types[-2] == "envelope"
    assert frame_types[-1] == "done"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true python -m pytest tests/unit/test_backend_frontend_copilot_stream.py::test_copilot_chat_stream_formats_sse_bytes -xvs 2>&1 | tail -15`

Expected: FAIL with `AttributeError: module 'src.backend.copilot_chat' has no attribute 'process_frontend_copilot_turn_stream'`

- [ ] **Step 3: Add async generator to `src/backend/copilot_chat.py`**

Add `import json` and `import asyncio` and `import time` at the top if missing. Append at end of file:

```python
async def process_frontend_copilot_turn_stream(
    *,
    product_id: int | None,
    page_key: str,
    page_title: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
    page_context: dict[str, Any] | None = None,
):
    """
    Async generator yielding SSE-formatted bytes 'data: {json}\\n\\n'.

    Frames: context → N×delta → envelope → done (or error → done on failure).
    Applies 45s cap on each pump step; logs start/completed/cancelled/error.
    """
    import asyncio
    import time
    from src.config.logger import get_logger
    from src.data.db import Database

    logger = get_logger(__name__)
    db_path = _get_app_database_path()
    history = history or []
    page_context = page_context or {}

    logger.info(
        f"SSE started product={product_id} page={page_key} "
        f"msg_len={len(user_message)}"
    )
    start = time.perf_counter()
    chunks_count = 0
    total_chars = 0

    def _frame(obj: dict[str, Any]) -> bytes:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")

    try:
        with Database(str(db_path)) as db:
            context_pack = build_ai_context_pack(
                db,
                product_id,
                page_key=page_key,
                page_title=page_title,
                page_context=page_context,
            )
            assistant = get_chat_assistant(db=db, product_id=product_id)

            history_lines: list[str] = []
            for item in history[-6:]:
                role = str(item.get("role") or "user")
                content = str(item.get("content") or "").strip()
                if content:
                    history_lines.append(f"{role}: {content}")

            prompt_sections: list[str] = []
            page_summary = _build_page_context_summary(page_context)
            if page_summary:
                prompt_sections.append(f"当前页面状态：{page_summary}")
            if history_lines:
                prompt_sections.append("最近对话：\n" + "\n".join(history_lines))
            prompt_sections.append(f"当前问题：{user_message.strip()}")
            prompt = "\n\n".join(s for s in prompt_sections if s.strip())

            stream = assistant.process_message_stream(
                prompt, context_label=context_pack.context_label
            )

            async def _pump():
                nonlocal chunks_count, total_chars
                async for frame_type, payload in stream:
                    if frame_type == "context":
                        yield _frame({"type": "context", "contextLabel": payload})
                    elif frame_type == "delta":
                        chunks_count += 1
                        total_chars += len(payload)
                        yield _frame({"type": "delta", "text": payload})
                    elif frame_type == "envelope":
                        action_links = _derive_action_links(
                            payload.get("recommendedNextActions", []), page_key
                        )
                        yield _frame(
                            {
                                "type": "envelope",
                                "followUpPrompts": payload.get("followUpPrompts", []),
                                "recommendedNextActions": payload.get(
                                    "recommendedNextActions", []
                                ),
                                "actionLinks": action_links,
                                "warning": payload.get("warning")
                                or context_pack.warning,
                            }
                        )
                    elif frame_type == "error":
                        yield _frame(
                            {"type": "error", "message": payload.get("message", "")}
                        )

            pump = _pump()
            try:
                while True:
                    piece = await asyncio.wait_for(pump.__anext__(), timeout=45)
                    yield piece
            except StopAsyncIteration:
                pass
            except asyncio.TimeoutError:
                yield _frame({"type": "error", "message": "响应超时，请简化问题重试"})
                logger.warning(
                    f"SSE timeout product={product_id} page={page_key} "
                    f"chunks_so_far={chunks_count}"
                )

            yield _frame({"type": "done"})

    except asyncio.CancelledError:
        logger.info(
            f"SSE cancelled product={product_id} page={page_key} "
            f"chunks_so_far={chunks_count}"
        )
        raise
    except Exception as exc:
        logger.warning(f"SSE error product={product_id} page={page_key} err={exc}")
        yield _frame({"type": "error", "message": f"AI 助手当前不可用：{exc}"})
        yield _frame({"type": "done"})
    finally:
        dur_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"SSE completed product={product_id} page={page_key} "
            f"chunks={chunks_count} chars={total_chars} duration_ms={dur_ms}"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true python -m pytest tests/unit/test_backend_frontend_copilot_stream.py::test_copilot_chat_stream_formats_sse_bytes -xvs 2>&1 | tail -15`

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/backend/copilot_chat.py tests/unit/test_backend_frontend_copilot_stream.py
git commit -m "feat(backend): add copilot chat stream SSE byte formatter"
```

---

## Task 4: Backend — FastAPI `/frontend/copilot/chat/stream` route

**Files:**
- Modify: `src/backend/app.py`
- Test: `tests/unit/test_backend_frontend_copilot_stream.py`

- [ ] **Step 1: Write the failing integration tests**

Append to `tests/unit/test_backend_frontend_copilot_stream.py`:

```python
def test_chat_stream_endpoint_returns_sse_frames(client, monkeypatch):
    from src.backend import copilot_chat as cc

    async def fake_turn_stream(**kwargs):
        yield b'data: {"type":"context","contextLabel":"ok"}\n\n'
        yield b'data: {"type":"delta","text":"hi"}\n\n'
        yield (
            b'data: {"type":"envelope","followUpPrompts":[],'
            b'"recommendedNextActions":[],"actionLinks":[],"warning":null}\n\n'
        )
        yield b'data: {"type":"done"}\n\n'

    monkeypatch.setattr(cc, "process_frontend_copilot_turn_stream", fake_turn_stream)
    response = client.post(
        "/frontend/copilot/chat/stream",
        json={
            "product_id": None, "page_key": "workbench",
            "page_title": "工作台", "user_message": "hi",
            "history": [], "page_context": None,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = [json.loads(line[len("data: "):])
              for line in response.text.split("\n\n")
              if line.strip().startswith("data: ")]
    assert [f["type"] for f in frames] == ["context", "delta", "envelope", "done"]


def test_chat_stream_endpoint_envelope_before_done(client, monkeypatch):
    from src.backend import copilot_chat as cc

    async def fake_turn_stream(**kwargs):
        yield b'data: {"type":"delta","text":"abc"}\n\n'
        yield (
            b'data: {"type":"envelope","followUpPrompts":["p1"],'
            b'"recommendedNextActions":["a1"],"actionLinks":[],'
            b'"warning":null}\n\n'
        )
        yield b'data: {"type":"done"}\n\n'

    monkeypatch.setattr(cc, "process_frontend_copilot_turn_stream", fake_turn_stream)
    response = client.post(
        "/frontend/copilot/chat/stream",
        json={
            "product_id": None, "page_key": "workbench",
            "page_title": "工作台", "user_message": "x",
            "history": [], "page_context": None,
        },
    )
    lines = [l for l in response.text.split("\n\n") if l.strip().startswith("data: ")]
    types = [json.loads(l[len("data: "):])["type"] for l in lines]
    assert types[-2] == "envelope"
    assert types[-1] == "done"
    envelope = json.loads(lines[-2][len("data: "):])
    assert envelope["followUpPrompts"] == ["p1"]
    assert envelope["recommendedNextActions"] == ["a1"]


def test_chat_stream_endpoint_error_frame(client, monkeypatch):
    from src.backend import copilot_chat as cc

    async def fake_turn_stream(**kwargs):
        yield b'data: {"type":"error","message":"boom"}\n\n'
        yield b'data: {"type":"done"}\n\n'

    monkeypatch.setattr(cc, "process_frontend_copilot_turn_stream", fake_turn_stream)
    response = client.post(
        "/frontend/copilot/chat/stream",
        json={
            "product_id": None, "page_key": "workbench",
            "page_title": "工作台", "user_message": "x",
            "history": [], "page_context": None,
        },
    )
    assert response.status_code == 200
    lines = [l for l in response.text.split("\n\n") if l.strip().startswith("data: ")]
    first = json.loads(lines[0][len("data: "):])
    assert first["type"] == "error"
    assert "boom" in first["message"]
    assert json.loads(lines[-1][len("data: "):])["type"] == "done"
```

Note: `client` fixture comes from `tests/conftest.py`. Confirm with `grep -n "def client" tests/conftest.py`. If missing, add locally:
```python
from fastapi.testclient import TestClient
from src.backend.app import create_app

@pytest.fixture
def client():
    return TestClient(create_app())
```

- [ ] **Step 2: Run to verify failures**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true python -m pytest tests/unit/test_backend_frontend_copilot_stream.py -xvs 2>&1 | tail -30`

Expected: 3 new tests FAIL with 404 Not Found

- [ ] **Step 3: Add endpoint to `src/backend/app.py`**

Locate existing `/frontend/copilot/chat` route (around line 577). Immediately after that function, inside the same `create_app` scope, add:

```python
    from fastapi.responses import StreamingResponse
    from src.backend.copilot_chat import process_frontend_copilot_turn_stream

    @app.post("/frontend/copilot/chat/stream", tags=["frontend"])
    async def chat_frontend_copilot_stream(
        payload: FrontendCopilotChatRequest,
    ) -> StreamingResponse:
        return StreamingResponse(
            process_frontend_copilot_turn_stream(
                product_id=payload.product_id,
                page_key=payload.page_key,
                page_title=payload.page_title,
                user_message=payload.user_message,
                history=[m.model_dump() for m in payload.history],
                page_context=payload.page_context,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
```

If `StreamingResponse` already imported at top, remove the inline import. If `process_frontend_copilot_turn` already imported, merge:
```python
from src.backend.copilot_chat import (
    process_frontend_copilot_turn,
    process_frontend_copilot_turn_stream,
)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true python -m pytest tests/unit/test_backend_frontend_copilot_stream.py -xvs 2>&1 | tail -15`

Expected: `5 passed`

- [ ] **Step 5: Run full test suite (regression check)**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true python -m pytest -q 2>&1 | tail -6`

Expected: `397 passed` (baseline 392 + 5 new). Any regression = do not proceed.

- [ ] **Step 6: Commit**

```bash
git add src/backend/app.py tests/unit/test_backend_frontend_copilot_stream.py
git commit -m "feat(backend): add POST /frontend/copilot/chat/stream endpoint"
```

---

## Task 5: Frontend — `copilot-stream.ts` SSE client helper

**Files:**
- Create: `frontend/src/lib/copilot-stream.ts`

No vitest this sprint (spec §3 non-goals; tests deferred to子项目 D).

- [ ] **Step 1: Create the file**

```typescript
// frontend/src/lib/copilot-stream.ts
/**
 * Copilot SSE 流式客户端（Sprint 4 · A1）
 * 调用后端 POST /frontend/copilot/chat/stream，逐 frame 分发到 handlers。
 * AbortController signal 由调用方传入以支持取消。
 */

import { BACKEND_BASE_URL } from "@/lib/backend";

export type ActionLink = { label: string; href: string };

export type CopilotEnvelopeFrame = {
	followUpPrompts: string[];
	recommendedNextActions: string[];
	actionLinks: ActionLink[];
	warning: string | null;
};

export type CopilotFrame =
	| { type: "context"; contextLabel: string | null }
	| { type: "delta"; text: string }
	| ({ type: "envelope" } & CopilotEnvelopeFrame)
	| { type: "error"; message: string }
	| { type: "done" };

export type CopilotChatPayload = {
	product_id: number | null;
	page_key: string;
	page_title: string;
	page_context: Record<string, unknown>;
	user_message: string;
	history: Array<{ role: "assistant" | "user"; content: string }>;
};

export type StreamHandlers = {
	onContext?: (label: string | null) => void;
	onDelta: (text: string) => void;
	onEnvelope: (env: CopilotEnvelopeFrame) => void;
	onError: (message: string) => void;
	signal?: AbortSignal;
};

export async function streamCopilotChat(
	payload: CopilotChatPayload,
	handlers: StreamHandlers,
): Promise<void> {
	const response = await fetch(`${BACKEND_BASE_URL}/frontend/copilot/chat/stream`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
		signal: handlers.signal,
	});
	if (!response.ok) {
		handlers.onError(`HTTP ${response.status}`);
		return;
	}
	if (!response.body) {
		handlers.onError("response body is null");
		return;
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder("utf-8");
	let buffer = "";

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;
			buffer += decoder.decode(value, { stream: true });
			const events = buffer.split("\n\n");
			buffer = events.pop() ?? "";
			for (const evt of events) {
				const line = evt.trim();
				if (!line.startsWith("data: ")) continue;
				const jsonStr = line.slice("data: ".length);
				let frame: CopilotFrame;
				try {
					frame = JSON.parse(jsonStr) as CopilotFrame;
				} catch {
					continue;
				}
				if (process.env.NODE_ENV === "development") {
					console.debug("[copilot-stream]", frame);
				}
				switch (frame.type) {
					case "context":
						handlers.onContext?.(frame.contextLabel);
						break;
					case "delta":
						handlers.onDelta(frame.text);
						break;
					case "envelope":
						handlers.onEnvelope({
							followUpPrompts: frame.followUpPrompts,
							recommendedNextActions: frame.recommendedNextActions,
							actionLinks: frame.actionLinks,
							warning: frame.warning,
						});
						break;
					case "error":
						handlers.onError(frame.message);
						break;
					case "done":
						return;
				}
			}
		}
	} catch (err) {
		if ((err as Error).name === "AbortError") {
			return;
		}
		handlers.onError((err as Error).message);
	} finally {
		reader.releaseLock();
	}
}
```

- [ ] **Step 2: TypeScript check**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统/frontend && npx tsc --noEmit 2>&1 | tail -15`

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/copilot-stream.ts
git commit -m "feat(frontend): add copilot-stream SSE client helper"
```

---

## Task 6: Frontend — integrate `copilot-panel.tsx`

**Files:**
- Modify: `frontend/src/components/copilot-panel.tsx`

- [ ] **Step 1: Add imports**

Near top imports, add:

```typescript
import {
	streamCopilotChat,
	type CopilotEnvelopeFrame,
} from "@/lib/copilot-stream";
```

- [ ] **Step 2: Add AbortController ref + env flag + unmount cleanup**

Inside `CopilotPanel` component body, near existing `const scrollRef = useRef` lines, add:

```typescript
const abortRef = useRef<AbortController | null>(null);
const streamEnabled =
	(process.env.NEXT_PUBLIC_COPILOT_STREAM_ENABLED ?? "1") !== "0";

useEffect(() => {
	return () => {
		abortRef.current?.abort();
	};
}, []);
```

- [ ] **Step 3: Replace `sendMessage` body**

Find existing `async function sendMessage(message: string)` and replace its body entirely:

```typescript
async function sendMessage(message: string) {
	const trimmed = message.trim();
	if (!trimmed) return;
	const nextMessages = [
		...messages,
		{ role: "user" as const, content: trimmed },
		{ role: "assistant" as const, content: "" },
	];
	setMessages(nextMessages);
	setInput("");
	setWarning(null);

	abortRef.current?.abort();
	abortRef.current = new AbortController();

	const appendToLastAssistant = (text: string) => {
		setMessages((current) => {
			if (current.length === 0) return current;
			const last = current[current.length - 1];
			if (last.role !== "assistant") return current;
			const patched = { ...last, content: last.content + text };
			return [...current.slice(0, -1), patched];
		});
	};

	const applyEnvelope = (env: CopilotEnvelopeFrame) => {
		setPrompts(
			env.followUpPrompts.length ? env.followUpPrompts : aiCard.prompts,
		);
		setRecommendedActions(env.recommendedNextActions);
		setActionLinks(env.actionLinks);
		setWarning(env.warning);
	};

	const fallbackNonStream = async () => {
		try {
			const response = await fetch(
				`${BACKEND_BASE_URL}/frontend/copilot/chat`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						product_id: productId ?? null,
						page_key: pageKey,
						page_title: pageTitle,
						page_context: pageContext,
						user_message: trimmed,
						history: nextMessages.slice(-6),
					}),
				},
			);
			const body = (await response
				.json()
				.catch(() => ({ message: "AI 助手当前不可用。" }))) as {
				message?: string;
				followUpPrompts?: string[];
				recommendedNextActions?: string[];
				actionLinks?: ActionLink[];
				warning?: string | null;
			};
			appendToLastAssistant(body.message ?? "AI 助手当前不可用。");
			applyEnvelope({
				followUpPrompts: body.followUpPrompts ?? [],
				recommendedNextActions: body.recommendedNextActions ?? [],
				actionLinks: body.actionLinks ?? [],
				warning: body.warning ?? null,
			});
		} catch {
			setWarning("AI 助手当前不可用，请稍后再试。");
		}
	};

	startTransition(async () => {
		if (!streamEnabled) {
			await fallbackNonStream();
			return;
		}
		try {
			await streamCopilotChat(
				{
					product_id: productId ?? null,
					page_key: pageKey,
					page_title: pageTitle,
					page_context: pageContext,
					user_message: trimmed,
					history: nextMessages.slice(-6),
				},
				{
					onDelta: appendToLastAssistant,
					onEnvelope: applyEnvelope,
					onError: async (msg) => {
						setMessages((current) => {
							const last = current[current.length - 1];
							if (last?.role === "assistant" && last.content === "") {
								return current.slice(0, -1);
							}
							return current;
						});
						setWarning(`流式请求失败：${msg}，已回退到稳定模式`);
						await fallbackNonStream();
					},
					signal: abortRef.current?.signal,
				},
			);
		} finally {
			abortRef.current = null;
		}
	});
}
```

- [ ] **Step 4: TypeScript check**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统/frontend && npx tsc --noEmit 2>&1 | tail -15`

Expected: no errors. If `ActionLink` conflicts between local and copilot-stream.ts export, make the local `type ActionLink` (in copilot-panel.tsx) match the one from copilot-stream.ts — they have the same shape `{ label: string; href: string }`, so either keep local + cast, or remove local and import.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/copilot-panel.tsx
git commit -m "feat(frontend): wire copilot panel to SSE stream with fallback"
```

---

## Task 7: Env var + full verification

**Files:**
- Modify: `frontend/.env.production`

- [ ] **Step 1: Read current env file**

Run: `cat /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统/frontend/.env.production`

Expected: prints existing env lines.

- [ ] **Step 2: Append stream flag**

Use Edit tool with `old_string` = last line of current content, `new_string` = same last line + `\nNEXT_PUBLIC_COPILOT_STREAM_ENABLED=1`. Keeps all existing lines.

Verify:
Run: `grep COPILOT_STREAM_ENABLED /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统/frontend/.env.production`

Expected: `NEXT_PUBLIC_COPILOT_STREAM_ENABLED=1`

- [ ] **Step 3: Run full pytest**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true python -m pytest -q 2>&1 | tail -6`

Expected: `397 passed` (392 baseline + 5 new)

- [ ] **Step 4: Run frontend build**

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统/frontend && npm run build 2>&1 | tail -20`

Expected: `✓ Compiled successfully` + route list identical to prior builds

- [ ] **Step 5: Start servers for manual verification**

Kill stale 3031:
Run: `powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 3031 -State Listen -ErrorAction SilentlyContinue | Select-Object -Expand OwningProcess | ForEach-Object { Stop-Process -Id \$_ -Force }"`

Start backend (if not running):
Run (background): `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && DEBUG=true uvicorn "src.backend.app:create_app" --factory --host 127.0.0.1 --port 8008`

Start frontend:
Run (background): `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统/frontend && npx next start -p 3031 -H 127.0.0.1`

Wait:
Run: `until curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3031/ 2>/dev/null | grep -q "^200$"; do sleep 1; done && echo ready`

- [ ] **Step 6: Chrome manual verification (claude-in-chrome)**

Navigate to `http://127.0.0.1:3031/`, hard refresh. Send Copilot message "为什么 ACOS 高？".

In DevTools → Network → filter `chat/stream` → EventStream tab. Confirm:
```
{"type":"context",...}
{"type":"delta","text":"..."} (many)
{"type":"envelope",...}
{"type":"done"}
```

Performance tab: measure `fetchStart → first delta frame` ≤ 0.8s.

- [ ] **Step 7: Cancellation verification**

While stream is active, click sidebar "数据导入". In backend stdout/log, expect a line like:
```
SSE cancelled product=None page=workbench chunks_so_far=N
```

Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统 && tail -50 logs/app.log 2>&1 | grep -i SSE | head -5`

If log file path differs, check the backend console window directly.

- [ ] **Step 8: Fallback verification**

Disable flag:
Run: `sed -i 's/NEXT_PUBLIC_COPILOT_STREAM_ENABLED=1/NEXT_PUBLIC_COPILOT_STREAM_ENABLED=0/' /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统/frontend/.env.production`

Rebuild + restart:
Run: `cd /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统/frontend && npm run build 2>&1 | tail -6`

Kill + restart server (Step 5 again).

Send Copilot message. DevTools Network: only `/chat` (non-stream) request fires; no `/chat/stream`.

Reset flag:
Run: `sed -i 's/NEXT_PUBLIC_COPILOT_STREAM_ENABLED=0/NEXT_PUBLIC_COPILOT_STREAM_ENABLED=1/' /c/Users/jackl/OneDrive/桌面/AMZ搜索词分析系统/frontend/.env.production`

Rebuild + restart.

- [ ] **Step 9: Final commit**

```bash
git add frontend/.env.production
git commit -m "chore(frontend): enable Copilot SSE streaming by default"
```

- [ ] **Step 10: Report summary**

Output:
- Tests: `pytest -q` = 397 passed
- Build: `npm run build` passed
- Chrome DevTools EventStream: 4 frame types confirmed
- First-byte latency: ___ ms (target ≤ 800 ms)
- Cancellation log: `SSE cancelled ...` appeared
- Fallback: env flag 0 → only `/chat` fires

---

## Self-Review

### 1. Spec coverage

| Spec § | Task | Covered |
|---|---|---|
| §4 Architecture (frame sequence) | Task 3 `_pump` formatter | ✅ |
| §5.1 GeminiClient.generate_stream | Task 1 | ✅ |
| §5.1 ChatAssistant.process_message_stream | Task 2 | ✅ |
| §5.1 process_frontend_copilot_turn_stream | Task 3 | ✅ |
| §5.1 FastAPI /chat/stream route | Task 4 | ✅ |
| §5.2 streamCopilotChat helper | Task 5 | ✅ |
| §5.2 copilot-panel integration | Task 6 | ✅ |
| §6 Data flow (AbortController + unmount cleanup) | Task 6 Step 2 | ✅ |
| §7 Error handling (error frame + fallback) | Task 3 + Task 6 onError | ✅ |
| §7 Client disconnect (CancelledError) | Task 3 except clause | ✅ |
| §7 45s cap | Task 3 `asyncio.wait_for(..., timeout=45)` | ✅ |
| §8 Config env flag | Task 7 Step 2 + Task 6 streamEnabled | ✅ |
| §9 Observability logs | Task 3 logger.info calls | ✅ |
| §10 Testing (3 integration cases) | Task 4 Step 1 (returns_sse_frames / envelope_last / error_frame) + Tasks 1-3 unit tests | ✅ |
| §11 Acceptance criteria (pytest ≥ 395 / build / Chrome verify / ≤ 0.8s / cancel log / fallback) | Task 7 Steps 3-8 | ✅ |

### 2. Placeholder scan

- No TBD / TODO / implement later
- No generic "add error handling" — explicit matrix in Task 3
- Every code block is runnable
- Every command shows expected output

### 3. Type consistency

- `CopilotFrame` discriminated union in Task 5 consumed by Task 6 via import
- `CopilotEnvelopeFrame` exported from copilot-stream.ts, imported in copilot-panel.tsx
- Backend frame tuple `(frame_type, payload)` consistent Task 2 → Task 3
- Frame `type` literals ("context" / "delta" / "envelope" / "error" / "done") identical backend ↔ frontend
- `FrontendCopilotChatRequest` (Pydantic) ↔ `CopilotChatPayload` (TypeScript) field alignment OK

No gaps found.
