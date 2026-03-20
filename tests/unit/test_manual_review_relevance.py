"""
单元测试: 人工相关性审核功能的数据库方法

测试范围:
- get_manual_review_relevance(): 查询优先级测试
- upsert_manual_review(): 新字段支持测试
- get_pending_reviews_count(): 待审核计数测试
- get_pending_reviews_list(): 待审核列表测试
- batch_update_relevance(): 批量更新测试
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.db import Database


@pytest.fixture
def test_db():
    """创建临时测试数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as file_obj:
        db_path = file_obj.name

    db = Database(db_path)
    db.init_schema()
    db.conn.execute(
        "INSERT INTO products (id, name, asin) VALUES (1, '测试产品', 'B0TEST123')"
    )
    db.conn.commit()

    yield db

    db.close()
    os.unlink(db_path)


class TestGetManualReviewRelevance:
    """测试 get_manual_review_relevance() 方法"""

    def test_returns_none_when_no_record(self, test_db):
        result = test_db.get_manual_review_relevance(product_id=1, term="nonexistent_term")
        assert result is None

    def test_returns_local_record_with_null_campaign(self, test_db):
        test_db.upsert_manual_review(
            product_id=1,
            term="test_term",
            campaign_id=None,
            relevance="strong_core",
            relevance_notes="测试备注",
            scope="local",
        )

        result = test_db.get_manual_review_relevance(product_id=1, term="test_term")
        assert result is not None
        assert result["relevance"] == "strong_core"
        assert result["scope"] == "local"

    def test_local_campaign_priority_over_null_campaign(self, test_db):
        test_db.upsert_manual_review(
            product_id=1,
            term="priority_term",
            campaign_id=None,
            relevance="weak",
            scope="local",
        )
        test_db.conn.execute(
            "INSERT INTO campaigns (id, product_id, name) VALUES (1, 1, '测试活动')"
        )
        test_db.conn.commit()
        test_db.upsert_manual_review(
            product_id=1,
            term="priority_term",
            campaign_id=1,
            relevance="strong_core",
            scope="local",
        )

        result = test_db.get_manual_review_relevance(
            product_id=1, term="priority_term", campaign_id=1
        )
        assert result["relevance"] == "strong_core"

    def test_global_scope_accessible_from_any_campaign(self, test_db):
        test_db.upsert_manual_review(
            product_id=1,
            term="global_term",
            campaign_id=None,
            relevance="irrelevant",
            scope="global",
        )

        result = test_db.get_manual_review_relevance(
            product_id=1, term="global_term", campaign_id=999
        )
        assert result is not None
        assert result["relevance"] == "irrelevant"
        assert result["scope"] == "global"


class TestUpsertManualReview:
    """测试 upsert_manual_review() 方法"""

    def test_insert_with_relevance_fields(self, test_db):
        record_id = test_db.upsert_manual_review(
            product_id=1,
            term="new_term",
            term_type="keyword",
            relevance="strong_longtail",
            relevance_notes="长尾相关词",
            scope="local",
            ai_suggestion="strong_core",
            ai_confidence=0.85,
        )

        assert record_id > 0

        result = test_db.get_manual_review_relevance(product_id=1, term="new_term")
        assert result["relevance"] == "strong_longtail"
        assert result["ai_suggestion"] == "strong_core"
        assert result["ai_confidence"] == 0.85

    def test_update_relevance_preserves_other_fields(self, test_db):
        test_db.upsert_manual_review(
            product_id=1,
            term="update_term",
            system_action="negative_exact",
            relevance="pending",
        )

        test_db.upsert_manual_review(
            product_id=1,
            term="update_term",
            relevance="weak",
            relevance_notes="更新后的备注",
        )

        cursor = test_db.conn.execute(
            "SELECT system_action, relevance FROM manual_reviews WHERE term = ?",
            ("update_term",),
        )
        row = cursor.fetchone()
        assert row["system_action"] == "negative_exact"
        assert row["relevance"] == "weak"

    def test_upsert_can_mark_record_as_reviewed(self, test_db):
        test_db.upsert_manual_review(
            product_id=1,
            term="reviewed_term",
            relevance="weak",
            reviewed=True,
        )

        row = test_db.conn.execute(
            "SELECT reviewed FROM manual_reviews WHERE term = ?",
            ("reviewed_term",),
        ).fetchone()
        assert row["reviewed"] == 1


class TestPendingReviews:
    """测试待审核相关方法"""

    def test_count_pending_reviews(self, test_db):
        test_db.upsert_manual_review(
            product_id=1, term="pending_1", term_type="keyword", relevance=None
        )
        test_db.upsert_manual_review(
            product_id=1, term="pending_2", term_type="keyword", relevance="pending"
        )
        test_db.upsert_manual_review(
            product_id=1, term="pending_3", term_type="asin", relevance=None
        )
        test_db.upsert_manual_review(
            product_id=1,
            term="reviewed_1",
            term_type="keyword",
            relevance="strong_core",
        )

        count = test_db.get_pending_reviews_count(product_id=1)
        assert count["total"] == 3
        assert count["keywords"] == 2
        assert count["asins"] == 1

    def test_asin_with_competition_level_is_not_pending(self, test_db):
        test_db.upsert_manual_review(
            product_id=1,
            term="B0ASIN123",
            term_type="asin",
            competition_level="can_compete",
            competition_notes="已确认可竞争",
            reviewed=True,
        )

        count = test_db.get_pending_reviews_count(product_id=1)
        assert count["total"] == 0
        assert count["asins"] == 0

    def test_list_pending_reviews(self, test_db):
        for i in range(5):
            test_db.upsert_manual_review(product_id=1, term=f"list_test_{i}", relevance=None)
        test_db.upsert_manual_review(product_id=1, term="reviewed", relevance="weak")

        pending = test_db.get_pending_reviews_list(product_id=1, limit=10)
        pending_terms = [item["term"] for item in pending]

        assert len(pending) == 5
        assert "reviewed" not in pending_terms

    def test_list_filter_by_term_type(self, test_db):
        test_db.upsert_manual_review(
            product_id=1, term="keyword_term", term_type="keyword", relevance=None
        )
        test_db.upsert_manual_review(
            product_id=1, term="B0ASIN123", term_type="asin", relevance=None
        )

        keywords_only = test_db.get_pending_reviews_list(product_id=1, term_type="keyword")
        assert len(keywords_only) == 1
        assert keywords_only[0]["term"] == "keyword_term"

    def test_pending_list_excludes_reviewed_asin_with_competition_level(self, test_db):
        test_db.upsert_manual_review(
            product_id=1,
            term="B0PENDING1",
            term_type="asin",
            competition_level=None,
        )
        test_db.upsert_manual_review(
            product_id=1,
            term="B0DONE1",
            term_type="asin",
            competition_level="cannot_compete",
            reviewed=True,
        )

        asins_only = test_db.get_pending_reviews_list(product_id=1, term_type="asin")
        assert [item["term"] for item in asins_only] == ["B0PENDING1"]


class TestBatchUpdateRelevance:
    """测试批量更新相关性"""

    def test_batch_update_multiple_terms(self, test_db):
        for i in range(3):
            test_db.upsert_manual_review(product_id=1, term=f"batch_{i}", relevance=None)

        updates = [
            {"term": "batch_0", "relevance": "strong_core"},
            {"term": "batch_1", "relevance": "weak"},
            {"term": "batch_2", "relevance": "irrelevant", "scope": "global"},
        ]
        count = test_db.batch_update_relevance(product_id=1, updates=updates)

        assert count == 3

        result0 = test_db.get_manual_review_relevance(product_id=1, term="batch_0")
        result2 = test_db.get_manual_review_relevance(product_id=1, term="batch_2")

        assert result0["relevance"] == "strong_core"
        assert result2["relevance"] == "irrelevant"
        assert result2["scope"] == "global"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
