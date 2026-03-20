"""
T29: AI洞察报告测试
TDD RED阶段 — 测试先于实现
"""

from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest


def _make_analysis_result(term, action_type, spend=10.0, orders=1, clicks=10):
    """创建模拟的AnalysisResult"""
    from src.rules.engine import AnalysisResult

    return AnalysisResult(
        term=term,
        term_type="keyword",
        triggered_rule="test_rule",
        suggested_action="test_action",
        action_type=action_type,
        confidence=1.0,
        data={
            "total_spend": spend,
            "total_orders": orders,
            "total_clicks": clicks,
            "total_sales": orders * 15.0,
            "total_impressions": clicks * 10,
        },
    )


class TestInsightReport:
    """AI洞察报告测试"""

    def test_generate_insights_returns_structured_report(self):
        """测试generate_insights返回结构化报告"""
        from src.ai.analyzer import AIAnalyzer, InsightReport

        mock_client = MagicMock()
        mock_client.generate_json.return_value = {
            "summary": "测试摘要",
            "key_findings": ["发现1", "发现2"],
            "recommendations": ["建议1"],
        }

        analyzer = AIAnalyzer(client=mock_client)
        results = [
            _make_analysis_result("word1", "negative_exact", spend=20, orders=0),
            _make_analysis_result("word2", "manual_exact", spend=10, orders=5),
            _make_analysis_result("word3", "observe", spend=5, orders=1),
        ]

        report = analyzer.generate_insights(results, product_context={"name": "旅行枕"})

        assert isinstance(report, InsightReport)
        assert report.summary != ""
        assert len(report.key_findings) > 0
        assert len(report.recommendations) > 0
        assert report.statistics is not None
        assert "total_terms" in report.statistics

    def test_generate_insights_handles_empty_results(self):
        """测试空结果返回空报告"""
        from src.ai.analyzer import AIAnalyzer, InsightReport

        mock_client = MagicMock()
        analyzer = AIAnalyzer(client=mock_client)

        report = analyzer.generate_insights([], product_context={"name": "test"})

        assert isinstance(report, InsightReport)
        assert report.statistics["total_terms"] == 0
        # 空结果不应调用API
        mock_client.generate_json.assert_not_called()

    def test_generate_insights_handles_api_failure(self):
        """测试API失败时降级为本地统计"""
        from src.ai.analyzer import AIAnalyzer, InsightReport

        mock_client = MagicMock()
        mock_client.generate_json.return_value = None  # API返回None模拟失败

        analyzer = AIAnalyzer(client=mock_client)
        results = [
            _make_analysis_result("word1", "negative_exact", spend=20, orders=0),
            _make_analysis_result("word2", "manual_exact", spend=10, orders=5),
        ]

        report = analyzer.generate_insights(results, product_context={"name": "旅行枕"})

        # 降级报告应有本地统计
        assert isinstance(report, InsightReport)
        assert report.statistics["total_terms"] == 2
        assert report.statistics["negative_count"] == 1
        assert report.statistics["manual_count"] == 1
        # 降级时应有默认摘要
        assert report.summary != ""

    def test_generate_insights_statistics_accuracy(self):
        """测试统计数据准确性"""
        from src.ai.analyzer import AIAnalyzer

        mock_client = MagicMock()
        mock_client.generate_json.return_value = {
            "summary": "test",
            "key_findings": ["f1"],
            "recommendations": ["r1"],
        }

        analyzer = AIAnalyzer(client=mock_client)
        results = [
            _make_analysis_result("w1", "negative_exact", spend=20, orders=0),
            _make_analysis_result("w2", "negative_phrase", spend=15, orders=0),
            _make_analysis_result("w3", "manual_exact", spend=10, orders=5),
            _make_analysis_result("w4", "observe", spend=5, orders=1),
            _make_analysis_result("w5", "evaluate", spend=3, orders=0),
        ]

        report = analyzer.generate_insights(results, product_context={"name": "test"})

        stats = report.statistics
        assert stats["total_terms"] == 5
        assert stats["negative_count"] == 2
        assert stats["manual_count"] == 1
        assert stats["observe_count"] >= 1
        assert stats["total_spend"] == pytest.approx(53.0)
        assert stats["total_orders"] == 6
