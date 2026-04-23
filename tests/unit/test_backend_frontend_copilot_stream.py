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
