"""Tests for A1 SSE streaming (Sprint 4).

Project convention: sync test functions; drive async code with
``asyncio.run(...)``.  ``pytest-asyncio`` is not installed.
"""

from __future__ import annotations

import asyncio
import json  # noqa: F401 — used by later tasks (T3/T4)
from typing import Iterator
from unittest.mock import MagicMock, patch  # noqa: F401 — used by later tasks

from src.ai.client import GeminiClient


class _FakeChunk:
    def __init__(self, text: str) -> None:
        self.text = text


def _fake_stream(chunks: list[str]) -> Iterator[_FakeChunk]:
    return iter(_FakeChunk(t) for t in chunks)


async def _collect(aiter) -> list:
    out = []
    async for item in aiter:
        out.append(item)
    return out


def test_gemini_client_generate_stream_yields_text_chunks():
    client = GeminiClient(api_key="test-key", model="gemini-2.5-flash")
    with patch.object(
        client.client.models,
        "generate_content_stream",
        return_value=_fake_stream(["Hello", " ", "world"]),
    ):
        out = asyncio.run(_collect(client.generate_stream("prompt")))
        assert out == ["Hello", " ", "world"]


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
    assert env["warning"] is None
    assert "intent" in env


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
        cc,
        "build_ai_context_pack",
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
        payload = json.loads(line[len("data: ") :])
        frame_types.append(payload["type"])

    assert frame_types[0] == "context"
    assert "delta" in frame_types
    assert frame_types[-2] == "envelope"
    assert frame_types[-1] == "done"


def test_chat_stream_endpoint_returns_sse_frames(monkeypatch):
    from src.backend import copilot_chat as cc
    from src.backend import app as app_module

    async def fake_turn_stream(**kwargs):
        yield b'data: {"type":"context","contextLabel":"ok"}\n\n'
        yield b'data: {"type":"delta","text":"hi"}\n\n'
        yield (
            b'data: {"type":"envelope","followUpPrompts":[],'
            b'"recommendedNextActions":[],"actionLinks":[],"warning":null}\n\n'
        )
        yield b'data: {"type":"done"}\n\n'

    monkeypatch.setattr(cc, "process_frontend_copilot_turn_stream", fake_turn_stream)
    monkeypatch.setattr(
        app_module, "process_frontend_copilot_turn_stream", fake_turn_stream
    )

    from fastapi.testclient import TestClient
    from src.backend.app import create_app

    client = TestClient(create_app())

    response = client.post(
        "/frontend/copilot/chat/stream",
        json={
            "product_id": None,
            "page_key": "workbench",
            "page_title": "工作台",
            "user_message": "hi",
            "history": [],
            "page_context": None,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = [
        json.loads(line[len("data: ") :])
        for line in response.text.split("\n\n")
        if line.strip().startswith("data: ")
    ]
    assert [f["type"] for f in frames] == ["context", "delta", "envelope", "done"]


def test_chat_stream_endpoint_envelope_before_done(monkeypatch):
    from src.backend import copilot_chat as cc
    from src.backend import app as app_module

    async def fake_turn_stream(**kwargs):
        yield b'data: {"type":"delta","text":"abc"}\n\n'
        yield (
            b'data: {"type":"envelope","followUpPrompts":["p1"],'
            b'"recommendedNextActions":["a1"],"actionLinks":[],'
            b'"warning":null}\n\n'
        )
        yield b'data: {"type":"done"}\n\n'

    monkeypatch.setattr(cc, "process_frontend_copilot_turn_stream", fake_turn_stream)
    monkeypatch.setattr(
        app_module, "process_frontend_copilot_turn_stream", fake_turn_stream
    )

    from fastapi.testclient import TestClient
    from src.backend.app import create_app

    client = TestClient(create_app())

    response = client.post(
        "/frontend/copilot/chat/stream",
        json={
            "product_id": None,
            "page_key": "workbench",
            "page_title": "工作台",
            "user_message": "x",
            "history": [],
            "page_context": None,
        },
    )
    lines = [
        line
        for line in response.text.split("\n\n")
        if line.strip().startswith("data: ")
    ]
    types = [json.loads(line[len("data: ") :])["type"] for line in lines]
    assert types[-2] == "envelope"
    assert types[-1] == "done"
    envelope = json.loads(lines[-2][len("data: ") :])
    assert envelope["followUpPrompts"] == ["p1"]
    assert envelope["recommendedNextActions"] == ["a1"]


def test_chat_stream_endpoint_error_frame(monkeypatch):
    from src.backend import copilot_chat as cc
    from src.backend import app as app_module

    async def fake_turn_stream(**kwargs):
        yield b'data: {"type":"error","message":"boom"}\n\n'
        yield b'data: {"type":"done"}\n\n'

    monkeypatch.setattr(cc, "process_frontend_copilot_turn_stream", fake_turn_stream)
    monkeypatch.setattr(
        app_module, "process_frontend_copilot_turn_stream", fake_turn_stream
    )

    from fastapi.testclient import TestClient
    from src.backend.app import create_app

    client = TestClient(create_app())

    response = client.post(
        "/frontend/copilot/chat/stream",
        json={
            "product_id": None,
            "page_key": "workbench",
            "page_title": "工作台",
            "user_message": "x",
            "history": [],
            "page_context": None,
        },
    )
    assert response.status_code == 200
    lines = [
        line
        for line in response.text.split("\n\n")
        if line.strip().startswith("data: ")
    ]
    first = json.loads(lines[0][len("data: ") :])
    assert first["type"] == "error"
    assert "boom" in first["message"]
    assert json.loads(lines[-1][len("data: ") :])["type"] == "done"


# ── Sprint 5 · D.4 — process_frontend_copilot_turn_stream error paths ────


def test_copilot_stream_forwards_assistant_error_frame(tmp_path, monkeypatch):
    """ChatAssistant yields ('error', {message}) → SSE error frame emitted + done."""
    from src.backend import copilot_chat as cc

    async def fake_stream(*args, **kwargs):
        yield ("context", "ctx")
        yield ("delta", "partial")
        yield ("error", {"message": "gemini down"})
        # Envelope NOT expected after error

    mock_assistant = MagicMock()
    mock_assistant.process_message_stream = fake_stream

    monkeypatch.setattr(cc, "get_chat_assistant", lambda **kwargs: mock_assistant)
    monkeypatch.setattr(cc, "_get_app_database_path", lambda: tmp_path / "t.db")
    (tmp_path / "t.db").write_bytes(b"")
    monkeypatch.setattr(
        cc,
        "build_ai_context_pack",
        lambda *a, **k: MagicMock(context_label="ctx", warning=None),
    )

    async def run():
        buf = b""
        async for piece in cc.process_frontend_copilot_turn_stream(
            product_id=None,
            page_key="workbench",
            page_title="工作台",
            user_message="hi",
        ):
            buf += piece
        return buf

    body = asyncio.run(run()).decode("utf-8")
    frames = [
        json.loads(evt.strip()[len("data: ") :])
        for evt in body.split("\n\n")
        if evt.strip().startswith("data: ")
    ]
    types = [f["type"] for f in frames]
    assert "error" in types
    error_frame = next(f for f in frames if f["type"] == "error")
    assert "gemini down" in error_frame["message"]
    # envelope must NOT appear after error
    assert "envelope" not in types
    assert types[-1] == "done"


def test_copilot_stream_outer_exception_emits_error_and_done(tmp_path, monkeypatch):
    """Upstream (context-pack build) exception → outer except fires → error + done frames."""
    from src.backend import copilot_chat as cc

    def _boom(*args, **kwargs):
        raise RuntimeError("context build exploded")

    monkeypatch.setattr(cc, "_get_app_database_path", lambda: tmp_path / "t.db")
    (tmp_path / "t.db").write_bytes(b"")
    monkeypatch.setattr(cc, "build_ai_context_pack", _boom)

    async def run():
        buf = b""
        async for piece in cc.process_frontend_copilot_turn_stream(
            product_id=None,
            page_key="workbench",
            page_title="工作台",
            user_message="hi",
        ):
            buf += piece
        return buf

    body = asyncio.run(run()).decode("utf-8")
    frames = [
        json.loads(evt.strip()[len("data: ") :])
        for evt in body.split("\n\n")
        if evt.strip().startswith("data: ")
    ]
    types = [f["type"] for f in frames]
    assert types[0] == "error"
    assert "context build exploded" in frames[0]["message"]
    assert types[-1] == "done"


# ── Sprint 5 · D.4 续 — timeout / cancel paths ───────────────────────────


def _configure_assistant_that_hangs(tmp_path, monkeypatch, cc):
    """Shared helper: 装一个永不 yield 的 assistant + 打通 build_ai_context_pack。"""

    async def never_yields(*args, **kwargs):
        if False:
            yield  # pragma: no cover  — 让函数成为 async generator
        await asyncio.sleep(3600)

    mock_assistant = MagicMock()
    mock_assistant.process_message_stream = never_yields
    monkeypatch.setattr(cc, "get_chat_assistant", lambda **kwargs: mock_assistant)
    monkeypatch.setattr(cc, "_get_app_database_path", lambda: tmp_path / "t.db")
    (tmp_path / "t.db").write_bytes(b"")
    monkeypatch.setattr(
        cc,
        "build_ai_context_pack",
        lambda *a, **k: MagicMock(context_label="ctx", warning=None),
    )


async def _cancel_pending_awaitable(awaitable) -> None:
    """取消传入的 awaitable，避免 'coroutine was never awaited' warning。"""
    task = asyncio.ensure_future(awaitable)
    task.cancel()
    try:
        await task
    except BaseException:
        pass


def test_copilot_stream_emits_error_frame_on_timeout(tmp_path, monkeypatch):
    """Gemini 流响应超过 45s → `asyncio.wait_for` TimeoutError
    应被捕获并转成 `error` + `done` 帧，对前端友好。"""
    from src.backend import copilot_chat as cc

    _configure_assistant_that_hangs(tmp_path, monkeypatch, cc)

    async def fake_wait_for(awaitable, timeout):
        await _cancel_pending_awaitable(awaitable)
        raise asyncio.TimeoutError

    monkeypatch.setattr(cc.asyncio, "wait_for", fake_wait_for)

    async def run():
        buf = b""
        async for piece in cc.process_frontend_copilot_turn_stream(
            product_id=None,
            page_key="workbench",
            page_title="工作台",
            user_message="hi",
        ):
            buf += piece
        return buf

    body = asyncio.run(run()).decode("utf-8")
    frames = [
        json.loads(evt.strip()[len("data: ") :])
        for evt in body.split("\n\n")
        if evt.strip().startswith("data: ")
    ]
    types = [f["type"] for f in frames]
    assert "error" in types
    err = next(f for f in frames if f["type"] == "error")
    assert "超时" in err["message"]
    assert types[-1] == "done"


def test_copilot_stream_reraises_cancelled_error(tmp_path, monkeypatch):
    """客户端断开连接 → asyncio.CancelledError 从 pump 抛出；
    外层 except 链把它记成 'SSE cancelled' 日志后 `raise`。调用方
    必须能接住 CancelledError 才能做资源清理。"""
    import pytest as _pytest

    from src.backend import copilot_chat as cc

    _configure_assistant_that_hangs(tmp_path, monkeypatch, cc)

    async def fake_wait_for(awaitable, timeout):
        await _cancel_pending_awaitable(awaitable)
        raise asyncio.CancelledError

    monkeypatch.setattr(cc.asyncio, "wait_for", fake_wait_for)

    async def run():
        async for _ in cc.process_frontend_copilot_turn_stream(
            product_id=None,
            page_key="workbench",
            page_title="工作台",
            user_message="hi",
        ):
            pass

    with _pytest.raises(asyncio.CancelledError):
        asyncio.run(run())
