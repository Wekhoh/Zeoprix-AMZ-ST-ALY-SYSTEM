from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

from src.backend.app import create_app
from src.data.db import Database


def _bootstrap(monkeypatch, tmp_path):
    legacy_db_path = tmp_path / "legacy-app.db"
    monkeypatch.setenv("DATABASE_PATH", str(legacy_db_path))
    monkeypatch.setenv(
        "AMZ_BACKEND_DATABASE_URL",
        f"sqlite:///{(tmp_path / 'backend-frontend-mutations.db').as_posix()}",
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
    db.save_analysis_run_snapshot(
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
    db.upsert_manual_review(
        product_id=product_id,
        term="travel pillow",
        term_type="keyword",
        campaign_id=campaign_id,
        relevance="pending",
        reviewed=False,
    )
    db.close()
    return product_id, campaign_id


def test_frontend_actions_batch_endpoints_roundtrip(monkeypatch, tmp_path):
    product_id, _ = _bootstrap(monkeypatch, tmp_path)
    with TestClient(create_app()) as client:
        create_response = client.post(
            "/frontend/actions/execution-batches",
            json={
                "product_id": product_id,
                "batch_type": "negative",
                "draft_note": "from test",
            },
        )
        assert create_response.status_code == 200
        batch = create_response.json()
        assert batch["batch_type"] == "negative"
        assert batch["id"]

        update_response = client.patch(
            f"/frontend/actions/execution-batches/{batch['id']}",
            json={"status": "executed", "execution_note": "done"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "executed"


def test_frontend_review_decision_endpoint_updates_manual_review(monkeypatch, tmp_path):
    product_id, campaign_id = _bootstrap(monkeypatch, tmp_path)
    with TestClient(create_app()) as client:
        response = client.post(
            "/frontend/review/manual-reviews",
            json={
                "product_id": product_id,
                "term": "travel pillow",
                "term_type": "keyword",
                "campaign_id": campaign_id,
                "relevance": "strong_core",
                "notes": "looks good",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["reviewId"]
    assert body["stats"]["reviewed"] >= 1
