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
