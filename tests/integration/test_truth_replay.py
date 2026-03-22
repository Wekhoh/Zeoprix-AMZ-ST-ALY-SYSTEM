"""集成测试：已审核真相回放与命名策略组合。"""

from __future__ import annotations

import pandas as pd

from src.analysis.asin_analyzer import ASINAnalyzer
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


class TestTruthFirstViews:
    def test_truth_first_action_buckets_and_pending_stats(
        self, db, product_id, tmp_path
    ):
        from src.analysis.truth_replay import (
            get_truth_first_action_buckets,
            get_truth_first_pending_stats,
            seed_truth_workbooks,
        )

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
        db.save_search_terms(
            _make_search_term_rows("flight pillow", clicks=9, spend=19.0),
            blk_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows(
                "B0COMP1234", term_type="asin", clicks=14, spend=32.0
            ),
            blk_campaign_id,
        )

        db.upsert_manual_review(
            product_id=product_id,
            term="travel pillow",
            term_type="keyword",
            relevance="pending",
            reviewed=False,
        )
        db.upsert_manual_review(
            product_id=product_id,
            term="flight pillow",
            term_type="keyword",
            relevance="pending",
            reviewed=False,
        )
        db.upsert_manual_review(
            product_id=product_id,
            term="B0COMP1234",
            term_type="asin",
            relevance="pending",
            reviewed=False,
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
                        "action_matrix": "[blk]手动精准+先不否",
                        "campaign_summary": "[blk]12clk/$28",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "BLK 保留并拉手动精准",
                    },
                    {
                        "term_type": "关键词",
                        "relevance": "不相关",
                        "keyword": "flight pillow",
                        "manual_action": None,
                        "auto_action": "否定词组",
                        "negate_keyword": None,
                        "negate_asin": None,
                        "rule_trigger": "用户标记(直接否词组)",
                        "action_matrix": "[blk]Neg Phrase",
                        "campaign_summary": "[blk]9clk/$19",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "flight pillow 直接否定词组",
                    },
                    {
                        "term_type": "ASIN",
                        "relevance": "不可竞争",
                        "keyword": "B0COMP1234",
                        "manual_action": None,
                        "auto_action": "直接否",
                        "negate_keyword": None,
                        "negate_asin": "Neg Product",
                        "rule_trigger": "用户标记(直接否ASIN)",
                        "action_matrix": "[blk]Neg Product",
                        "campaign_summary": "[blk]14clk/$32",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "竞品不可竞争，直接否定",
                    },
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
                        "campaign_summary": "[dbl]12clk/$28",
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

        buckets = get_truth_first_action_buckets(db, product_id)
        stats = get_truth_first_pending_stats(db, product_id)

        assert buckets is not None
        assert [item["term"] for item in buckets["negative_keyword_exact"]] == [
            "travel pillow"
        ]
        assert [item["term"] for item in buckets["negative_keyword_phrase"]] == [
            "flight pillow"
        ]
        assert [item["term"] for item in buckets["negative_asin"]] == ["B0COMP1234"]
        assert [item["term"] for item in buckets["manual_keywords"]] == [
            "travel pillow"
        ]
        assert buckets["manual_products"] == []

        assert stats == {
            "negative_count": 3,
            "manual_count": 1,
            "ai_pending_count": 0,
            "review_pending_count": 0,
        }

    def test_truth_first_home_rule_stats_uses_truth_distribution(
        self, db, product_id, tmp_path
    ):
        from src.analysis.truth_replay import seed_truth_workbooks
        from src.ui.pages.home import _build_overview_chart, get_rule_stats

        blk_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="BLK-home-campaign",
            match_type="auto",
        )
        dbl_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="DBL-home-campaign",
            match_type="auto",
        )

        db.save_search_terms(
            _make_search_term_rows("travel pillow", orders=1, clicks=12, spend=20.0),
            blk_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows("travel pillow", clicks=15, spend=30.0),
            dbl_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows("flight pillow", clicks=9, spend=19.0),
            blk_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows("B0COMP1234", term_type="asin", clicks=14, spend=32.0),
            blk_campaign_id,
        )

        aggregate_workbook = tmp_path / "home_truth.xlsx"
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
                        "campaign_summary": "[blk]12clk/$20",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "BLK 保留并拉手动精准",
                    },
                    {
                        "term_type": "关键词",
                        "relevance": "不相关",
                        "keyword": "flight pillow",
                        "manual_action": None,
                        "auto_action": "否定词组",
                        "negate_keyword": None,
                        "negate_asin": None,
                        "rule_trigger": "用户标记(词组否定)",
                        "action_matrix": "[blk]Neg Phrase",
                        "campaign_summary": "[blk]9clk/$19",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "明显不相关",
                    },
                    {
                        "term_type": "ASIN",
                        "relevance": "不可竞争",
                        "keyword": "B0COMP1234",
                        "manual_action": None,
                        "auto_action": "直接否",
                        "negate_keyword": None,
                        "negate_asin": "Neg Product",
                        "rule_trigger": "用户标记(ASIN否定)",
                        "action_matrix": "[blk]Neg Product",
                        "campaign_summary": "[blk]14clk/$32",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "竞品不可竞争",
                    },
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
                        "campaign_summary": "[dbl]15clk/$30",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "DBL 手动精准但自动直接否",
                    }
                ],
            },
        )

        seed_truth_workbooks(
            db=db,
            product_id=product_id,
            aggregate_workbook_path=aggregate_workbook,
        )

        rule_stats = get_rule_stats(db, product_id)
        assert rule_stats == {
            "继续观察-关键词": 0,
            "继续观察-ASIN": 0,
            "手动精准-关键词": 0,
            "手动商品定位-ASIN": 0,
            "否定精准-关键词": 0,
            "否定词组-关键词": 1,
            "否定ASIN": 1,
            "跨ASIN分歧": 1,
        }

        chart_spec = _build_overview_chart(
            {key: value for key, value in rule_stats.items() if value > 0}
        ).to_dict()
        assert chart_spec["encoding"]["x"]["field"] == "分类"
        assert chart_spec["encoding"]["tooltip"][0]["field"] == "分类"

    def test_truth_first_campaign_rows_only_include_campaign_truth(
        self, db, product_id, tmp_path
    ):
        from src.analysis.truth_replay import (
            get_truth_first_campaign_rows,
            seed_truth_workbooks,
        )

        keep_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="BLK-keep-campaign",
            match_type="auto",
        )
        neg_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="BLK-neg-campaign",
            match_type="auto",
        )
        unreviewed_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="BLK-unreviewed-campaign",
            match_type="auto",
        )

        db.save_search_terms(
            _make_search_term_rows("travel pillow", orders=1, clicks=14, spend=22.0),
            keep_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows("travel pillow", clicks=16, spend=35.0),
            neg_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows("memory foam pillow", clicks=12, spend=18.0),
            unreviewed_campaign_id,
        )

        campaign_workbook = tmp_path / "campaign_truth.xlsx"
        _write_campaign_truth_workbook(
            campaign_workbook,
            [
                {
                    "ASIN": "BLK",
                    "campaign_name": "BLK-keep-campaign",
                    "keyword": "travel pillow",
                    "plan": "手动精准，自动先不否",
                },
                {
                    "ASIN": "BLK",
                    "campaign_name": "BLK-neg-campaign",
                    "keyword": "travel pillow",
                    "plan": "自动直接否定精准",
                },
            ],
        )

        seed_truth_workbooks(
            db=db,
            product_id=product_id,
            campaign_workbook_path=campaign_workbook,
        )

        campaign_rows = get_truth_first_campaign_rows(db, product_id)
        assert campaign_rows is not None
        assert len(campaign_rows) == 2
        assert {row["campaign_name"] for row in campaign_rows} == {
            "BLK-keep-campaign",
            "BLK-neg-campaign",
        }
        assert {row["auto_action"] for row in campaign_rows} == {"keep", "negate"}
        assert {row["term"] for row in campaign_rows} == {"travel pillow"}

    def test_truth_first_summary_rows_fold_cross_asin_conflicts(
        self, db, product_id, tmp_path
    ):
        from src.analysis.truth_replay import (
            get_truth_first_summary_rows,
            seed_truth_workbooks,
        )

        blk_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="BLK-summary-campaign",
            match_type="auto",
        )
        dbl_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="DBL-summary-campaign",
            match_type="auto",
        )

        db.save_search_terms(_make_search_term_rows("travel pillow"), blk_campaign_id)
        db.save_search_terms(_make_search_term_rows("travel pillow"), dbl_campaign_id)
        db.save_search_terms(
            _make_search_term_rows("flight pillow", clicks=9, spend=19.0),
            blk_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows(
                "B0COMP1234", term_type="asin", clicks=14, spend=32.0
            ),
            blk_campaign_id,
        )

        aggregate_workbook = tmp_path / "summary_truth.xlsx"
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
                    },
                    {
                        "term_type": "关键词",
                        "relevance": "不相关",
                        "keyword": "flight pillow",
                        "manual_action": None,
                        "auto_action": "否定词组",
                        "negate_keyword": None,
                        "negate_asin": None,
                        "rule_trigger": "用户标记(词组否定)",
                        "action_matrix": "[blk]Neg Phrase",
                        "campaign_summary": "[blk]9clk/$19",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "明显不相关",
                    },
                    {
                        "term_type": "ASIN",
                        "relevance": "不可竞争",
                        "keyword": "B0COMP1234",
                        "manual_action": None,
                        "auto_action": "直接否",
                        "negate_keyword": None,
                        "negate_asin": "Neg Product",
                        "rule_trigger": "用户标记(ASIN否定)",
                        "action_matrix": "[blk]Neg Product",
                        "campaign_summary": "[blk]14clk/$32",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "竞品不可竞争",
                    },
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
                        "campaign_summary": "[dbl]18clk/$28",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "DBL 手动精准但自动直接否",
                    }
                ],
            },
        )

        seed_truth_workbooks(
            db=db,
            product_id=product_id,
            aggregate_workbook_path=aggregate_workbook,
        )

        summary_rows = get_truth_first_summary_rows(db, product_id)
        assert summary_rows is not None
        assert len(summary_rows) == 3

        rows_by_term = {row["term"]: row for row in summary_rows}

        travel_pillow = rows_by_term["travel pillow"]
        assert travel_pillow["action_type"] == "conflict"
        assert travel_pillow["suggested_action"] == "跨ASIN分歧"
        assert travel_pillow["asin_identifiers"] == ["BLK", "DBL"]
        assert "BLK: 手动精准" in travel_pillow["action_detail"]
        assert "DBL: 手动精准" in travel_pillow["action_detail"]

        flight_pillow = rows_by_term["flight pillow"]
        assert flight_pillow["action_type"] == "negative_phrase"
        assert flight_pillow["suggested_action"] == "否定词组"

        competitor_asin = rows_by_term["B0COMP1234"]
        assert competitor_asin["term_type"] == "asin"
        assert competitor_asin["action_type"] == "negative_exact"

    def test_asin_analyzer_uses_truth_for_distribution_and_conflicts(
        self, db, product_id, tmp_path
    ):
        from src.analysis.truth_replay import seed_truth_workbooks

        blk_keep_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="BLK-keep-campaign",
            match_type="auto",
        )
        blk_neg_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="BLK-neg-campaign",
            match_type="auto",
        )
        dbl_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="DBL-neg-campaign",
            match_type="auto",
        )

        db.save_search_terms(
            _make_search_term_rows("travel pillow", orders=1, clicks=14, spend=22.0),
            blk_keep_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows("travel pillow", clicks=16, spend=35.0),
            blk_neg_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows("flight pillow", clicks=9, spend=19.0),
            dbl_campaign_id,
        )

        campaign_workbook = tmp_path / "asin_campaign_truth.xlsx"
        _write_campaign_truth_workbook(
            campaign_workbook,
            [
                {
                    "ASIN": "BLK",
                    "campaign_name": "BLK-keep-campaign",
                    "keyword": "travel pillow",
                    "plan": "手动精准，自动先不否",
                },
                {
                    "ASIN": "BLK",
                    "campaign_name": "BLK-neg-campaign",
                    "keyword": "travel pillow",
                    "plan": "自动直接否定精准",
                },
            ],
        )

        aggregate_workbook = tmp_path / "asin_aggregate_truth.xlsx"
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
                        "campaign_summary": "[blk]14clk/$22 | [blk-neg]16clk/$35",
                        "campaign_conflict": "存在活动分歧",
                        "decision_source": "用户标记",
                        "conflict": "BLK 两个活动动作不同",
                        "original_notes": "BLK 存在 keep/neg 冲突",
                    }
                ],
                "DBL汇总": [
                    {
                        "term_type": "关键词",
                        "relevance": "不相关",
                        "keyword": "flight pillow",
                        "manual_action": None,
                        "auto_action": "否定词组",
                        "negate_keyword": None,
                        "negate_asin": None,
                        "rule_trigger": "用户标记(词组否定)",
                        "action_matrix": "[dbl]Neg Phrase",
                        "campaign_summary": "[dbl]9clk/$19",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "明显不相关",
                    }
                ],
            },
        )

        seed_truth_workbooks(
            db=db,
            product_id=product_id,
            campaign_workbook_path=campaign_workbook,
            aggregate_workbook_path=aggregate_workbook,
        )

        analyzer = ASINAnalyzer(db)

        distribution = analyzer.get_keyword_distribution(product_id)
        assert distribution["BLK"]["手动精准"] == 1
        assert distribution["DBL"]["否定词组"] == 1

        conflicts = analyzer.detect_conflicts(product_id, "BLK")
        assert not conflicts.empty
        assert conflicts.iloc[0]["term"] == "travel pillow"
        assert conflicts.iloc[0]["severity"] == "严重"

    def test_truth_first_action_exports_use_truth_buckets(
        self, db, product_id, tmp_path
    ):
        from src.analysis.truth_replay import seed_truth_workbooks
        from src.ui.pages.actions import _get_export_results

        blk_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="BLK-export-campaign",
            match_type="auto",
        )
        dbl_campaign_id = db.get_or_create_campaign(
            product_id=product_id,
            name="DBL-export-campaign",
            match_type="auto",
        )

        db.save_search_terms(
            _make_search_term_rows("travel pillow", orders=1, clicks=12, spend=20.0),
            blk_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows("travel pillow", clicks=15, spend=30.0),
            dbl_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows("flight pillow", clicks=9, spend=19.0),
            blk_campaign_id,
        )
        db.save_search_terms(
            _make_search_term_rows("B0COMP1234", term_type="asin", clicks=14, spend=32.0),
            blk_campaign_id,
        )

        aggregate_workbook = tmp_path / "export_truth.xlsx"
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
                        "campaign_summary": "[blk]12clk/$20",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "BLK 保留并拉手动精准",
                    },
                    {
                        "term_type": "关键词",
                        "relevance": "不相关",
                        "keyword": "flight pillow",
                        "manual_action": None,
                        "auto_action": "否定词组",
                        "negate_keyword": None,
                        "negate_asin": None,
                        "rule_trigger": "用户标记(直接否词组)",
                        "action_matrix": "[blk]Neg Phrase",
                        "campaign_summary": "[blk]9clk/$19",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "flight pillow 直接否定词组",
                    },
                    {
                        "term_type": "ASIN",
                        "relevance": "不可竞争",
                        "keyword": "B0COMP1234",
                        "manual_action": None,
                        "auto_action": "直接否",
                        "negate_keyword": None,
                        "negate_asin": "Neg Product",
                        "rule_trigger": "用户标记(直接否ASIN)",
                        "action_matrix": "[blk]Neg Product",
                        "campaign_summary": "[blk]14clk/$32",
                        "campaign_conflict": None,
                        "decision_source": "用户标记",
                        "conflict": None,
                        "original_notes": "竞品不可竞争，直接否定",
                    },
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
                        "campaign_summary": "[dbl]15clk/$30",
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

        negative_results = _get_export_results(db, product_id, export_kind="negative")
        manual_results = _get_export_results(db, product_id, export_kind="manual")

        assert {(item.term, item.action_type) for item in negative_results} == {
            ("travel pillow", "manual_exact_with_neg"),
            ("flight pillow", "negative_phrase"),
            ("B0COMP1234", "negative_exact"),
        }
        assert len(manual_results) == 1
        assert manual_results[0].term == "travel pillow"
        assert manual_results[0].action_type.startswith("manual_exact")
