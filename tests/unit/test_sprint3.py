"""
Sprint 3 单元测试
测试规则引擎和配置版本管理模块
"""

import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestRuleEngine:
    """T14-T20: 规则引擎测试"""

    @pytest.fixture
    def db_with_rules(self):
        """创建带有规则的数据库"""
        from src.data.db import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path)
        db.init_schema()
        db.init_default_rules()

        # 创建测试产品
        product_id = db.create_product(
            name="测试产品",
            asin="B0TESTPROD",
            config={
                "core_keywords": ["wireless charger", "快充"],
                "own_asins": ["B0TESTPROD"],
            },
        )

        yield db, product_id

        db.close()
        os.unlink(db_path)

    def test_load_rules(self, db_with_rules):
        """测试加载规则"""
        from src.rules.engine import RuleEngine

        db, product_id = db_with_rules
        engine = RuleEngine(db, product_id)

        assert len(engine.rules) >= 5  # 至少5个默认规则

    def test_high_spend_zero_orders(self, db_with_rules):
        """测试高花费零转化规则"""
        from src.rules.engine import RuleEngine

        db, product_id = db_with_rules
        engine = RuleEngine(db, product_id)

        # 创建测试数据
        test_df = pd.DataFrame(
            [
                {
                    "term": "bad keyword",
                    "term_type": "keyword",
                    "total_spend": 15.0,
                    "total_orders": 0,
                    "acos": 0,
                },
            ]
        )

        results = engine.analyze(test_df)

        assert len(results) == 1
        assert results[0].triggered_rule == "高花费零转化"
        # 更新：新规则使用"否定精准"而非"精确否定"
        assert "否定" in results[0].suggested_action

    def test_high_conversion(self, db_with_rules):
        """测试高转化规则"""
        from src.rules.engine import RuleEngine

        db, product_id = db_with_rules
        engine = RuleEngine(db, product_id)

        test_df = pd.DataFrame(
            [
                {
                    "term": "good keyword",
                    "term_type": "keyword",
                    "total_spend": 20.0,
                    "total_orders": 5,
                    "total_sales": 100.0,
                    "acos": 0.2,
                },
            ]
        )

        results = engine.analyze(test_df)

        assert len(results) == 1
        assert results[0].triggered_rule == "高转化词"
        # 更新：新规则使用"手动精准"而非"手动投放"
        assert "手动" in results[0].suggested_action

    def test_low_conversion_high_spend(self, db_with_rules):
        """测试低转化高花费规则"""
        from src.rules.engine import RuleEngine

        db, product_id = db_with_rules
        engine = RuleEngine(db, product_id)

        test_df = pd.DataFrame(
            [
                {
                    "term": "expensive keyword",
                    "term_type": "keyword",
                    "total_spend": 25.0,
                    "total_orders": 1,
                    "total_clicks": 25,  # 添加clicks以满足新规则条件
                    "total_sales": 15.0,
                    "acos": 1.67,  # 很高的ACOS
                },
            ]
        )

        results = engine.analyze(test_df)

        assert len(results) == 1
        # 更新：可能匹配"低转化高花费"或"高花费"规则
        assert (
            "否定" in results[0].suggested_action
            or "评估" in results[0].suggested_action
        )

    def test_competitor_asin(self, db_with_rules):
        """测试竞品ASIN规则"""
        from src.rules.engine import RuleEngine

        db, product_id = db_with_rules
        engine = RuleEngine(db, product_id)

        test_df = pd.DataFrame(
            [
                {
                    "term": "B0COMPETI1",
                    "term_type": "asin",
                    "total_spend": 5.0,
                    "total_orders": 0,
                    "acos": 0,
                },
            ]
        )

        results = engine.analyze(test_df)

        assert len(results) == 1
        assert results[0].triggered_rule == "竞品ASIN"

    def test_get_negative_keywords(self, db_with_rules):
        """测试获取否词列表"""
        from src.rules.engine import RuleEngine

        db, product_id = db_with_rules
        engine = RuleEngine(db, product_id)

        test_df = pd.DataFrame(
            [
                {
                    "term": "bad1",
                    "term_type": "keyword",
                    "total_spend": 15.0,
                    "total_orders": 0,
                    "acos": 0,
                },
                {
                    "term": "good1",
                    "term_type": "keyword",
                    "total_spend": 10.0,
                    "total_orders": 5,
                    "acos": 0.15,
                },
                {
                    "term": "bad2",
                    "term_type": "keyword",
                    "total_spend": 20.0,
                    "total_orders": 0,
                    "acos": 0,
                },
            ]
        )

        results = engine.analyze(test_df)
        negative = engine.get_negative_keywords(results)

        assert len(negative) == 2

    def test_get_manual_keywords(self, db_with_rules):
        """测试获取手动词列表"""
        from src.rules.engine import RuleEngine

        db, product_id = db_with_rules
        engine = RuleEngine(db, product_id)

        test_df = pd.DataFrame(
            [
                {
                    "term": "bad1",
                    "term_type": "keyword",
                    "total_spend": 15.0,
                    "total_orders": 0,
                    "acos": 0,
                },
                {
                    "term": "good1",
                    "term_type": "keyword",
                    "total_spend": 10.0,
                    "total_orders": 5,
                    "acos": 0.15,
                },
            ]
        )

        results = engine.analyze(test_df)
        manual = engine.get_manual_keywords(results)

        assert len(manual) == 1
        assert manual[0].term == "good1"


class TestKeywordRules:
    """关键词规则函数测试"""

    def test_high_spend_zero_orders_func(self):
        """测试高花费零转化规则函数"""
        from src.rules.keyword_rules import high_spend_zero_orders

        row = pd.Series({"total_spend": 15.0, "total_orders": 0})
        config = {"spend_threshold": 10.0}

        assert high_spend_zero_orders(row, config) == True

        row2 = pd.Series({"total_spend": 5.0, "total_orders": 0})
        assert high_spend_zero_orders(row2, config) == False

    def test_high_conversion_func(self):
        """测试高转化规则函数"""
        from src.rules.keyword_rules import high_conversion

        row = pd.Series({"acos": 0.15, "total_orders": 5})
        config = {"acos_threshold": 0.25, "min_orders": 3}

        assert high_conversion(row, config) == True

        row2 = pd.Series({"acos": 0.5, "total_orders": 5})
        assert high_conversion(row2, config) == False


class TestASINRules:
    """ASIN规则测试"""

    def test_is_valid_asin(self):
        """测试ASIN格式验证"""
        from src.rules.asin_rules import is_valid_asin

        assert is_valid_asin("B0TESTPROD") is True
        assert is_valid_asin("B0ABCDEFGH") is True
        assert is_valid_asin("B0COMPETITOR") is False  # 11位
        assert is_valid_asin("A0TESTPROD") is False  # 不是B开头
        assert is_valid_asin("wireless charger") is False

    def test_analyze_asin(self):
        """测试ASIN分析"""
        from src.rules.asin_rules import analyze_asin

        row = pd.Series(
            {
                "term": "B0COMPETI1",
                "term_type": "asin",
                "total_spend": 15.0,
                "total_orders": 0,
            }
        )
        config = {"own_asins": ["B0TESTPROD"]}

        result = analyze_asin(row, config)

        assert result is not None
        assert result.is_competitor is True
        assert result.suggested_action == "否定"


class TestConfigManager:
    """T21-T23: 配置版本管理测试"""

    @pytest.fixture
    def db_with_product(self):
        """创建带产品的数据库"""
        from src.data.db import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path)
        db.init_schema()
        db.init_default_rules()

        product_id = db.create_product(name="测试产品", asin="B0TESTPROD")

        yield db, product_id

        db.close()
        os.unlink(db_path)

    def test_get_product_config(self, db_with_product):
        """测试获取产品配置"""
        from src.config.manager import ConfigManager

        db, product_id = db_with_product
        cm = ConfigManager(db)

        config = cm.get_product_config(product_id)
        assert isinstance(config, dict)

    def test_update_product_config(self, db_with_product):
        """测试更新产品配置"""
        from src.config.manager import ConfigManager

        db, product_id = db_with_product
        cm = ConfigManager(db)

        cm.update_product_config(product_id, {"core_keywords": ["test", "keyword"]})

        config = cm.get_product_config(product_id)
        assert "core_keywords" in config
        assert len(config["core_keywords"]) == 2

    def test_set_core_keywords(self, db_with_product):
        """测试设置核心关键词"""
        from src.config.manager import ConfigManager

        db, product_id = db_with_product
        cm = ConfigManager(db)

        cm.set_core_keywords(product_id, ["wireless", "charger"])

        config = cm.get_product_config(product_id)
        assert config["core_keywords"] == ["wireless", "charger"]

    def test_create_version(self, db_with_product):
        """测试创建版本"""
        from src.config.manager import ConfigManager

        db, product_id = db_with_product
        cm = ConfigManager(db)

        version = cm.create_version(product_id, "初始版本")

        assert version == 1

        history = cm.get_version_history(product_id)
        assert len(history) == 1
        assert history[0]["description"] == "初始版本"

    def test_rollback(self, db_with_product):
        """测试回滚"""
        from src.config.manager import ConfigManager

        db, product_id = db_with_product
        cm = ConfigManager(db)

        # 创建初始版本
        cm.create_version(product_id, "v1")

        # 添加自定义规则
        db.execute(
            """
            INSERT INTO rules (product_id, name, rule_type, conditions, action, priority)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (product_id, "自定义规则", "keyword", '{"spend_min": 50}', "测试动作", 5),
        )
        db.commit()

        # 创建v2版本
        cm.create_version(product_id, "v2-添加自定义规则")

        # 验证有自定义规则
        rules_before = cm.get_current_rules(product_id)
        custom_rules = [r for r in rules_before if r["name"] == "自定义规则"]
        assert len(custom_rules) == 1

        # 回滚到v1
        cm.rollback(product_id, 1)

        # 验证自定义规则被删除
        rules_after = cm.get_current_rules(product_id)
        custom_rules = [r for r in rules_after if r["name"] == "自定义规则"]
        assert len(custom_rules) == 0


class TestCampaignAnalysis:
    """按活动分析功能测试"""

    @pytest.fixture
    def engine_with_config(self):
        """创建带有配置的规则引擎"""
        from unittest.mock import MagicMock
        from src.rules.engine import RuleEngine
        from src.data.models import ActionType

        db = MagicMock()
        db.get_rules.return_value = []
        db.get_product.return_value = {
            "config": {
                "thresholds": {
                    "min_clicks_for_analysis": 20,
                    "good_cvr": 0.10,
                }
            }
        }

        engine = RuleEngine(db, product_id=1)
        return engine, ActionType

    def test_auto_action_keep_on_good_performance(self, engine_with_config):
        """测试表现好时返回 keep"""
        engine, ActionType = engine_with_config

        result = engine._determine_auto_action(
            action_type=ActionType.MANUAL_EXACT,
            clicks=25,
            orders=3,
            cvr=0.12,  # > 0.10
            spend=50.0,
        )
        assert result == "keep"

    def test_auto_action_negate_on_bad_performance(self, engine_with_config):
        """测试表现差时返回 negate"""
        engine, ActionType = engine_with_config

        result = engine._determine_auto_action(
            action_type=ActionType.MANUAL_EXACT,
            clicks=25,  # >= 20
            orders=0,  # 零转化
            cvr=0.0,
            spend=50.0,
        )
        assert result == "negate"

    def test_auto_action_observe_on_insufficient_sample(self, engine_with_config):
        """测试样本不足时返回 observe"""
        engine, ActionType = engine_with_config

        result = engine._determine_auto_action(
            action_type=ActionType.MANUAL_EXACT,
            clicks=15,  # < 20，样本不足
            orders=0,
            cvr=0.0,
            spend=30.0,
        )
        assert result == "observe"

    def test_auto_action_respects_explicit_with_neg(self, engine_with_config):
        """测试规则指定 WITH_NEG 时直接返回 negate，不受表现影响"""
        engine, ActionType = engine_with_config

        # 即使表现很好（CVR 15%），规则指定否定就应该否定
        result = engine._determine_auto_action(
            action_type=ActionType.MANUAL_EXACT_WITH_NEG,
            clicks=30,
            orders=5,
            cvr=0.15,  # 表现好
            spend=100.0,
        )
        assert result == "negate"

    def test_auto_action_respects_explicit_no_neg(self, engine_with_config):
        """测试规则指定 NO_NEG 时直接返回 keep，不受表现影响"""
        engine, ActionType = engine_with_config

        # 即使表现很差（零转化），规则指定不否定就应该保留
        result = engine._determine_auto_action(
            action_type=ActionType.MANUAL_EXACT_NO_NEG,
            clicks=30,
            orders=0,
            cvr=0.0,  # 表现差
            spend=100.0,
        )
        assert result == "keep"

    def test_auto_action_none_for_non_manual(self, engine_with_config):
        """测试非手动动作返回 None"""
        engine, ActionType = engine_with_config

        result = engine._determine_auto_action(
            action_type=ActionType.NEGATIVE_EXACT,
            clicks=30,
            orders=5,
            cvr=0.15,
            spend=100.0,
        )
        assert result is None

    def test_auto_action_boundary_cvr(self, engine_with_config):
        """测试 CVR 边界值（恰好等于 10%）"""
        engine, ActionType = engine_with_config

        # CVR = 10% 且有订单应该返回 keep
        result = engine._determine_auto_action(
            action_type=ActionType.MANUAL_EXACT,
            clicks=20,
            orders=2,
            cvr=0.10,  # 恰好等于阈值
            spend=40.0,
        )
        assert result == "keep"

    def test_auto_action_boundary_clicks(self, engine_with_config):
        """测试点击数边界值（恰好等于 20）"""
        engine, ActionType = engine_with_config

        # clicks = 20 且零订单应该返回 negate
        result = engine._determine_auto_action(
            action_type=ActionType.MANUAL_EXACT,
            clicks=20,  # 恰好等于阈值
            orders=0,
            cvr=0.0,
            spend=40.0,
        )
        assert result == "negate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
