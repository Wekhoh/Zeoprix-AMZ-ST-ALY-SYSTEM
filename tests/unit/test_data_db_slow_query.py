"""Tests for Sprint 5 · C.3 — SQLite slow query trace.

Covers: threshold env var, stats accumulation, snippet truncation.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.data import db as db_module
from src.data.db import (
    Database,
    _slow_query_threshold_ms,
    get_slow_query_stats,
    reset_slow_query_stats,
)


@pytest.fixture(autouse=True)
def _clear_stats():
    reset_slow_query_stats()
    yield
    reset_slow_query_stats()


def test_threshold_defaults_to_100ms_when_env_unset(monkeypatch):
    monkeypatch.delenv("AMZ_DB_SLOW_QUERY_MS", raising=False)
    assert _slow_query_threshold_ms() == 100


def test_threshold_reads_env_override(monkeypatch):
    monkeypatch.setenv("AMZ_DB_SLOW_QUERY_MS", "5")
    assert _slow_query_threshold_ms() == 5


def test_threshold_ignores_invalid_env_value(monkeypatch):
    monkeypatch.setenv("AMZ_DB_SLOW_QUERY_MS", "not-a-number")
    assert _slow_query_threshold_ms() == 100


def _make_raw_database(tmp_path, name: str) -> Database:
    """Bypass bootstrap schema — wrap a bare sqlite3 connection in Database."""
    db = Database.__new__(Database)
    db.db_path = str(tmp_path / name)
    db.conn = sqlite3.connect(db.db_path)
    return db


def test_execute_records_stats_when_threshold_zero(monkeypatch, tmp_path):
    """threshold=0 → every query gets recorded, proving the hook fires."""
    monkeypatch.setenv("AMZ_DB_SLOW_QUERY_MS", "0")

    db = _make_raw_database(tmp_path, "trace-test.db")
    db.execute("SELECT 1")
    db.execute("SELECT 1")
    db.conn.close()

    stats = get_slow_query_stats()
    assert "SELECT 1" in stats
    assert stats["SELECT 1"]["count"] == 2
    assert stats["SELECT 1"]["max_ms"] >= 0


def test_executemany_records_stats_when_threshold_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("AMZ_DB_SLOW_QUERY_MS", "0")

    db = _make_raw_database(tmp_path, "trace-many.db")
    db.conn.execute("CREATE TABLE t (val INTEGER)")
    db.executemany("INSERT INTO t VALUES (?)", [(1,), (2,), (3,)])
    db.conn.close()

    stats = get_slow_query_stats()
    hit = [k for k in stats if k.startswith("INSERT INTO t VALUES")]
    assert hit, f"expected INSERT entry; got keys={list(stats.keys())}"


def test_record_slow_query_truncates_long_sql():
    """SQL snippet exceeding 160 chars must be truncated (keep keys bounded)."""
    long_sql = "SELECT " + ", ".join(f"col_{i}" for i in range(200)) + " FROM t"
    db_module._record_slow_query(long_sql, 12.3)

    stats = get_slow_query_stats()
    keys = list(stats.keys())
    assert len(keys) == 1
    assert len(keys[0]) <= db_module._SLOW_QUERY_LOG_LIMIT


def test_get_slow_query_stats_returns_count_avg_max_shape():
    db_module._record_slow_query("SELECT x", 10.0)
    db_module._record_slow_query("SELECT x", 30.0)

    stats = get_slow_query_stats()
    assert stats["SELECT x"] == {"count": 2, "avg_ms": 20.0, "max_ms": 30.0}
