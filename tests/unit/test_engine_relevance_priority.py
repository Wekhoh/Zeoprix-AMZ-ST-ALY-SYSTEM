"""
单元测试: engine.py 相关性优先级逻辑

测试范围:
- _get_term_relevance(): 人工标记 > 自动检测
- 优先级顺序: Local(campaign) > Local(NULL) > Global
- pending状态回退到自动检测
"""

import json
import os
import sys
import tempfile

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.db import Database
from src.data.models import RelevanceLevel
from src.rules.engine import RuleEngine


# 测试用的产品配置
TEST_PRODUCT_CONFIG = {
    "core_keywords": ["travel pillow", "neck pillow"],
    "related_keywords": ["airplane pillow"],
    "keyword_libraries": {
        "generic_keywords": ["pillow", "neck"],
        "weak_category_keywords": ["massager", "blanket"],
        "car_keywords": ["car", "automobile"],
        "irrelevant_keywords": ["microbead"],
    },
}


@pytest.fixture
def test_db():
    """创建临时测试数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = Database(db_path)
    db.init_schema()

    # 创建测试产品（包含config）
    db.conn.execute(
        "INSERT INTO products (id, name, asin, config) VALUES (1, '测试产品', 'B0TEST123', ?)",
        (json.dumps(TEST_PRODUCT_CONFIG),),
    )
    # 创建测试活动
    db.conn.execute(
        "INSERT INTO campaigns (id, product_id, name) VALUES (1, 1, '测试活动1')"
    )
    db.conn.execute(
        "INSERT INTO campaigns (id, product_id, name) VALUES (2, 1, '测试活动2')"
    )
    db.conn.commit()

    yield db

    db.close()
    os.unlink(db_path)


@pytest.fixture
def engine(test_db):
    """创建规则引擎实例"""
    return RuleEngine(db=test_db, product_id=1)


class TestManualReviewPriority:
    """测试人工标记优先于自动检测"""

    def test_manual_strong_core_overrides_auto_weak(self, test_db, engine):
        """人工标记strong_core覆盖自动检测的weak"""
        # "neck massager" 自动检测应该是 WEAK
        auto_result = engine._get_term_relevance("neck massager")
        assert auto_result == RelevanceLevel.WEAK

        # 人工标记为 strong_core
        test_db.upsert_manual_review(
            product_id=1,
            term="neck massager",
            campaign_id=None,
            relevance="strong_core",
            scope="local",
        )

        # 人工标记应该优先
        result = engine._get_term_relevance("neck massager")
        assert result == "strong_core"

    def test_manual_irrelevant_overrides_auto_strong(self, test_db, engine):
        """人工标记irrelevant覆盖自动检测的strong"""
        # "travel pillow" 自动检测应该是 STRONG
        auto_result = engine._get_term_relevance("travel pillow")
        assert auto_result == RelevanceLevel.STRONG

        # 人工标记为 irrelevant
        test_db.upsert_manual_review(
            product_id=1,
            term="travel pillow",
            campaign_id=None,
            relevance="irrelevant",
            scope="local",
        )

        # 人工标记应该优先
        result = engine._get_term_relevance("travel pillow")
        assert result == "irrelevant"

    def test_pending_falls_back_to_auto_detection(self, test_db, engine):
        """pending状态回退到自动检测"""
        # "travel pillow" 自动检测应该是 STRONG
        auto_result = engine._get_term_relevance("travel pillow")
        assert auto_result == RelevanceLevel.STRONG

        # 人工标记为 pending
        test_db.upsert_manual_review(
            product_id=1,
            term="travel pillow",
            campaign_id=None,
            relevance="pending",
            scope="local",
        )

        # pending应该回退到自动检测
        result = engine._get_term_relevance("travel pillow")
        assert result == RelevanceLevel.STRONG


class TestLocalGlobalPriority:
    """测试Local/Global优先级顺序"""

    def test_local_campaign_overrides_local_null(self, test_db, engine):
        """Local(campaign_id=1) 优先于 Local(campaign_id=NULL)"""
        # 先插入NULL活动的标记
        test_db.upsert_manual_review(
            product_id=1,
            term="priority_test",
            campaign_id=None,
            relevance="weak",
            scope="local",
        )

        # 再插入特定活动的标记
        test_db.upsert_manual_review(
            product_id=1,
            term="priority_test",
            campaign_id=1,
            relevance="strong_core",
            scope="local",
        )

        # 查询时指定campaign_id=1应返回特定活动的标记
        result = engine._get_term_relevance("priority_test", campaign_id=1)
        assert result == "strong_core"

        # 查询时指定campaign_id=2（无特定标记）应返回NULL活动的标记
        result2 = engine._get_term_relevance("priority_test", campaign_id=2)
        assert result2 == "weak"

    def test_local_null_overrides_global(self, test_db, engine):
        """Local(campaign_id=NULL) 优先于 Global"""
        # 先插入global标记
        test_db.upsert_manual_review(
            product_id=1,
            term="scope_test",
            campaign_id=None,
            relevance="irrelevant",
            scope="global",
        )

        # 再插入local NULL标记
        test_db.upsert_manual_review(
            product_id=1,
            term="scope_test",
            campaign_id=None,
            relevance="strong_longtail",
            scope="local",
        )

        # Local应该优先于Global
        result = engine._get_term_relevance("scope_test")
        assert result == "strong_longtail"

    def test_global_accessible_from_any_campaign(self, test_db, engine):
        """Global标记可从任何活动访问"""
        # 插入global标记
        test_db.upsert_manual_review(
            product_id=1,
            term="global_term",
            campaign_id=None,
            relevance="weak",
            scope="global",
        )

        # 任何campaign_id都应能访问global标记
        result1 = engine._get_term_relevance("global_term", campaign_id=1)
        result2 = engine._get_term_relevance("global_term", campaign_id=2)
        result3 = engine._get_term_relevance("global_term", campaign_id=999)

        assert result1 == "weak"
        assert result2 == "weak"
        assert result3 == "weak"


class TestRelevanceLevelMapping:
    """测试RelevanceLevel.to_category()映射"""

    def test_strong_core_maps_to_strong(self):
        """strong_core映射到strong大类"""
        assert RelevanceLevel.to_category("strong_core") == RelevanceLevel.STRONG

    def test_strong_longtail_maps_to_strong(self):
        """strong_longtail映射到strong大类"""
        assert RelevanceLevel.to_category("strong_longtail") == RelevanceLevel.STRONG

    def test_strong_maps_to_strong(self):
        """strong保持不变"""
        assert RelevanceLevel.to_category("strong") == RelevanceLevel.STRONG

    def test_weak_maps_to_weak(self):
        """weak保持不变"""
        assert RelevanceLevel.to_category("weak") == RelevanceLevel.WEAK

    def test_irrelevant_maps_to_irrelevant(self):
        """irrelevant保持不变"""
        assert RelevanceLevel.to_category("irrelevant") == RelevanceLevel.IRRELEVANT

    def test_generic_maps_to_generic(self):
        """generic保持不变"""
        assert RelevanceLevel.to_category("generic") == RelevanceLevel.GENERIC

    def test_pending_maps_to_pending(self):
        """pending保持不变"""
        assert RelevanceLevel.to_category("pending") == RelevanceLevel.PENDING


class TestAutoDetectionFallback:
    """测试无人工标记时的自动检测"""

    def test_auto_detect_strong_keyword(self, engine):
        """自动检测核心词为strong"""
        result = engine._get_term_relevance("travel pillow")
        assert result == RelevanceLevel.STRONG

    def test_auto_detect_weak_keyword(self, engine):
        """自动检测弱相关词为weak"""
        result = engine._get_term_relevance("neck massager")
        assert result == RelevanceLevel.WEAK

    def test_auto_detect_generic_keyword(self, engine):
        """自动检测泛词为generic"""
        result = engine._get_term_relevance("pillow")
        assert result == RelevanceLevel.GENERIC

    def test_auto_detect_car_keyword(self, engine):
        """自动检测汽车相关词为car"""
        result = engine._get_term_relevance("car neck pillow")
        assert result == RelevanceLevel.CAR

    def test_auto_detect_irrelevant_keyword(self, engine):
        """自动检测不相关词为irrelevant"""
        result = engine._get_term_relevance("microbead pillow")
        assert result == RelevanceLevel.IRRELEVANT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
