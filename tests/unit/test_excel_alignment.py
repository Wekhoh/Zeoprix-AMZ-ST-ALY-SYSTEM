"""
测试Excel对齐 - 验证规则引擎是否正确处理用户Excel中的107条决策
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock

from src.rules.engine import RuleEngine
from src.data.models import ActionType, RelevanceLevel


class TestExcelKeywordAlignment:
    """测试Excel关键词决策对齐"""

    @pytest.fixture
    def mock_db(self):
        """Mock database with default rules"""
        db = MagicMock()
        db.get_rules.return_value = [
            # Rule #2: 弱相关类目词 -> 否定词组
            {
                "name": "弱相关类目词",
                "rule_type": "keyword",
                "conditions": {"relevance": "weak"},
                "action": "否定词组",
                "priority": 6,
            },
            # Rule #3: 太泛的词 -> 否定精准
            {
                "name": "太泛的词",
                "rule_type": "keyword",
                "conditions": {"relevance": "generic"},
                "action": "否定精准",
                "priority": 7,
            },
            # Rule #4: 汽车相关词 -> 否定精准
            {
                "name": "汽车相关词",
                "rule_type": "keyword",
                "conditions": {"relevance": "car"},
                "action": "否定精准",
                "priority": 8,
            },
            # Rule #5: 高花费零转化 -> 否定精准
            {
                "name": "高花费零转化",
                "rule_type": "keyword",
                "conditions": {"spend_min": 10.0, "orders_max": 0},
                "action": "否定精准",
                "priority": 10,
            },
        ]
        db.get_product.return_value = {
            "config": {
                "keyword_libraries": {
                    "weak_category_keywords": [
                        "massager",
                        "blanket",
                        "stuffable",
                        "brace",
                    ],
                    "generic_keywords": ["pillows", "pillow", "neck", "home"],
                    "car_keywords": ["car"],
                    "irrelevant_keywords": ["microbead", "cover", "airplane"],
                },
                "own_variants": ["B0FCSM9THX"],
                "thresholds": {
                    "min_clicks_for_analysis": 20,
                    "min_clicks_for_asin_neg": 6,
                    "high_spend_no_order": 20.0,
                    "good_cvr": 0.10,
                    "bad_cvr": 0.05,
                },
            }
        }
        # v2.0: 人工审核相关性接口返回None，回退到自动检测
        db.get_manual_review_relevance.return_value = None
        return db

    def test_weak_category_massager_phrase_negative(self, mock_db):
        """Row 9: neck massager -> 否定词组"""
        engine = RuleEngine(mock_db, product_id=1)
        df = pd.DataFrame(
            [
                {
                    "term": "neck massager",
                    "term_type": "keyword",
                    "total_spend": 5.0,
                    "total_orders": 0,
                    "total_clicks": 3,
                }
            ]
        )

        results = engine.analyze(df)
        assert len(results) == 1
        assert results[0].triggered_rule == "弱相关类目词"
        assert results[0].action_type == ActionType.NEGATIVE_PHRASE

    def test_weak_category_blanket_phrase_negative(self, mock_db):
        """Row 18/19: travel blanket -> 否定词组"""
        engine = RuleEngine(mock_db, product_id=1)
        df = pd.DataFrame(
            [
                {
                    "term": "travel blanket",
                    "term_type": "keyword",
                    "total_spend": 3.0,
                    "total_orders": 0,
                    "total_clicks": 2,
                }
            ]
        )

        results = engine.analyze(df)
        assert len(results) == 1
        assert results[0].triggered_rule == "弱相关类目词"
        assert results[0].action_type == ActionType.NEGATIVE_PHRASE

    def test_generic_keyword_pillows_exact_negative(self, mock_db):
        """Row 20: pillows -> 否定精准 (太泛)"""
        engine = RuleEngine(mock_db, product_id=1)
        df = pd.DataFrame(
            [
                {
                    "term": "pillows",
                    "term_type": "keyword",
                    "total_spend": 8.0,
                    "total_orders": 0,
                    "total_clicks": 10,
                }
            ]
        )

        results = engine.analyze(df)
        assert len(results) == 1
        assert results[0].triggered_rule == "太泛的词"
        assert results[0].action_type == ActionType.NEGATIVE_EXACT

    def test_car_keyword_exact_negative(self, mock_db):
        """Row 21: car neck pillow -> 否定精准"""
        engine = RuleEngine(mock_db, product_id=1)
        df = pd.DataFrame(
            [
                {
                    "term": "car neck pillow",
                    "term_type": "keyword",
                    "total_spend": 5.0,
                    "total_orders": 0,
                    "total_clicks": 4,
                }
            ]
        )

        results = engine.analyze(df)
        assert len(results) == 1
        assert results[0].triggered_rule == "汽车相关词"
        assert results[0].action_type == ActionType.NEGATIVE_EXACT


class TestExcelASINAlignment:
    """测试Excel ASIN决策对齐"""

    @pytest.fixture
    def mock_db(self):
        """Mock database with ASIN rules"""
        db = MagicMock()
        db.get_rules.return_value = [
            # Rule #12: 自家变体ASIN
            {
                "name": "自家变体ASIN",
                "rule_type": "asin",
                "conditions": {"is_own_variant": True},
                "action": "手动商品定位",
                "priority": 5,
            },
            # Rule #13: ASIN未出单高花费
            {
                "name": "ASIN未出单高花费",
                "rule_type": "asin",
                "conditions": {"orders_max": 0, "clicks_min": 6, "spend_min": 20.0},
                "action": "否定精准",
                "priority": 10,
            },
            # Rule #14: ASIN出单低转化
            {
                "name": "ASIN出单低转化",
                "rule_type": "asin",
                "conditions": {"orders_min": 1, "clicks_min": 10, "cvr_max": 0.10},
                "action": "否定精准",
                "priority": 15,
            },
            # Rule #15: ASIN出单表现好
            {
                "name": "ASIN出单表现好",
                "rule_type": "asin",
                "conditions": {"orders_min": 1, "cvr_min": 0.10},
                "action": "手动商品定位",
                "priority": 20,
            },
        ]
        db.get_product.return_value = {
            "config": {
                "own_variants": ["B0FCSM9THX"],
                "keyword_libraries": {},
            }
        }
        # v2.0: 人工审核相关性接口返回None，回退到自动检测
        db.get_manual_review_relevance.return_value = None
        return db

    def test_asin_unorder_high_spend_exact_negative(self, mock_db):
        """Row 6: B0CL9SXSBD - Orders=0, Clicks>=6, Spend>=$20 -> 否定精准"""
        engine = RuleEngine(mock_db, product_id=1)
        df = pd.DataFrame(
            [
                {
                    "term": "B0CL9SXSBD",
                    "term_type": "asin",
                    "total_spend": 25.0,
                    "total_orders": 0,
                    "total_clicks": 8,
                }
            ]
        )

        results = engine.analyze(df)
        assert len(results) == 1
        assert results[0].triggered_rule == "ASIN未出单高花费"
        assert results[0].action_type == ActionType.NEGATIVE_EXACT

    def test_asin_order_low_cvr_exact_negative(self, mock_db):
        """Row 23: B07SRRQS5B - Orders>=1, Clicks>=10, CVR<10% -> 否定精准"""
        engine = RuleEngine(mock_db, product_id=1)
        df = pd.DataFrame(
            [
                {
                    "term": "B07SRRQS5B",
                    "term_type": "asin",
                    "total_spend": 30.0,
                    "total_orders": 1,
                    "total_clicks": 15,  # CVR = 1/15 = 6.67% < 10%
                }
            ]
        )

        results = engine.analyze(df)
        assert len(results) == 1
        assert results[0].triggered_rule == "ASIN出单低转化"
        assert results[0].action_type == ActionType.NEGATIVE_EXACT

    def test_asin_order_good_cvr_manual_product(self, mock_db):
        """Row 75: B01IEJHJWK - CVR>=10% -> 手动商品定位"""
        engine = RuleEngine(mock_db, product_id=1)
        df = pd.DataFrame(
            [
                {
                    "term": "B01IEJHJWK",
                    "term_type": "asin",
                    "total_spend": 20.0,
                    "total_orders": 3,
                    "total_clicks": 15,  # CVR = 3/15 = 20% >= 10%
                }
            ]
        )

        results = engine.analyze(df)
        assert len(results) == 1
        assert results[0].triggered_rule == "ASIN出单表现好"
        assert results[0].action_type == ActionType.MANUAL_PRODUCT

    def test_own_variant_asin_manual_product(self, mock_db):
        """Row 38: B0FCSM9THX (自家变体) -> 手动商品定位"""
        engine = RuleEngine(mock_db, product_id=1)
        df = pd.DataFrame(
            [
                {
                    "term": "B0FCSM9THX",
                    "term_type": "asin",
                    "total_spend": 10.0,
                    "total_orders": 1,
                    "total_clicks": 3,
                }
            ]
        )

        results = engine.analyze(df)
        assert len(results) == 1
        assert results[0].triggered_rule == "自家变体ASIN"
        assert results[0].action_type == ActionType.MANUAL_PRODUCT


class TestRelevanceLevelDetection:
    """测试相关性等级检测"""

    @pytest.fixture
    def engine(self):
        db = MagicMock()
        db.get_rules.return_value = []
        db.get_product.return_value = {
            "config": {
                "core_keywords": ["travel pillow", "neck pillow"],
                "related_keywords": ["airplane neck pillow"],
                "keyword_libraries": {
                    "weak_category_keywords": ["massager", "blanket"],
                    "generic_keywords": ["pillows", "pillow", "neck"],
                    "car_keywords": ["car"],
                    "irrelevant_keywords": ["microbead"],
                },
            }
        }
        # v2.0: 人工审核相关性接口返回None，回退到自动检测
        db.get_manual_review_relevance.return_value = None
        return RuleEngine(db, product_id=1)

    def test_strong_relevance_core_keyword(self, engine):
        """核心关键词 -> STRONG"""
        assert engine._get_term_relevance("travel pillow") == RelevanceLevel.STRONG
        assert (
            engine._get_term_relevance("neck pillow for airplane")
            == RelevanceLevel.STRONG
        )

    def test_weak_relevance(self, engine):
        """弱相关类目词 -> WEAK"""
        assert engine._get_term_relevance("neck massager") == RelevanceLevel.WEAK
        assert engine._get_term_relevance("travel blanket") == RelevanceLevel.WEAK

    def test_generic_relevance(self, engine):
        """太泛的词 -> GENERIC (完全匹配)"""
        assert engine._get_term_relevance("pillows") == RelevanceLevel.GENERIC
        assert engine._get_term_relevance("neck") == RelevanceLevel.GENERIC

    def test_car_relevance(self, engine):
        """汽车相关 -> CAR"""
        assert engine._get_term_relevance("car neck pillow") == RelevanceLevel.CAR
        assert engine._get_term_relevance("travel pillow for car") == RelevanceLevel.CAR

    def test_irrelevant(self, engine):
        """不相关 -> IRRELEVANT"""
        assert (
            engine._get_term_relevance("microbead neck pillow")
            == RelevanceLevel.IRRELEVANT
        )
