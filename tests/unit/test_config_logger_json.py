"""Tests for Sprint 5 · B.7 续 — JSON log formatter.

Covers: key shape, extra-fields passthrough, non-JSON-safe value fallback,
env-flag gating for formatter selection.
"""

from __future__ import annotations

import json
import logging

from src.config.logger import JsonFormatter, _select_formatter


def _make_record(
    msg: str = "hello",
    level: int = logging.INFO,
    extra: dict | None = None,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test.logger",
        level=level,
        pathname=__file__,
        lineno=42,
        msg=msg,
        args=(),
        exc_info=None,
    )
    if extra:
        for k, v in extra.items():
            setattr(record, k, v)
    return record


def test_json_formatter_emits_required_keys():
    formatter = JsonFormatter()
    line = formatter.format(_make_record("hi"))
    doc = json.loads(line)

    assert set(doc.keys()) >= {"ts", "level", "logger", "msg"}
    assert doc["level"] == "INFO"
    assert doc["logger"] == "test.logger"
    assert doc["msg"] == "hi"


def test_json_formatter_includes_extra_fields():
    """logger.info('x', extra={'request_id': 'abc'}) 应进入 JSON payload。"""
    formatter = JsonFormatter()
    record = _make_record("req", extra={"request_id": "abc-123", "duration_ms": 42})
    doc = json.loads(formatter.format(record))

    assert doc["request_id"] == "abc-123"
    assert doc["duration_ms"] == 42


def test_json_formatter_falls_back_to_repr_for_non_serializable():
    """非 JSON-safe 值应 repr() 后回传而不是崩掉整行。"""

    class _NotJson:
        def __repr__(self) -> str:
            return "<NotJson sentinel>"

    formatter = JsonFormatter()
    record = _make_record("x", extra={"weird": _NotJson()})
    doc = json.loads(formatter.format(record))

    assert doc["weird"] == "<NotJson sentinel>"


def test_select_formatter_defaults_to_text(monkeypatch):
    monkeypatch.delenv("AMZ_LOG_JSON", raising=False)
    formatter = _select_formatter()
    assert not isinstance(formatter, JsonFormatter)


def test_select_formatter_returns_json_when_env_set(monkeypatch):
    for flag in ("1", "true", "yes", "TRUE"):
        monkeypatch.setenv("AMZ_LOG_JSON", flag)
        assert isinstance(_select_formatter(), JsonFormatter), (
            f"flag={flag!r} should enable JSON"
        )


def test_select_formatter_ignores_invalid_flag_values(monkeypatch):
    for flag in ("0", "no", "false", "", "random"):
        monkeypatch.setenv("AMZ_LOG_JSON", flag)
        assert not isinstance(_select_formatter(), JsonFormatter), (
            f"flag={flag!r} leaked JSON mode"
        )
