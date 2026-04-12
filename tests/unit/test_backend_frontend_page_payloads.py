from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

from src.backend.app import create_app
from src.data.db import Database


def _seed_product(db: Database) -> int:
    product_id = db.create_product(name='真实产品', asin='B0TEST12345', category='Home')
    campaign_id = db.get_or_create_campaign(product_id=product_id, name='Auto Campaign', match_type='auto')
    df = pd.DataFrame([
        {
            'term': 'travel pillow',
            'impressions': 120,
            'clicks': 25,
            'ctr': 0.21,
            'spend': 18.5,
            'cpc': 0.74,
            'orders': 2,
            'sales': 42.0,
            'acos': 0.44,
            'roas': 2.27,
            'conversion_rate': 0.08,
            'report_date': '2026-04-11',
        }
    ])
    db.save_search_terms(df, campaign_id)
    snapshot_id = db.save_analysis_run_snapshot(
        product_id,
        [
            {
                'term': 'travel pillow',
                'term_type': 'keyword',
                'triggered_rule': '高点击无转化',
                'suggested_action': '否定精准',
                'action_type': 'negative_exact',
                'spend': 18.5,
                'sales': 42.0,
                'orders': 2,
                'confidence': 1.0,
            }
        ],
        summary={'item_count': 1},
    )
    db.upsert_manual_review(product_id=product_id, term='travel pillow', reviewed=True, relevance='strong_core')
    db.create_execution_batch(
        product_id=product_id,
        batch_type='negative',
        summary={'item_count': 1, 'items': [{'term': 'travel pillow'}], 'baseline_snapshot_id': snapshot_id, 'spend_total': 18.5, 'sales_total': 42.0},
        draft_note='test batch',
    )
    return product_id


def _bootstrap(monkeypatch, tmp_path):
    legacy_db_path = tmp_path / 'legacy-app.db'
    monkeypatch.setenv('DATABASE_PATH', str(legacy_db_path))
    monkeypatch.setenv('AMZ_BACKEND_DATABASE_URL', f"sqlite:///{(tmp_path / 'backend-workbench.db').as_posix()}")
    db = Database(str(legacy_db_path))
    db.init_schema()
    db.init_default_rules()
    _seed_product(db)
    db.close()


def test_frontend_page_payload_endpoints_return_live_data(monkeypatch, tmp_path):
    _bootstrap(monkeypatch, tmp_path)

    with TestClient(create_app()) as client:
        upload = client.get('/frontend/upload')
        review = client.get('/frontend/review')
        settings = client.get('/frontend/settings')
        actions = client.get('/frontend/actions')
        analysis = client.get('/frontend/analysis')

    assert upload.status_code == 200
    assert review.status_code == 200
    assert settings.status_code == 200
    assert actions.status_code == 200
    assert analysis.status_code == 200

    assert upload.json()['source'] == 'live'
    assert upload.json()['upload']['searchTerms'] == 1
    assert review.json()['review']['stats']['reviewed'] >= 1
    assert settings.json()['settings']['backupSummary']['searchTerms'] == 1
    assert actions.json()['actions']['latestBatchCode'].startswith('NEG-')
    assert analysis.json()['analysis']['rowCount'] >= 1
