"""
集成测试：数据管道
测试 上传→解析→存储→聚合 完整流程
"""

import pandas as pd
import pytest


class TestDataPipeline:
    """数据管道集成测试"""

    def test_save_and_retrieve_search_terms(self, db, product_id, campaign_id):
        """测试搜索词保存和检索的完整流程"""
        df = pd.DataFrame(
            [
                {
                    "term": "test keyword",
                    "impressions": 100,
                    "clicks": 10,
                    "spend": 5.0,
                    "orders": 1,
                    "sales": 15.0,
                    "acos": 0.333,
                },
            ]
        )

        saved_count = db.save_search_terms(df, campaign_id)
        assert saved_count == 1

        # 检索并验证
        result = db.get_search_terms({"campaign_id": campaign_id})
        assert len(result) == 1
        assert result.iloc[0]["term"] == "test keyword"
        assert result.iloc[0]["clicks"] == 10

    def test_save_multiple_terms_and_aggregate(self, db_with_data, product_id):
        """测试多词保存后聚合"""
        from src.data.aggregator import DataAggregator

        aggregator = DataAggregator(db_with_data)
        df = aggregator.aggregate_by_term(product_id)

        assert not df.empty
        assert len(df) == 7  # conftest 中有7条搜索词

        # 验证衍生指标被计算
        required_cols = ["ctr", "cpc", "acos", "roas", "conversion_rate"]
        for col in required_cols:
            assert col in df.columns

    def test_aggregate_by_campaign(self, db_with_data, product_id):
        """测试按活动聚合"""
        from src.data.aggregator import DataAggregator

        aggregator = DataAggregator(db_with_data)
        df = aggregator.aggregate_by_campaign_term(product_id)

        assert not df.empty
        # 所有词都在同一个活动中
        assert "campaign_id" in df.columns
        assert "campaign_name" in df.columns

    def test_duplicate_terms_accumulate(self, db, product_id, campaign_id):
        """测试重复词多次导入后通过聚合合并"""
        from src.data.aggregator import DataAggregator

        df1 = pd.DataFrame(
            [
                {
                    "term": "travel pillow",
                    "impressions": 100,
                    "clicks": 10,
                    "spend": 5.0,
                    "orders": 1,
                    "sales": 15.0,
                    "acos": 0.333,
                },
            ]
        )
        df2 = pd.DataFrame(
            [
                {
                    "term": "travel pillow",
                    "impressions": 200,
                    "clicks": 20,
                    "spend": 10.0,
                    "orders": 2,
                    "sales": 30.0,
                    "acos": 0.333,
                },
            ]
        )

        db.save_search_terms(df1, campaign_id)
        db.save_search_terms(df2, campaign_id)

        # 聚合后应合并为1条
        aggregator = DataAggregator(db)
        agg_df = aggregator.aggregate_by_term(product_id)
        travel_rows = agg_df[agg_df["term"] == "travel pillow"]
        assert len(travel_rows) == 1

    def test_asin_term_type_detection(self, db, product_id, campaign_id):
        """测试ASIN类型自动检测"""
        df = pd.DataFrame(
            [
                {
                    "term": "B0ABCDEFGH",
                    "impressions": 100,
                    "clicks": 10,
                    "spend": 5.0,
                    "orders": 0,
                    "sales": 0.0,
                    "acos": 0.0,
                },
                {
                    "term": "regular keyword",
                    "impressions": 100,
                    "clicks": 10,
                    "spend": 5.0,
                    "orders": 1,
                    "sales": 15.0,
                    "acos": 0.333,
                },
            ]
        )

        db.save_search_terms(df, campaign_id)
        result = db.get_search_terms({"campaign_id": campaign_id})

        asin_row = result[result["term"] == "B0ABCDEFGH"]
        keyword_row = result[result["term"] == "regular keyword"]

        assert asin_row.iloc[0]["term_type"] == "asin"
        assert keyword_row.iloc[0]["term_type"] == "keyword"

    def test_parser_column_mapping(self):
        """测试解析器中英文列名映射"""
        from src.data.parser import FileParser

        parser = FileParser()

        # 模拟中文列名的DataFrame
        cn_df = pd.DataFrame(
            {
                "客户搜索词": ["test"],
                "展示量": [100],
                "点击量": [10],
                "花费": [5.0],
                "7天总订单数(#)": [1],
                "7天总销售额": [15.0],
            }
        )

        mapped = parser.map_columns(cn_df)
        assert "term" in mapped.columns
        assert "impressions" in mapped.columns
        assert "clicks" in mapped.columns

    def test_parser_clean_data(self):
        """测试数据清洗（百分比转换、去重）"""
        from src.data.parser import FileParser

        parser = FileParser()

        df = pd.DataFrame(
            {
                "term": ["word1", "word1", "word2", ""],
                "impressions": [100, 100, 200, 50],
                "clicks": [10, 10, 20, 5],
                "spend": ["$5.00", "$5.00", "10.0", "2.5"],
                "orders": [1, 1, 2, 0],
                "sales": [15.0, 15.0, 30.0, 0.0],
                "acos": ["33.3%", "33.3%", "0.333", "0%"],
            }
        )

        cleaned = parser.clean_data(df)
        # 应去除空term行
        assert "" not in cleaned["term"].values
        # 百分比应被正确转换
        assert cleaned[cleaned["term"] == "word2"]["acos"].iloc[0] == pytest.approx(
            0.333, abs=0.01
        )

    def test_high_spend_zero_orders_filter(self, db_with_data, product_id):
        """测试高花费零转化筛选"""
        from src.data.aggregator import DataAggregator

        aggregator = DataAggregator(db_with_data)
        result = aggregator.get_high_spend_zero_orders(threshold=10.0)

        # neck massager 花费15 订单0，car neck pillow 花费10 订单0
        high_spend_terms = result["term"].tolist()
        assert "neck massager" in high_spend_terms
