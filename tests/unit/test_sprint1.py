"""
Sprint 1 单元测试
测试数据库、配置和日志模块
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestDatabaseSchema:
    """T01: 数据库Schema测试"""

    def test_all_tables_created(self):
        """测试所有表是否创建成功"""
        from src.data.db import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db = Database(db_path)
            db.init_schema()

            # 检查7个表是否都存在
            expected_tables = [
                "products",
                "campaigns",
                "search_terms",
                "rules",
                "rule_versions",
                "analysis_results",
                "action_plans",
            ]

            for table in expected_tables:
                assert db.table_exists(table), f"表 {table} 不存在"

            db.close()
        finally:
            os.unlink(db_path)

    def test_foreign_keys_enabled(self):
        """测试外键约束是否启用"""
        from src.data.db import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db = Database(db_path)
            db.init_schema()

            # 检查外键设置
            cursor = db.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()
            assert result[0] == 1, "外键约束未启用"

            db.close()
        finally:
            os.unlink(db_path)


class TestDatabaseOperations:
    """T02: 数据库操作测试"""

    @pytest.fixture
    def db(self):
        """创建临时数据库"""
        from src.data.db import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path)
        db.init_schema()
        yield db
        db.close()
        os.unlink(db_path)

    def test_create_product(self, db):
        """测试创建产品"""
        product_id = db.create_product(
            name="测试产品",
            asin="B0TESTPROD",
            category="电子产品",
            config={"core_keywords": ["charger", "充电器"]},
        )

        assert product_id > 0

        product = db.get_product(product_id)
        assert product is not None
        assert product["name"] == "测试产品"
        assert product["asin"] == "B0TESTPROD"
        assert "core_keywords" in product["config"]

    def test_create_campaign(self, db):
        """测试创建广告活动"""
        product_id = db.create_product(name="测试产品")
        campaign_id = db.create_campaign(
            product_id=product_id,
            name="测试活动-自动紧密",
            match_type="close-match",
        )

        assert campaign_id > 0

    def test_get_or_create_campaign(self, db):
        """测试获取或创建广告活动"""
        product_id = db.create_product(name="测试产品")

        # 第一次创建
        campaign_id1 = db.get_or_create_campaign(product_id, "活动A")
        # 第二次获取（应该返回同一个）
        campaign_id2 = db.get_or_create_campaign(product_id, "活动A")

        assert campaign_id1 == campaign_id2

    def test_save_and_get_search_terms(self, db):
        """测试保存和查询搜索词"""
        import pandas as pd

        product_id = db.create_product(name="测试产品")
        campaign_id = db.create_campaign(product_id, "测试活动")

        # 创建测试数据
        test_data = pd.DataFrame(
            [
                {
                    "term": "wireless charger",
                    "impressions": 1000,
                    "clicks": 50,
                    "ctr": 0.05,
                    "spend": 25.0,
                    "cpc": 0.5,
                    "orders": 3,
                    "sales": 45.0,
                    "acos": 0.556,
                    "roas": 1.8,
                    "conversion_rate": 0.06,
                    "report_date": "2026-01-10",
                },
                {
                    "term": "B0TESTASIN",  # 10位ASIN格式
                    "impressions": 500,
                    "clicks": 10,
                    "ctr": 0.02,
                    "spend": 8.0,
                    "cpc": 0.8,
                    "orders": 0,
                    "sales": 0.0,
                    "acos": 0.0,
                    "roas": 0.0,
                    "conversion_rate": 0.0,
                    "report_date": "2026-01-10",
                },
            ]
        )

        # 保存
        count = db.save_search_terms(test_data, campaign_id)
        assert count == 2

        # 查询
        results = db.get_search_terms({"campaign_id": campaign_id})
        assert len(results) == 2

        # 验证ASIN识别
        asin_row = results[results["term"] == "B0TESTASIN"].iloc[0]
        assert asin_row["term_type"] == "asin"

        keyword_row = results[results["term"] == "wireless charger"].iloc[0]
        assert keyword_row["term_type"] == "keyword"

    def test_default_rules(self, db):
        """测试默认规则初始化"""
        db.init_default_rules()

        rules = db.get_rules(product_id=None)
        assert len(rules) >= 5  # 至少有5个默认规则

        # 检查规则名称
        rule_names = [r["name"] for r in rules]
        assert "高花费零转化" in rule_names
        assert "高转化词" in rule_names


class TestSettings:
    """T03: 配置模块测试"""

    def test_load_settings(self):
        """测试加载配置"""
        from src.config.settings import Settings

        # 创建临时.env文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("GEMINI_API_KEY=test_key_12345\n")
            f.write("GEMINI_MODEL=gemini-2.5-flash\n")
            f.write("DATABASE_PATH=data/db/test.db\n")
            f.write("DEBUG=true\n")
            f.write("LOG_LEVEL=DEBUG\n")
            env_path = f.name

        try:
            settings = Settings(env_path)
            assert settings.gemini_api_key == "test_key_12345"
            assert settings.gemini_model == "gemini-2.5-flash"
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
        finally:
            os.unlink(env_path)

    def test_is_api_configured(self):
        """测试API配置检查"""
        from src.config.settings import Settings

        # 清除之前的环境变量
        old_key = os.environ.pop("GEMINI_API_KEY", None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("GEMINI_API_KEY=your_gemini_api_key_here\n")
            f.write("DEBUG=true\n")
            env_path = f.name

        try:
            settings = Settings(env_path)
            assert settings.is_api_configured is False
        finally:
            os.unlink(env_path)
            # 恢复环境变量
            if old_key:
                os.environ["GEMINI_API_KEY"] = old_key


class TestLogger:
    """T04: 日志模块测试"""

    def test_get_logger(self):
        """测试获取日志记录器"""
        from src.config.logger import get_logger

        logger = get_logger(__name__)
        assert logger is not None
        assert logger.name == __name__

    def test_log_output(self, caplog):
        """测试日志输出"""
        import logging

        from src.config.logger import get_logger

        logger = get_logger("test_logger")

        with caplog.at_level(logging.INFO):
            logger.info("测试日志消息")

        # 使用caplog检查日志记录
        assert "测试日志消息" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
