"""集成测试：已审核真相回放与命名策略组合。"""

from __future__ import annotations

import pandas as pd

from src.rules.engine import (
    analyze_search_terms_by_asin,
    analyze_search_terms_by_campaign,
)


def _make_search_term_rows(
    term: str,
    *,
    term_type: str = "keyword",
    clicks: int | None = None,
    spend: float | None = None,
    orders: int = 0,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "term": term,
                "term_type": term_type,
                "impressions": 1000,
                "clicks": clicks if clicks is not None else (12 if term_type == "asin" else 18),
                "ctr": 0.02,
                "spend": spend if spend is not None else 28.0,
                "cpc": 1.55,
                "orders": orders,
                "sales": 0.0,
                "acos": 0.0,
                "roas": 0.0,
                "conversion_rate": 0.0,
                "report_date": "2026-03-21",
            }
        ]
    )


def _write_campaign_truth_workbook(path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_excel(path, index=False)


def _write_aggregate_truth_workbook(path, sheets: dict[str, list[dict]]) -> None:
    with pd.ExcelWriter(path) as writer:
        for sheet_name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name, index=False)


class TestTruthReplay:
    def test_imported_aggregate_truth_overrides_term_analysis(
        self, db, product_id, campaign_id, tmp_path
    ):
        from src.analysis.truth_replay import seed_truth_workbooks

        db.save_search_terms(
            _make_search_term_rows("synthetic replay term", clicks=2, spend=3.0),
            campaign_id,
        )

        before = {
            (item.asin_identifier, item.term): item
            for item in analyze_search_terms_by_asin(db, product_id)
        }
        assert before[("BLK", "synthetic replay term")].action_type != "negative_exact"

        aggregate_workbook = tmp_path / "aggregate_truth.xlsx"
        _write_aggregate_truth_workbook(
            aggregate_workbook,
            {
                "BLK汇总": [
                    {
                        "term_type": "关键词",
                        "relevance": "强相关核心词",
                        "keyword": "synthetic replay term",
                        "manual_action": None,
                        "auto_action": "直接否",
                        "negate_keyword": "Neg Exact",
                        "negate_asin": None,
                        "rule_trigger": "人工已审核",
                        "action_matrix": "[synthetic]Neg Exact",
                        "campaign_summary": "[synthetic]18clk/$28",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "已人工审核，直接否定精准",
                    }
                ]
            },
        )

        imported = seed_truth_workbooks(
            db=db,
            product_id=product_id,
            aggregate_workbook_path=aggregate_workbook,
        )
        assert imported["aggregate_rows"] == 1

        after = {
            (item.asin_identifier, item.term): item
            for item in analyze_search_terms_by_asin(db, product_id)
        }
        result = after[("BLK", "synthetic replay term")]
        assert result.action_type == "negative_exact"
        assert result.suggested_action == "否定精准"
        assert result.triggered_rule == "人工已审核回放"
        assert result.data["truth_replay"]["review_source"] == "aggregate_truth"

    def test_campaign_truth_override_has_priority_over_global_truth(
        self, db, product_id, campaign_id, tmp_path
    ):
        from src.analysis.truth_replay import seed_truth_workbooks

        db.save_search_terms(_make_search_term_rows("travel pillow"), campaign_id)

        campaign_workbook = tmp_path / "campaign_truth.xlsx"
        _write_campaign_truth_workbook(
            campaign_workbook,
            [
                {
                    "ASIN": "BLK",
                    "campaign_name": "BLK-Auto-Broad",
                    "keyword": "travel pillow",
                    "plan": "明显不相关，直接否定词组",
                }
            ],
        )

        aggregate_workbook = tmp_path / "aggregate_truth.xlsx"
        _write_aggregate_truth_workbook(
            aggregate_workbook,
            {
                "BLK汇总": [
                    {
                        "term_type": "关键词",
                        "relevance": "强相关核心词",
                        "keyword": "travel pillow",
                        "manual_action": "手动精准",
                        "auto_action": "先不否",
                        "negate_keyword": None,
                        "negate_asin": None,
                        "rule_trigger": "用户标记(先不否)",
                        "action_matrix": "[1.2bid]手动精准+先不否",
                        "campaign_summary": "[1.2bid]18clk/$28",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "先做手动精准，自动先不否",
                    }
                ]
            },
        )

        imported = seed_truth_workbooks(
            db=db,
            product_id=product_id,
            campaign_workbook_path=campaign_workbook,
            aggregate_workbook_path=aggregate_workbook,
        )
        assert imported["campaign_rows"] == 1
        assert imported["aggregate_rows"] == 1

        asin_results = analyze_search_terms_by_asin(db, product_id)
        asin_result = next(
            item
            for item in asin_results
            if item.term == "travel pillow" and item.asin_identifier == "BLK"
        )
        assert asin_result.action_type == "manual_exact_no_neg"

        campaign_results = analyze_search_terms_by_campaign(db, product_id)
        campaign_result = next(
            item
            for item in campaign_results
            if item.term == "travel pillow" and item.campaign_id == campaign_id
        )
        assert campaign_result.action_type == "negative_phrase"
        assert campaign_result.suggested_action == "否定词组"
        assert campaign_result.auto_action == "negate"

    def test_aggregate_truth_can_distinguish_same_term_across_asin_identifiers(
        self, db, product_id, tmp_path
    ):
        from src.analysis.truth_replay import seed_truth_workbooks

        blk_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="BLK-test-campaign",
            match_type="auto",
        )
        dbl_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="DBL-test-campaign",
            match_type="auto",
        )

        db.save_search_terms(_make_search_term_rows("travel pillow"), blk_campaign_id)
        db.save_search_terms(_make_search_term_rows("travel pillow"), dbl_campaign_id)

        aggregate_workbook = tmp_path / "aggregate_truth.xlsx"
        _write_aggregate_truth_workbook(
            aggregate_workbook,
            {
                "BLK汇总": [
                    {
                        "term_type": "关键词",
                        "relevance": "强相关核心词",
                        "keyword": "travel pillow",
                        "manual_action": "手动精准",
                        "auto_action": "先不否",
                        "negate_keyword": None,
                        "negate_asin": None,
                        "rule_trigger": "用户标记(先不否)",
                        "action_matrix": "[blk]手动精准+先不否",
                        "campaign_summary": "[blk]18clk/$28",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "BLK 保留并拉手动精准",
                    }
                ],
                "DBL汇总": [
                    {
                        "term_type": "关键词",
                        "relevance": "强相关核心词",
                        "keyword": "travel pillow",
                        "manual_action": "手动精准",
                        "auto_action": "直接否",
                        "negate_keyword": "Neg Exact",
                        "negate_asin": None,
                        "rule_trigger": "用户标记(直接否)",
                        "action_matrix": "[dbl]手动精准+Neg Exact",
                        "campaign_summary": "[dbl]25clk/$40",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "DBL 直接否自动，手动精准单独测",
                    }
                ],
            },
        )

        seed_truth_workbooks(
            db=db,
            product_id=product_id,
            aggregate_workbook_path=aggregate_workbook,
        )

        asin_results = analyze_search_terms_by_asin(db, product_id)
        blk_result = next(
            item
            for item in asin_results
            if item.term == "travel pillow" and item.asin_identifier == "BLK"
        )
        dbl_result = next(
            item
            for item in asin_results
            if item.term == "travel pillow" and item.asin_identifier == "DBL"
        )

        assert blk_result.action_type == "manual_exact_no_neg"
        assert dbl_result.action_type == "manual_exact_with_neg"


class TestStrategyProfiles:
    def test_strategy_profile_can_be_saved_and_applied_to_other_product(self, db):
        source_product_id = db.create_product(
            name="源产品",
            asin="B0SOURCE123",
            config={
                "core_keywords": ["travel pillow", "neck pillow"],
                "keyword_libraries": {"generic_keywords": ["pillow"]},
                "thresholds": {"min_clicks_for_analysis": 20},
            },
        )
        target_product_id = db.create_product(
            name="目标产品",
            asin="B0TARGET123",
            config={"core_keywords": ["old keyword"]},
        )

        profile_id = db.save_strategy_profile(
            name="新品期-精准流量优先-v1",
            config_snapshot=db.get_product(source_product_id)["config"],
            lifecycle="launch",
            goal="precision_traffic",
            notes="truth replay calibrated",
            source_product_id=source_product_id,
        )
        assert profile_id > 0

        db.apply_strategy_profile(
            product_id=target_product_id,
            profile_name="新品期-精准流量优先-v1",
        )

        target_config = db.get_product(target_product_id)["config"]
        assert target_config["core_keywords"] == ["travel pillow", "neck pillow"]
        assert target_config["thresholds"]["min_clicks_for_analysis"] == 20

        profile = db.get_strategy_profile(name="新品期-精准流量优先-v1")
        assert profile["goal"] == "precision_traffic"

        version_count = db.execute(
            "SELECT COUNT(*) FROM rule_versions WHERE product_id = ?",
            (target_product_id,),
        ).fetchone()[0]
        assert version_count == 1
