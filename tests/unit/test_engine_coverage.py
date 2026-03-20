"""
engine.py 覆盖率提升测试
针对未覆盖的分支和方法
"""

import pandas as pd
import pytest

from src.data.db import Database
from src.data.models import ActionType, RelevanceLevel
from src.rules.engine import (
    AnalysisResult,
    ASINAnalysisResult,
    CampaignAnalysisResult,
    Confidence,
    RuleEngine,
    analyze_search_terms_by_asin,
)


@pytest.fixture
def db_engine(tmp_path):
    """创建带默认规则的数据库和引擎"""
    db = Database(str(tmp_path / "test.db"))
    db.init_schema()
    db.init_default_rules()
    pid = db.create_product(name="test", asin="B0TEST00001", category="test")
    db.update_product_config(
        pid,
        {
            "core_keywords": ["travel pillow"],
            "own_asins": ["B0TEST00001"],
            "own_variants": ["B0VARIANT01"],
            "keyword_libraries": {
                "generic_keywords": ["pillow"],
                "irrelevant_keywords": ["massager"],
                "weak_category_keywords": ["cushion"],
                "car_keywords": ["car"],
            },
            "thresholds": {
                "spend_threshold": 10.0,
                "min_clicks_for_analysis": 20,
                "good_cvr": 0.10,
            },
        },
    )
    engine = RuleEngine(db, pid)
    yield db, engine, pid
    db.close()


class TestMatchRuleConditions:
    """测试 _match_rule 的各种条件分支"""

    def test_clicks_max_condition(self, db_engine):
        """测试 clicks_max 条件"""
        _, engine, _ = db_engine
        row = pd.Series({"term": "test", "term_type": "keyword", "total_clicks": 50})
        rule = {
            "name": "test",
            "rule_type": "keyword",
            "conditions": {"clicks_max": 30},
        }
        assert not engine._match_rule(row, rule)

    def test_acos_min_condition(self, db_engine):
        """测试 acos_min 条件"""
        _, engine, _ = db_engine
        row = pd.Series(
            {
                "term": "test",
                "term_type": "keyword",
                "acos": 0.1,
                "total_clicks": 10,
                "total_spend": 5,
                "total_orders": 1,
            }
        )
        rule = {
            "name": "test",
            "rule_type": "keyword",
            "conditions": {"acos_min": 0.3},
        }
        assert not engine._match_rule(row, rule)

    def test_cvr_conditions(self, db_engine):
        """测试 cvr_min/cvr_max 条件"""
        _, engine, _ = db_engine
        row = pd.Series(
            {
                "term": "test",
                "term_type": "keyword",
                "total_clicks": 100,
                "total_orders": 5,
                "total_spend": 50,
                "conversion_rate": 0.05,
            }
        )
        # cvr_min 不满足
        rule = {"name": "t", "rule_type": "keyword", "conditions": {"cvr_min": 0.1}}
        assert not engine._match_rule(row, rule)

        # cvr_max 不满足
        rule2 = {"name": "t", "rule_type": "keyword", "conditions": {"cvr_max": 0.01}}
        assert not engine._match_rule(row, rule2)

    def test_impressions_conditions(self, db_engine):
        """测试 impressions_min/max 条件"""
        _, engine, _ = db_engine
        row = pd.Series(
            {"term": "test", "term_type": "keyword", "total_impressions": 500}
        )
        rule = {
            "name": "t",
            "rule_type": "keyword",
            "conditions": {"impressions_min": 1000},
        }
        assert not engine._match_rule(row, rule)

        rule2 = {
            "name": "t",
            "rule_type": "keyword",
            "conditions": {"impressions_max": 100},
        }
        assert not engine._match_rule(row, rule2)

    def test_ctr_conditions(self, db_engine):
        """测试 ctr 条件"""
        _, engine, _ = db_engine
        row = pd.Series(
            {
                "term": "test",
                "term_type": "keyword",
                "total_impressions": 1000,
                "total_clicks": 50,
                "ctr": 0.05,
            }
        )
        rule = {"name": "t", "rule_type": "keyword", "conditions": {"ctr_min": 0.1}}
        assert not engine._match_rule(row, rule)

    def test_cpc_conditions(self, db_engine):
        """测试 cpc 条件"""
        _, engine, _ = db_engine
        row = pd.Series(
            {
                "term": "test",
                "term_type": "keyword",
                "total_clicks": 10,
                "total_spend": 5.0,
                "cpc": 0.5,
            }
        )
        rule = {"name": "t", "rule_type": "keyword", "conditions": {"cpc_min": 1.0}}
        assert not engine._match_rule(row, rule)

    def test_sales_conditions(self, db_engine):
        """测试 sales 条件"""
        _, engine, _ = db_engine
        row = pd.Series({"term": "test", "term_type": "keyword", "total_sales": 50.0})
        rule = {"name": "t", "rule_type": "keyword", "conditions": {"sales_min": 100}}
        assert not engine._match_rule(row, rule)

    def test_roas_conditions(self, db_engine):
        """测试 roas 条件"""
        _, engine, _ = db_engine
        row = pd.Series(
            {
                "term": "test",
                "term_type": "keyword",
                "total_spend": 50.0,
                "total_sales": 100.0,
                "roas": 2.0,
            }
        )
        rule = {"name": "t", "rule_type": "keyword", "conditions": {"roas_min": 3.0}}
        assert not engine._match_rule(row, rule)

    def test_own_variant_condition(self, db_engine):
        """测试 is_own_variant 条件"""
        _, engine, _ = db_engine
        # 非自有变体
        row = pd.Series({"term": "B0NOTOURS01", "term_type": "asin"})
        rule = {
            "name": "t",
            "rule_type": "asin",
            "conditions": {"is_own_variant": True},
        }
        assert not engine._match_rule(row, rule)

        # 自有变体
        row2 = pd.Series({"term": "B0VARIANT01", "term_type": "asin"})
        assert engine._match_rule(row2, rule)

    def test_empty_conditions_skip(self, db_engine):
        """测试空条件规则不匹配"""
        _, engine, _ = db_engine
        row = pd.Series({"term": "test", "term_type": "keyword"})
        rule = {"name": "empty", "rule_type": "keyword", "conditions": {}}
        assert not engine._match_rule(row, rule)


class TestGetActionType:
    """测试 _get_action_type 的各种分支"""

    def test_manual_product_type(self, db_engine):
        _, engine, _ = db_engine
        assert engine._get_action_type("手动商品定位") == ActionType.MANUAL_PRODUCT

    def test_manual_product_english(self, db_engine):
        _, engine, _ = db_engine
        assert engine._get_action_type("manual_product") == ActionType.MANUAL_PRODUCT

    def test_continue_observe(self, db_engine):
        _, engine, _ = db_engine
        assert engine._get_action_type("继续观察") == ActionType.CONTINUE_OBSERVE

    def test_evaluate_type(self, db_engine):
        _, engine, _ = db_engine
        assert engine._get_action_type("评估") == ActionType.EVALUATE

    def test_unknown_action(self, db_engine):
        _, engine, _ = db_engine
        assert engine._get_action_type("unknown_xyz") == "other"

    def test_manual_default(self, db_engine):
        _, engine, _ = db_engine
        assert engine._get_action_type("手动") == ActionType.MANUAL_EXACT


class TestHelperMethods:
    """测试辅助方法"""

    def test_get_manual_product_keywords(self, db_engine):
        _, engine, _ = db_engine
        results = [
            AnalysisResult(
                term="B0TEST",
                term_type="asin",
                triggered_rule="t",
                suggested_action="手动商品定位",
                action_type=ActionType.MANUAL_PRODUCT,
            ),
            AnalysisResult(
                term="word",
                term_type="keyword",
                triggered_rule="t",
                suggested_action="否定",
                action_type=ActionType.NEGATIVE_EXACT,
            ),
        ]
        manual_products = engine.get_manual_product_keywords(results)
        assert len(manual_products) == 1
        assert manual_products[0].term == "B0TEST"

    def test_get_negative_phrase_keywords(self, db_engine):
        _, engine, _ = db_engine
        results = [
            AnalysisResult(
                term="weak word",
                term_type="keyword",
                triggered_rule="t",
                suggested_action="否定词组",
                action_type=ActionType.NEGATIVE_PHRASE,
            ),
        ]
        phrases = engine.get_negative_phrase_keywords(results)
        assert len(phrases) == 1

    def test_get_manual_exact_keywords(self, db_engine):
        _, engine, _ = db_engine
        results = [
            AnalysisResult(
                term="good word",
                term_type="keyword",
                triggered_rule="t",
                suggested_action="手动精准",
                action_type=ActionType.MANUAL_EXACT,
            ),
        ]
        exact = engine.get_manual_exact_keywords(results)
        assert len(exact) == 1
