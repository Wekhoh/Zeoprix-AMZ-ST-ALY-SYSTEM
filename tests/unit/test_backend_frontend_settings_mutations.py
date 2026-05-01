from __future__ import annotations

import json
import pandas as pd
from fastapi.testclient import TestClient

from src.backend.app import create_app
from src.data.db import Database
from src.services.settings_service import build_full_backup_export_payload


def _bootstrap(monkeypatch, tmp_path):
    legacy_db_path = tmp_path / "legacy-app.db"
    monkeypatch.setenv("DATABASE_PATH", str(legacy_db_path))
    monkeypatch.setenv(
        "AMZ_BACKEND_DATABASE_URL",
        f"sqlite:///{(tmp_path / 'backend-frontend-settings.db').as_posix()}",
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
    return db, product_id


def test_frontend_settings_restore_backup_endpoint(monkeypatch, tmp_path):
    db, product_id = _bootstrap(monkeypatch, tmp_path)
    payload = build_full_backup_export_payload(db, product_id)
    backup_data = json.loads(payload["data"].decode("utf-8"))
    db.close()

    with TestClient(create_app()) as client:
        response = client.post(
            "/frontend/settings/restore-backup",
            json={
                "product_id": product_id,
                "restore_as_new_product": True,
                "backup_data": backup_data,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["restoredProductId"] != product_id


def test_frontend_settings_config_endpoint_updates_product_config(
    monkeypatch, tmp_path
):
    db, product_id = _bootstrap(monkeypatch, tmp_path)
    db.close()

    with TestClient(create_app()) as client:
        response = client.post(
            "/frontend/settings/product-config",
            json={
                "product_id": product_id,
                "core_keywords": ["travel pillow", "neck pillow"],
                "related_keywords": ["airplane pillow"],
                "competitor_asins": ["b0comp12345"],
                "own_variants": ["b0own12345"],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["configEditor"]["coreKeywords"] == ["travel pillow", "neck pillow"]
    assert body["configEditor"]["competitorAsins"] == ["B0COMP12345"]
    assert body["ruleVersionCount"] >= 1
    assert body["recentRuleVersions"]

    db = Database(str(tmp_path / "legacy-app.db"))
    product = db.get_product(product_id)
    db.close()
    assert product["config"]["core_keywords"] == ["travel pillow", "neck pillow"]
    assert product["config"]["own_variants"] == ["B0OWN12345"]


def test_frontend_settings_restore_rule_version_endpoint(monkeypatch, tmp_path):
    db, product_id = _bootstrap(monkeypatch, tmp_path)
    db.update_product_config(product_id, {"core_keywords": ["new keyword"]})
    from src.services.settings_service import save_config_version

    save_config_version(
        db,
        product_id,
        {"core_keywords": ["travel pillow"]},
        {"core_keywords": ["new keyword"]},
    )
    db.close()

    with TestClient(create_app()) as client:
        response = client.post(
            "/frontend/settings/rule-versions/restore",
            json={
                "product_id": product_id,
                "version": 1,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["ruleVersionCount"] >= 1


def test_frontend_settings_preview_rule_version_endpoint(monkeypatch, tmp_path):
    db, product_id = _bootstrap(monkeypatch, tmp_path)
    from src.services.settings_service import save_config_version

    save_config_version(
        db,
        product_id,
        {"core_keywords": ["travel pillow"]},
        {"core_keywords": ["neck pillow"], "competitor_asins": ["B0COMP12345"]},
    )
    db.close()

    with TestClient(create_app()) as client:
        response = client.get(
            f"/frontend/settings/rule-versions/1?product_id={product_id}"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["configEditor"]["coreKeywords"] == ["neck pillow"]
    assert "neck pillow" in body["diff"]["coreKeywords"]["added"]


# ── Audit HIGH-1: backup schema 校验单元测试 ────────────────────────────


def test_validate_backup_schema_rejects_non_dict():
    import pytest

    from src.services.settings_service import _validate_backup_schema

    with pytest.raises(ValueError, match="不是有效的 JSON 对象"):
        _validate_backup_schema("not a dict")
    with pytest.raises(ValueError, match="不是有效的 JSON 对象"):
        _validate_backup_schema([])


def test_validate_backup_schema_rejects_wrong_export_type():
    import pytest

    from src.services.settings_service import _validate_backup_schema

    with pytest.raises(ValueError, match="不是完整数据备份"):
        _validate_backup_schema({"export_type": "rule_config", "product": {}})


def test_validate_backup_schema_rejects_missing_product():
    import pytest

    from src.services.settings_service import _validate_backup_schema

    with pytest.raises(ValueError, match="product 字段"):
        _validate_backup_schema({"export_type": "full_backup"})
    with pytest.raises(ValueError, match="product 字段"):
        _validate_backup_schema({"export_type": "full_backup", "product": "wrong"})


def test_validate_backup_schema_rejects_list_with_wrong_type():
    import pytest

    from src.services.settings_service import _validate_backup_schema

    with pytest.raises(ValueError, match="campaigns 类型错误"):
        _validate_backup_schema(
            {
                "export_type": "full_backup",
                "product": {"name": "x"},
                "campaigns": "not a list",
            }
        )
    with pytest.raises(ValueError, match=r"search_terms\[0\] 类型错误"):
        _validate_backup_schema(
            {
                "export_type": "full_backup",
                "product": {"name": "x"},
                "search_terms": ["should be dict"],
            }
        )


def test_validate_backup_schema_rejects_missing_id():
    import pytest

    from src.services.settings_service import _validate_backup_schema

    with pytest.raises(ValueError, match=r"campaigns\[0\]\.id"):
        _validate_backup_schema(
            {
                "export_type": "full_backup",
                "product": {"name": "x"},
                "campaigns": [{"name": "无 id 的活动"}],
            }
        )
    with pytest.raises(ValueError, match=r"analysis_results\[0\]\.search_term_id"):
        _validate_backup_schema(
            {
                "export_type": "full_backup",
                "product": {"name": "x"},
                "analysis_results": [{"id": 1}],
            }
        )
    with pytest.raises(ValueError, match=r"action_plans\[0\]\.analysis_result_id"):
        _validate_backup_schema(
            {
                "export_type": "full_backup",
                "product": {"name": "x"},
                "action_plans": [{"action": "negate"}],
            }
        )


def test_validate_backup_schema_accepts_minimal_valid():
    """最小合法 backup（只有 export_type + product）不应 raise。"""
    from src.services.settings_service import _validate_backup_schema

    _validate_backup_schema({"export_type": "full_backup", "product": {}})
    _validate_backup_schema(
        {
            "export_type": "full_backup",
            "product": {},
            "campaigns": [],
            "search_terms": [],
            "analysis_results": [],
        }
    )


# ── restore_full_backup 端到端 round-trip 测试 ─────────────────────────


def _bootstrap_rich(monkeypatch, tmp_path):
    """构造一个 entity 多样化的产品，覆盖 restore 路径上 8 类表中的 6 类。

    返回 (db, product_id, expected_counts)。db 已 close 前调用方需重新打开。
    """
    legacy_db_path = tmp_path / "rich-app.db"
    monkeypatch.setenv("DATABASE_PATH", str(legacy_db_path))
    db = Database(str(legacy_db_path))
    db.init_schema()
    db.init_default_rules()

    product_id = db.create_product(
        name="圆枕产品",
        asin="B0RICH00001",
        category="Travel",
        config={
            "core_keywords": ["travel pillow"],
            "competitor_asins": ["B0COMP00001"],
        },
    )

    cid_auto = db.get_or_create_campaign(
        product_id=product_id, name="Auto Hub", match_type="auto"
    )
    cid_manual = db.get_or_create_campaign(
        product_id=product_id, name="Manual Exact", match_type="exact"
    )

    df = pd.DataFrame(
        [
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "impressions": 200,
                "clicks": 30,
                "ctr": 0.15,
                "spend": 22.5,
                "cpc": 0.75,
                "orders": 4,
                "sales": 96.0,
                "acos": 0.23,
                "roas": 4.27,
                "conversion_rate": 0.13,
                "report_date": "2026-04-15",
            },
            {
                "term": "neck pillow",
                "term_type": "keyword",
                "impressions": 80,
                "clicks": 8,
                "ctr": 0.10,
                "spend": 6.4,
                "cpc": 0.80,
                "orders": 1,
                "sales": 19.0,
                "acos": 0.34,
                "roas": 2.97,
                "conversion_rate": 0.13,
                "report_date": "2026-04-15",
            },
        ]
    )
    db.save_search_terms(df, cid_auto)

    df2 = pd.DataFrame(
        [
            {
                "term": "memory foam pillow",
                "term_type": "keyword",
                "impressions": 50,
                "clicks": 3,
                "ctr": 0.06,
                "spend": 2.4,
                "cpc": 0.80,
                "orders": 0,
                "sales": 0.0,
                "acos": 0.0,
                "roas": 0.0,
                "conversion_rate": 0.0,
                "report_date": "2026-04-15",
            },
        ]
    )
    db.save_search_terms(df2, cid_manual)

    db.save_analysis_result_by_term(
        product_id=product_id,
        term="travel pillow",
        triggered_rule="strong_core",
        suggested_action="加大投放",
        action_type="manual_increase",
        confidence=0.92,
        ai_reasoning="高 ROAS + 高转化",
    )
    db.save_analysis_result_by_term(
        product_id=product_id,
        term="memory foam pillow",
        triggered_rule="weak_low_conversion",
        suggested_action="加 negative",
        action_type="negative_keyword",
        confidence=0.81,
        ai_reasoning="低转化无订单",
    )

    db.upsert_manual_review(
        product_id=product_id,
        term="memory foam pillow",
        term_type="keyword",
        relevance="irrelevant",
        relevance_notes="同事审核确认无关",
        reviewed=True,
    )

    db.save_analysis_run_snapshot(
        product_id,
        [
            {
                "term": "travel pillow",
                "action_type": "manual_increase",
                "suggested_action": "加大投放",
                "spend": 22.5,
                "sales": 96.0,
            }
        ],
        run_source="manual",
        summary={"item_count": 1},
    )

    db.create_execution_batch(
        product_id=product_id,
        batch_type="manual",
        summary={
            "item_count": 1,
            "items": [
                {
                    "term": "travel pillow",
                    "suggested_action": "加大投放",
                    "action_type": "manual_increase",
                }
            ],
            "spend_total": 22.5,
            "sales_total": 96.0,
            "baseline_snapshot_id": None,
        },
        draft_note="冲量计划",
    )

    expected = {
        "campaigns": 2,
        "search_terms": 3,
        "analysis_results": 2,
        "manual_reviews": 1,
        "analysis_run_snapshots": 1,
        "execution_batches": 1,
    }
    return db, product_id, expected


def _count(db, table: str, product_id: int, *, filter_clause: str = "") -> int:
    """Helper · 数据库行数（按 product_id 直接或经 campaign 间接关联）。"""
    if table == "campaigns":
        sql = "SELECT COUNT(*) AS n FROM campaigns WHERE product_id = ?"
    elif table == "search_terms":
        sql = (
            "SELECT COUNT(*) AS n FROM search_terms st "
            "JOIN campaigns c ON st.campaign_id = c.id WHERE c.product_id = ?"
        )
    elif table == "analysis_results":
        sql = (
            "SELECT COUNT(*) AS n FROM analysis_results ar "
            "JOIN search_terms st ON ar.search_term_id = st.id "
            "JOIN campaigns c ON st.campaign_id = c.id WHERE c.product_id = ?"
        )
    elif table in ("manual_reviews", "execution_batches", "analysis_run_snapshots"):
        sql = f"SELECT COUNT(*) AS n FROM {table} WHERE product_id = ?"
    else:
        raise ValueError(f"unknown table: {table}")
    if filter_clause:
        sql = f"{sql} AND {filter_clause}"
    row = db.execute(sql, (product_id,)).fetchone()
    return int(row["n"])


def test_restore_full_backup_round_trip_as_new_product(monkeypatch, tmp_path):
    """完整 round-trip：build → JSON → restore 到新产品 → 6 类实体逐一比对。"""
    from src.services.settings_service import (
        build_full_backup_export_payload,
        restore_full_backup,
    )

    db, source_pid, expected = _bootstrap_rich(monkeypatch, tmp_path)
    payload = build_full_backup_export_payload(db, source_pid)
    backup_data = json.loads(payload["data"].decode("utf-8"))

    new_pid = restore_full_backup(
        db,
        backup_data,
        current_product_id=None,
        restore_as_new_product=True,
    )

    assert new_pid != source_pid

    # 新产品必须重建所有 6 类实体，数量与源一致
    for table, expected_count in expected.items():
        actual = _count(db, table, new_pid)
        assert actual == expected_count, (
            f"{table} round-trip 数量不符：期望 {expected_count}，实际 {actual}"
        )

    # 抽样核对内容：travel pillow 的 spend / 22.5
    row = db.execute(
        """
        SELECT st.term, st.spend
        FROM search_terms st
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ? AND st.term = ?
        """,
        (new_pid, "travel pillow"),
    ).fetchone()
    assert row is not None
    assert float(row["spend"]) == 22.5

    # 新产品名称带"恢复"后缀
    new_product = db.get_product(new_pid)
    assert new_product["name"].endswith("（恢复）")
    # 源产品 config 也应该过来
    assert "travel pillow" in new_product["config"].get("core_keywords", [])

    db.close()


def test_restore_full_backup_round_trip_overwrite(monkeypatch, tmp_path):
    """覆盖模式 round-trip：备份 → 用户改动 → restore 覆盖 → 验证恢复到备份状态。"""
    from src.services.settings_service import (
        build_full_backup_export_payload,
        restore_full_backup,
    )

    db, source_pid, expected = _bootstrap_rich(monkeypatch, tmp_path)
    payload = build_full_backup_export_payload(db, source_pid)
    backup_data = json.loads(payload["data"].decode("utf-8"))

    # 模拟用户在备份后改了配置 + 新增 1 条 manual_review
    db.update_product_config(source_pid, {"core_keywords": ["後續修改"]})
    db.upsert_manual_review(
        product_id=source_pid,
        term="新增的词",
        term_type="keyword",
        relevance="strong_core",
        reviewed=True,
    )

    # 现在 restore 覆盖模式
    restored_pid = restore_full_backup(
        db,
        backup_data,
        current_product_id=source_pid,
        restore_as_new_product=False,
    )
    assert restored_pid == source_pid  # 覆盖模式 PID 不变

    # 数量回到备份状态（用户后改的不在内）
    for table, expected_count in expected.items():
        actual = _count(db, table, restored_pid)
        assert actual == expected_count, (
            f"{table} overwrite round-trip 数量不符：期望 {expected_count}，实际 {actual}"
        )

    # config 也回到备份状态（不再有"後續修改"）
    product = db.get_product(restored_pid)
    assert product["config"].get("core_keywords") == ["travel pillow"]
    assert product["config"].get("competitor_asins") == ["B0COMP00001"]

    db.close()
