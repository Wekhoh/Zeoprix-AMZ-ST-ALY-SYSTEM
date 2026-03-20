"""
Sprint 2 单元测试
测试文件解析和数据聚合模块
"""

import io
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestFileParser:
    """T05-T07: 文件解析测试"""

    def test_detect_csv_type(self):
        """测试CSV类型检测"""
        from src.data.parser import FileParser

        parser = FileParser()

        # 通过文件名检测
        csv_content = b"col1,col2\nval1,val2"
        file = io.BytesIO(csv_content)
        assert parser.detect_file_type(file, "test.csv") == "csv"

    def test_parse_csv_utf8(self):
        """测试解析UTF-8编码CSV"""
        from src.data.parser import FileParser

        parser = FileParser()

        csv_content = """Customer Search Term,Impressions,Clicks,Spend,Orders,Sales
wireless charger,1000,50,25.00,3,45.00
phone case,800,40,20.00,2,30.00"""

        file = io.BytesIO(csv_content.encode("utf-8"))
        df = parser.parse(file, "test.csv")

        assert len(df) == 2
        assert "term" in df.columns
        assert df.iloc[0]["term"] == "wireless charger"

    def test_parse_csv_gbk(self):
        """测试解析GBK编码CSV"""
        from src.data.parser import FileParser

        parser = FileParser()

        csv_content = """客户搜索词,展示量,点击量,花费,订单,销售额
无线充电器,1000,50,25.00,3,45.00
手机壳,800,40,20.00,2,30.00"""

        file = io.BytesIO(csv_content.encode("gbk"))
        df = parser.parse(file, "test.csv")

        assert len(df) == 2
        assert "term" in df.columns

    def test_column_mapping(self):
        """测试列名映射"""
        from src.data.parser import FileParser

        parser = FileParser()

        csv_content = """Customer Search Term,Impressions,Clicks,Click-Thru Rate (CTR),Spend,7 Day Total Orders (#),7 Day Total Sales,Total Advertising Cost of Sales (ACOS)
test keyword,1000,50,5%,25.00,3,45.00,55.56%"""

        file = io.BytesIO(csv_content.encode("utf-8"))
        df = parser.parse(file, "test.csv")

        # 验证列名已映射
        expected_columns = [
            "term",
            "impressions",
            "clicks",
            "ctr",
            "spend",
            "orders",
            "sales",
            "acos",
        ]
        for col in expected_columns:
            assert col in df.columns, f"缺少列: {col}"

    def test_clean_numeric_data(self):
        """测试数值类型转换"""
        from src.data.parser import FileParser

        parser = FileParser()

        csv_content = """Customer Search Term,Impressions,Clicks,Spend,Orders
test keyword,$1,000,50,$25.00,3"""

        file = io.BytesIO(csv_content.encode("utf-8"))
        df = parser.parse(file, "test.csv")

        assert df["impressions"].dtype in ["int64", "int32", "float64"]
        assert df["spend"].dtype == "float64"
        assert df.iloc[0]["spend"] == 25.0

    def test_clean_percent_data(self):
        """测试百分比转换"""
        from src.data.parser import FileParser

        parser = FileParser()

        csv_content = """Customer Search Term,Click-Thru Rate (CTR),Total Advertising Cost of Sales (ACOS)
test keyword,5.5%,55.56%"""

        file = io.BytesIO(csv_content.encode("utf-8"))
        df = parser.parse(file, "test.csv")

        # 百分比应转为小数
        assert 0 < df.iloc[0]["ctr"] < 1
        assert 0 < df.iloc[0]["acos"] < 1

    def test_filter_empty_terms(self):
        """测试过滤空term"""
        from src.data.parser import FileParser

        parser = FileParser()

        csv_content = """Customer Search Term,Impressions,Clicks
keyword1,100,10
,200,20
keyword3,300,30"""

        file = io.BytesIO(csv_content.encode("utf-8"))
        df = parser.parse(file, "test.csv")

        assert len(df) == 2
        assert "" not in df["term"].values


class TestDataAggregator:
    """T09-T13: 数据聚合测试"""

    @pytest.fixture
    def db_with_data(self):
        """创建带有测试数据的数据库"""
        from src.data.db import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path)
        db.init_schema()

        # 创建测试产品
        product_id = db.create_product(name="测试产品", asin="B0TESTPROD")

        # 创建两个广告活动
        campaign1_id = db.create_campaign(
            product_id, "自动紧密", match_type="close-match"
        )
        campaign2_id = db.create_campaign(
            product_id, "自动宽泛", match_type="loose-match"
        )

        # 准备测试数据
        test_data_1 = pd.DataFrame(
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
                },
                {
                    "term": "fast charger",
                    "impressions": 500,
                    "clicks": 20,
                    "ctr": 0.04,
                    "spend": 15.0,
                    "cpc": 0.75,
                    "orders": 0,
                    "sales": 0.0,
                    "acos": 0.0,
                    "roas": 0.0,
                    "conversion_rate": 0.0,
                },
            ]
        )

        test_data_2 = pd.DataFrame(
            [
                {
                    "term": "wireless charger",
                    "impressions": 800,
                    "clicks": 30,
                    "ctr": 0.0375,
                    "spend": 18.0,
                    "cpc": 0.6,
                    "orders": 1,
                    "sales": 15.0,
                    "acos": 1.2,
                    "roas": 0.83,
                    "conversion_rate": 0.033,
                },
                {
                    "term": "phone charger",
                    "impressions": 1200,
                    "clicks": 60,
                    "ctr": 0.05,
                    "spend": 30.0,
                    "cpc": 0.5,
                    "orders": 5,
                    "sales": 75.0,
                    "acos": 0.4,
                    "roas": 2.5,
                    "conversion_rate": 0.083,
                },
            ]
        )

        db.save_search_terms(test_data_1, campaign1_id)
        db.save_search_terms(test_data_2, campaign2_id)

        yield db

        db.close()
        os.unlink(db_path)

    def test_aggregate_by_term(self, db_with_data):
        """测试关键词层聚合"""
        from src.data.aggregator import DataAggregator

        agg = DataAggregator(db_with_data)
        result = agg.aggregate_by_term()

        assert len(result) == 3  # wireless charger, fast charger, phone charger

        # wireless charger应该跨活动聚合
        wc = result[result["term"] == "wireless charger"].iloc[0]
        assert wc["campaign_count"] == 2
        assert wc["total_spend"] == 43.0  # 25 + 18

    def test_aggregate_by_campaign(self, db_with_data):
        """测试广告活动层聚合"""
        from src.data.aggregator import DataAggregator

        agg = DataAggregator(db_with_data)
        result = agg.aggregate_by_campaign()

        assert len(result) == 2  # 两个活动

        # 验证有match_type列
        assert "match_type" in result.columns

    def test_aggregate_by_match_type(self, db_with_data):
        """测试匹配类型层聚合"""
        from src.data.aggregator import DataAggregator

        agg = DataAggregator(db_with_data)
        result = agg.aggregate_by_match_type()

        assert len(result) == 2  # close-match, loose-match
        assert "match_type" in result.columns

    def test_cross_campaign_analysis(self, db_with_data):
        """测试跨活动对比分析"""
        from src.data.aggregator import DataAggregator

        agg = DataAggregator(db_with_data)
        result = agg.cross_campaign_analysis("wireless charger")

        assert len(result) == 2  # 两个活动都有这个词
        assert "has_conflict" in result.columns
        assert result["has_conflict"].iloc[0]  # 表现有分歧

    def test_get_high_spend_zero_orders(self, db_with_data):
        """测试获取高花费零转化词"""
        from src.data.aggregator import DataAggregator

        agg = DataAggregator(db_with_data)
        result = agg.get_high_spend_zero_orders(threshold=10.0)

        assert len(result) == 1  # fast charger
        assert result.iloc[0]["term"] == "fast charger"

    def test_get_high_conversion_keywords(self, db_with_data):
        """测试获取高转化词"""
        from src.data.aggregator import DataAggregator

        agg = DataAggregator(db_with_data)
        result = agg.get_high_conversion_keywords(acos_threshold=0.5, min_orders=3)

        assert len(result) >= 1
        # phone charger应该在结果中
        terms = result["term"].tolist()
        assert "phone charger" in terms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
