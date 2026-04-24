"""Tests for src/ai/client.py (Sprint 5 · D.3).

Targets:
- generate() happy path / empty response / retry / final failure
- generate_json() pure / markdown-wrapped / malformed
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.ai.client import GeminiClient


def _client() -> GeminiClient:
    return GeminiClient(api_key="test-key", model="gemini-2.5-flash")


def _mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


def test_generate_returns_response_text():
    client = _client()
    with patch.object(
        client.client.models,
        "generate_content",
        return_value=_mock_response("hello world"),
    ):
        out = client.generate("prompt")
    assert out == "hello world"


def test_generate_empty_text_returns_empty_string():
    client = _client()
    with patch.object(
        client.client.models,
        "generate_content",
        return_value=_mock_response(""),
    ):
        out = client.generate("prompt")
    assert out == ""


def test_generate_retries_then_succeeds():
    client = _client()
    side_effects = [RuntimeError("flaky"), _mock_response("recovered")]
    with (
        patch.object(
            client.client.models,
            "generate_content",
            side_effect=side_effects,
        ),
        patch("src.ai.client.time.sleep"),
    ):
        out = client.generate("prompt", max_retries=2)
    assert out == "recovered"


def test_generate_raises_after_max_retries():
    client = _client()
    with (
        patch.object(
            client.client.models,
            "generate_content",
            side_effect=RuntimeError("permanent"),
        ),
        patch("src.ai.client.time.sleep"),
    ):
        with pytest.raises(RuntimeError, match="permanent"):
            client.generate("prompt", max_retries=2)


def test_generate_json_parses_pure_json():
    client = _client()
    with patch.object(
        client.client.models,
        "generate_content",
        return_value=_mock_response('{"key": "value", "n": 3}'),
    ):
        out = client.generate_json("prompt")
    assert out == {"key": "value", "n": 3}


def test_generate_json_strips_markdown_code_block():
    client = _client()
    response = '```json\n{"items": [1, 2, 3]}\n```'
    with patch.object(
        client.client.models,
        "generate_content",
        return_value=_mock_response(response),
    ):
        out = client.generate_json("prompt")
    assert out == {"items": [1, 2, 3]}


def test_generate_json_returns_none_on_malformed():
    client = _client()
    with patch.object(
        client.client.models,
        "generate_content",
        return_value=_mock_response("not json at all"),
    ):
        out = client.generate_json("prompt")
    assert out is None
