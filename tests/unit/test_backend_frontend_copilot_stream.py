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
