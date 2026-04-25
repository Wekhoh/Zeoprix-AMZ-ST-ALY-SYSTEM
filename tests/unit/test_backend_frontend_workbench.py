from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

from src.backend.app import create_app
from src.data.db import Database


def test_frontend_workbench_endpoint_reads_legacy_product_data(monkeypatch, tmp_path):
    legacy_db_path = tmp_path / "legacy-app.db"
    monkeypatch.setenv("DATABASE_PATH", str(legacy_db_path))
    monkeypatch.setenv(
        "AMZ_BACKEND_DATABASE_URL",
        f"sqlite:///{(tmp_path / 'backend-workbench.db').as_posix()}",
    )

    db = Database(str(legacy_db_path))
    db.init_schema()
    db.init_default_rules()
    product_id = db.create_product(name="真实产品", asin="B0TEST12345", category="Home")
    campaign_id = db.get_or_create_campaign(
        product_id=product_id, name="Auto Campaign", match_type="auto"
    )
    df = pd.DataFrame(
        [
            {
                "term": "travel pillow",
                "impressions": 120,
                "clicks": 25,
                "ctr": 0.21,
                "spend": 18.5,
                "cpc": 0.74,
                "orders": 2,
                "sales": 42.0,
                "acos": 0.44,
                "roas": 2.27,
                "conversion_rate": 0.08,
                "report_date": "2026-04-11",
            }
        ]
    )
    db.save_search_terms(df, campaign_id)
    snapshot_id = db.save_analysis_run_snapshot(
        product_id,
        [
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "triggered_rule": "高点击无转化",
                "suggested_action": "否定精准",
                "action_type": "negative_exact",
                "spend": 18.5,
                "sales": 42.0,
                "orders": 2,
                "confidence": 1.0,
            }
        ],
        summary={"item_count": 1},
    )
    db.create_execution_batch(
        product_id=product_id,
        batch_type="negative",
        summary={
            "item_count": 1,
            "items": [{"term": "travel pillow"}],
            "baseline_snapshot_id": snapshot_id,
            "spend_total": 18.5,
            "sales_total": 42.0,
        },
        draft_note="test batch",
    )
    db.close()

    with TestClient(create_app()) as client:
        response = client.get("/frontend/workbench")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "live"
    assert body["productContext"]["name"] == "真实产品"
    assert body["workbenchStats"][1]["value"] != "尚未分析"
    assert "·" in body["workbenchStats"][1]["value"]
    assert body["analysisRows"][0]["term"] == "travel pillow"
    assert body["executionBatches"][0]["code"].startswith("NEG-")


# ── Sprint A.1 · review payload 增强（cluster + historical decisions）────


def test_cluster_pending_terms_groups_similar_terms():
    """SequenceMatcher.ratio() ≥ 0.7 的词应同 cluster_id。"""
    from src.backend.workbench_payload import _cluster_pending_terms

    items = [
        {"term": "travel pillow"},
        {"term": "travel pillows"},  # 与上 ratio ≈ 0.96
        {"term": "neck pillow"},  # 与上 ratio ≈ 0.71
        {"term": "B07ABC1234"},  # 完全不相关
    ]
    clusters = _cluster_pending_terms(items)
    assert clusters["travel pillow"] == clusters["travel pillows"], (
        "近似词应在同 cluster"
    )
    assert clusters["b07abc1234"] != clusters["travel pillow"], "ASIN 应单独 cluster"


def test_cluster_pending_terms_handles_empty_and_singleton():
    from src.backend.workbench_payload import _cluster_pending_terms

    assert _cluster_pending_terms([]) == {}
    single = _cluster_pending_terms([{"term": "wireless mouse"}])
    assert single == {"wireless mouse": 0}


def test_fetch_historical_decisions_filters_pending_and_sorts_desc():
    """已决策的按时间降序返回；pending 状态过滤掉。"""
    from unittest.mock import MagicMock

    from src.backend.workbench_payload import _fetch_historical_decisions

    db = MagicMock()
    db.get_manual_reviews_by_term.return_value = [
        {
            "relevance": "irrelevant",
            "updated_at": "2026-04-01 10:00:00",
            "scope": "global",
            "campaign_id": 1,
            "relevance_notes": "明显跑偏",
        },
        {
            "relevance": "pending",  # 应过滤
            "updated_at": "2026-04-15 10:00:00",
        },
        {
            "relevance": "strong_core",
            "updated_at": "2026-04-20 10:00:00",
            "scope": "local",
            "notes": "实测有单",
        },
    ]
    result = _fetch_historical_decisions(db, product_id=1, term="travel pillow")
    assert len(result) == 2
    # 降序：04-20 在前
    assert "2026-04-20" in (result[0]["decidedAt"] or "")
    assert result[0]["decision"] == "strong_core"
    assert result[1]["decision"] == "irrelevant"


def test_fetch_historical_decisions_returns_empty_for_blank_term():
    from unittest.mock import MagicMock

    from src.backend.workbench_payload import _fetch_historical_decisions

    db = MagicMock()
    assert _fetch_historical_decisions(db, 1, "") == []
    # 空串短路 → 不调 db 方法
    db.get_manual_reviews_by_term.assert_not_called()
