"""
集成测试共享 fixtures
提供内存数据库、测试数据等共用资源
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.data.db import Database


@pytest.fixture
def temp_db_path():
    """创建临时数据库文件路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "test.db")


@pytest.fixture
def db(temp_db_path):
    """创建已初始化的数据库实例"""
    database = Database(temp_db_path)
    database.init_schema()
    database.init_default_rules()
    yield database
    database.close()


@pytest.fixture
def product_id(db):
    """创建测试产品并返回ID"""
    pid = db.create_product(
        name="旅行枕",
        asin="B0TEST12345",
        category="Home & Kitchen",
    )
    # 配置核心关键词和自有ASIN
    db.update_product_config(
        pid,
        {
            "core_keywords": ["travel pillow", "neck pillow", "travel neck pillow"],
            "related_keywords": ["airplane pillow", "flight pillow"],
            "own_asins": ["B0TEST12345"],
            "keyword_libraries": {
                "generic_keywords": ["pillow", "pillows"],
                "irrelevant_keywords": ["massager", "blanket"],
                "weak_category_keywords": ["neck support", "cushion"],
                "car_keywords": ["car", "automotive"],
            },
            "thresholds": {
                "spend_threshold": 10.0,
                "min_clicks_for_analysis": 20,
                "good_cvr": 0.10,
            },
        },
    )
    return pid


@pytest.fixture
def sample_search_terms_df():
    """创建模拟的搜索词DataFrame（模拟解析后的数据）"""
    return pd.DataFrame(
        [
            # 高花费零转化 → 应否定
            {
                "term": "neck massager",
                "impressions": 500,
                "clicks": 30,
                "spend": 15.0,
                "orders": 0,
                "sales": 0.0,
                "acos": 0.0,
                "term_type": "keyword",
            },
            # 高转化 → 应手动投放
            {
                "term": "travel pillow for airplane",
                "impressions": 1000,
                "clicks": 50,
                "spend": 25.0,
                "orders": 8,
                "sales": 120.0,
                "acos": 0.208,
                "term_type": "keyword",
            },
            # 核心词低转化 → 继续观察
            {
                "term": "travel neck pillow",
                "impressions": 200,
                "clicks": 5,
                "spend": 2.5,
                "orders": 1,
                "sales": 15.0,
                "acos": 0.167,
                "term_type": "keyword",
            },
            # 竞品ASIN → 监控
            {
                "term": "B0COMPET001",
                "impressions": 100,
                "clicks": 10,
                "spend": 5.0,
                "orders": 0,
                "sales": 0.0,
                "acos": 0.0,
                "term_type": "asin",
            },
            # 泛词 → 否定
            {
                "term": "pillow",
                "impressions": 2000,
                "clicks": 100,
                "spend": 50.0,
                "orders": 2,
                "sales": 30.0,
                "acos": 1.667,
                "term_type": "keyword",
            },
            # 汽车词 → 否定
            {
                "term": "car neck pillow",
                "impressions": 300,
                "clicks": 20,
                "spend": 10.0,
                "orders": 0,
                "sales": 0.0,
                "acos": 0.0,
                "term_type": "keyword",
            },
            # 正常表现词
            {
                "term": "memory foam travel pillow",
                "impressions": 800,
                "clicks": 40,
                "spend": 20.0,
                "orders": 5,
                "sales": 75.0,
                "acos": 0.267,
                "term_type": "keyword",
            },
        ]
    )


@pytest.fixture
def campaign_id(db, product_id):
    """创建测试广告活动并返回ID"""
    return db.get_or_create_campaign(
        product_id=product_id,
        name="BLK-Auto-Broad",
        match_type="auto",
    )


@pytest.fixture
def db_with_data(db, product_id, campaign_id, sample_search_terms_df):
    """创建带有测试数据的数据库"""
    db.save_search_terms(sample_search_terms_df, campaign_id)
    return db
