"""Tests for A3 daily insights endpoints (Sprint 4)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.ai.analyzer import InsightReport
from src.backend import insights as insights_module
from src.backend.app import create_app
from src.data.db import Database


@pytest.fixture
def insights_client(tmp_path, monkeypatch):
    """FastAPI TestClient with an isolated app.db + mocked AI analyzer."""
    db_file = tmp_path / "insights_test.db"

    def _fake_db_path():
        return db_file

    from src.backend import workbench_payload

    monkeypatch.setattr(workbench_payload, "_get_app_database_path", _fake_db_path)

    canned = InsightReport(
        summary="AI 洞察测试摘要",
        key_findings=["finding-a", "finding-b"],
        recommendations=["rec-x", "rec-y"],
        statistics={"total_terms": 3, "negative_count": 1, "manual_count": 2},
    )

    fake_analyzer = type(
        "FakeAnalyzer",
        (),
        {"generate_insights": lambda self, r, p=None: canned},
    )()
    monkeypatch.setattr(insights_module, "get_ai_analyzer", lambda: fake_analyzer)
    monkeypatch.setattr(
        insights_module, "analyze_search_terms_cached", lambda db, pid: []
    )

    with Database(str(db_file)) as db:
        insights_module.ensure_daily_insights_schema(db)

    client = TestClient(create_app())
    return client, db_file


def test_today_returns_null_when_no_row(insights_client):
    client, _ = insights_client
    response = client.get("/frontend/insights/today")
    assert response.status_code == 200
    body = response.json()
    assert body == {"today": None}


def test_generate_creates_row_and_returns_report(insights_client):
    client, _ = insights_client
    response = client.post("/frontend/insights/generate")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "AI 洞察测试摘要"
    assert body["key_findings"] == ["finding-a", "finding-b"]
    assert body["recommendations"] == ["rec-x", "rec-y"]
    assert body["statistics"]["total_terms"] == 3
    assert body["id"] is not None
    assert body["date"]  # YYYY-MM-DD populated


def test_today_returns_stored_row_after_generate(insights_client):
    client, _ = insights_client
    client.post("/frontend/insights/generate")
    response = client.get("/frontend/insights/today")
    assert response.status_code == 200
    body = response.json()
    assert body["today"] is not None
    assert body["today"]["summary"] == "AI 洞察测试摘要"
    assert body["today"]["recommendations"] == ["rec-x", "rec-y"]


def test_generate_with_product_id_filters_today(insights_client):
    """Different product_id yields distinct today rows."""
    client, _ = insights_client
    client.post("/frontend/insights/generate?product_id=1")
    response_p1 = client.get("/frontend/insights/today?product_id=1")
    response_p2 = client.get("/frontend/insights/today?product_id=2")
    assert response_p1.json()["today"]["product_id"] == 1
    # product_id=2 has no stored row yet
    assert response_p2.json()["today"] is None
