from __future__ import annotations

import json
import pandas as pd
from fastapi.testclient import TestClient

from src.backend.app import create_app
from src.data.db import Database
from src.ui.pages.settings_data import build_full_backup_export_payload


def _bootstrap(monkeypatch, tmp_path):
    legacy_db_path = tmp_path / 'legacy-app.db'
    monkeypatch.setenv('DATABASE_PATH', str(legacy_db_path))
    monkeypatch.setenv('AMZ_BACKEND_DATABASE_URL', f"sqlite:///{(tmp_path / 'backend-frontend-settings.db').as_posix()}")
    db = Database(str(legacy_db_path))
    db.init_schema()
    db.init_default_rules()
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
    return db, product_id


def test_frontend_settings_restore_backup_endpoint(monkeypatch, tmp_path):
    db, product_id = _bootstrap(monkeypatch, tmp_path)
    payload = build_full_backup_export_payload(db, product_id)
    backup_data = json.loads(payload['data'].decode('utf-8'))
    db.close()

    with TestClient(create_app()) as client:
        response = client.post('/frontend/settings/restore-backup', json={
            'product_id': product_id,
            'restore_as_new_product': True,
            'backup_data': backup_data,
        })

    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'success'
    assert body['restoredProductId'] != product_id


def test_frontend_settings_config_endpoint_updates_product_config(monkeypatch, tmp_path):
    db, product_id = _bootstrap(monkeypatch, tmp_path)
    db.close()

    with TestClient(create_app()) as client:
        response = client.post('/frontend/settings/product-config', json={
            'product_id': product_id,
            'core_keywords': ['travel pillow', 'neck pillow'],
            'related_keywords': ['airplane pillow'],
            'competitor_asins': ['b0comp12345'],
            'own_variants': ['b0own12345'],
        })

    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'success'
    assert body['configEditor']['coreKeywords'] == ['travel pillow', 'neck pillow']
    assert body['configEditor']['competitorAsins'] == ['B0COMP12345']
    assert body['ruleVersionCount'] >= 1
    assert body['recentRuleVersions']

    db = Database(str(tmp_path / 'legacy-app.db'))
    product = db.get_product(product_id)
    db.close()
    assert product['config']['core_keywords'] == ['travel pillow', 'neck pillow']
    assert product['config']['own_variants'] == ['B0OWN12345']


def test_frontend_settings_restore_rule_version_endpoint(monkeypatch, tmp_path):
    db, product_id = _bootstrap(monkeypatch, tmp_path)
    db.update_product_config(product_id, {'core_keywords': ['new keyword']})
    from src.ui.pages.settings_data import save_config_version
    save_config_version(db, product_id, {'core_keywords': ['travel pillow']}, {'core_keywords': ['new keyword']})
    db.close()

    with TestClient(create_app()) as client:
        response = client.post('/frontend/settings/rule-versions/restore', json={
            'product_id': product_id,
            'version': 1,
        })

    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'success'
    assert body['ruleVersionCount'] >= 1
