"""
Sprint 5 单元测试
测试UI组件和导出功能
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.export.exporter import ReportExporter
from src.rules.engine import AnalysisResult


class TestReportExporter:
    """ReportExporter 测试"""

    @pytest.fixture
    def exporter(self, tmp_path):
        """创建导出器实例"""
        return ReportExporter(output_dir=str(tmp_path))

    @pytest.fixture
    def sample_results(self):
        """创建示例分析结果"""
        return [
            AnalysisResult(
                term="wireless charger",
                term_type="keyword",
                triggered_rule="高转化规则",
                suggested_action="建议手动投放（精确匹配）",
                action_type="manual",
                confidence=0.95,
                need_ai_judgment=False,
                data={
                    "total_spend": 50.0,
                    "total_clicks": 100,
                    "total_orders": 5,
                    "total_sales": 150.0,
                    "acos": 0.33,
                    "cpc": 0.5,
                },
            ),
            AnalysisResult(
                term="cheap phone case",
                term_type="keyword",
                triggered_rule="高花费零转化规则",
                suggested_action="建议精确否定",
                action_type="negative",
                confidence=0.9,
                need_ai_judgment=False,
                data={
                    "total_spend": 25.0,
                    "total_clicks": 50,
                    "total_orders": 0,
                    "total_sales": 0,
                },
            ),
            AnalysisResult(
                term="phone accessories",
                term_type="keyword",
                triggered_rule="高花费低转化规则",
                suggested_action="建议短语否定",
                action_type="negative",
                confidence=0.85,
                need_ai_judgment=False,
                data={
                    "total_spend": 30.0,
                    "total_clicks": 60,
                    "total_orders": 1,
                    "total_sales": 20.0,
                },
            ),
            AnalysisResult(
                term="B0ABC12345",
                term_type="asin",
                triggered_rule="竞品ASIN规则",
                suggested_action="需AI确认是否相关",
                action_type="evaluate",
                confidence=0.7,
                need_ai_judgment=True,
                data={
                    "total_spend": 40.0,
                    "total_clicks": 80,
                    "total_orders": 2,
                    "total_sales": 60.0,
                },
            ),
        ]

    def test_exporter_init(self, tmp_path):
        """测试导出器初始化"""
        exporter = ReportExporter(output_dir=str(tmp_path))
        assert exporter.output_dir == tmp_path

    def test_exporter_default_dir(self):
        """测试默认输出目录"""
        exporter = ReportExporter()
        assert exporter.output_dir == Path.cwd()

    def test_export_negative_keywords(self, exporter, sample_results, tmp_path):
        """测试导出否词表"""
        filepath = exporter.export_negative_keywords(sample_results)

        assert filepath is not None
        assert filepath.exists()
        assert filepath.suffix == ".xlsx"
        assert "否词表" in filepath.name

    def test_export_negative_keywords_empty(self, exporter):
        """测试空结果导出否词表"""
        # 只有手动投放类型，没有否定类型
        results = [
            AnalysisResult(
                term="test",
                term_type="keyword",
                triggered_rule="test",
                suggested_action="test",
                action_type="manual",
                confidence=0.9,
                need_ai_judgment=False,
                data={},
            )
        ]

        filepath = exporter.export_negative_keywords(results)
        assert filepath is None

    def test_export_manual_keywords(self, exporter, sample_results, tmp_path):
        """测试导出手动词表"""
        filepath = exporter.export_manual_keywords(sample_results)

        assert filepath is not None
        assert filepath.exists()
        assert filepath.suffix == ".xlsx"
        assert "手动词表" in filepath.name

    def test_export_manual_keywords_empty(self, exporter):
        """测试空结果导出手动词表"""
        # 只有否定类型，没有手动投放类型
        results = [
            AnalysisResult(
                term="test",
                term_type="keyword",
                triggered_rule="test",
                suggested_action="test",
                action_type="negative",
                confidence=0.9,
                need_ai_judgment=False,
                data={},
            )
        ]

        filepath = exporter.export_manual_keywords(results)
        assert filepath is None

    def test_export_analysis_report(self, exporter, sample_results, tmp_path):
        """测试导出完整分析报告"""
        summary = {
            "total_spend": 145.0,
            "total_orders": 8,
            "total_sales": 230.0,
            "acos": 0.63,
        }

        filepath = exporter.export_analysis_report(sample_results, summary=summary)

        assert filepath is not None
        assert filepath.exists()
        assert filepath.suffix == ".xlsx"
        assert "分析报告" in filepath.name

    def test_export_analysis_report_empty(self, exporter):
        """测试空结果导出分析报告"""
        filepath = exporter.export_analysis_report([])
        assert filepath is None

    def test_export_to_csv(self, exporter, sample_results, tmp_path):
        """测试导出CSV"""
        filepath = exporter.export_to_csv(sample_results, result_type="negative")

        assert filepath is not None
        assert filepath.exists()
        assert filepath.suffix == ".csv"

    def test_export_to_csv_all(self, exporter, sample_results, tmp_path):
        """测试导出全部结果为CSV"""
        filepath = exporter.export_to_csv(sample_results, result_type="all")

        assert filepath is not None
        assert filepath.exists()

    def test_get_negative_type_exact(self, exporter):
        """测试识别精确否定类型"""
        result = exporter._get_negative_type("建议精确否定")
        assert result == "精确否定"

    def test_get_negative_type_phrase(self, exporter):
        """测试识别短语否定类型"""
        result = exporter._get_negative_type("建议短语否定")
        assert result == "短语否定"

    def test_get_negative_type_default(self, exporter):
        """测试默认否定类型"""
        result = exporter._get_negative_type("其他操作")
        assert result == "精确否定"

    def test_suggest_bid_increase(self, exporter):
        """测试建议提高出价"""
        result = AnalysisResult(
            term="test",
            term_type="keyword",
            triggered_rule="test",
            suggested_action="test",
            action_type="manual",
            confidence=0.9,
            need_ai_judgment=False,
            data={"acos": 0.1, "cpc": 1.0},
        )
        bid = exporter._suggest_bid(result)
        assert "提高" in bid

    def test_suggest_bid_maintain(self, exporter):
        """测试建议维持出价"""
        result = AnalysisResult(
            term="test",
            term_type="keyword",
            triggered_rule="test",
            suggested_action="test",
            action_type="manual",
            confidence=0.9,
            need_ai_judgment=False,
            data={"acos": 0.2, "cpc": 1.0},
        )
        bid = exporter._suggest_bid(result)
        assert "维持" in bid

    def test_suggest_bid_decrease(self, exporter):
        """测试建议降低出价"""
        result = AnalysisResult(
            term="test",
            term_type="keyword",
            triggered_rule="test",
            suggested_action="test",
            action_type="manual",
            confidence=0.9,
            need_ai_judgment=False,
            data={"acos": 0.3, "cpc": 1.0},
        )
        bid = exporter._suggest_bid(result)
        assert "降低" in bid

    def test_calculate_priority_high(self, exporter):
        """测试高优先级计算"""
        result = AnalysisResult(
            term="test",
            term_type="keyword",
            triggered_rule="test",
            suggested_action="test",
            action_type="manual",
            confidence=0.9,
            need_ai_judgment=False,
            data={"total_orders": 5, "total_spend": 10, "total_sales": 100},
        )
        priority = exporter._calculate_priority(result)
        assert priority == "高"

    def test_calculate_priority_medium(self, exporter):
        """测试中优先级计算"""
        result = AnalysisResult(
            term="test",
            term_type="keyword",
            triggered_rule="test",
            suggested_action="test",
            action_type="manual",
            confidence=0.9,
            need_ai_judgment=False,
            data={"total_orders": 3, "total_spend": 10, "total_sales": 50},
        )
        priority = exporter._calculate_priority(result)
        assert priority == "中"

    def test_calculate_priority_low(self, exporter):
        """测试低优先级计算"""
        result = AnalysisResult(
            term="test",
            term_type="keyword",
            triggered_rule="test",
            suggested_action="test",
            action_type="manual",
            confidence=0.9,
            need_ai_judgment=False,
            data={"total_orders": 1, "total_spend": 10, "total_sales": 20},
        )
        priority = exporter._calculate_priority(result)
        assert priority == "低"


class TestUIImports:
    """测试UI模块导入"""

    def test_import_render_home(self):
        """测试导入首页渲染函数"""
        from src.ui.pages.home import render_home
        assert callable(render_home)

    def test_import_render_upload(self):
        """测试导入上传页渲染函数"""
        from src.ui.pages.upload import render_upload
        assert callable(render_upload)

    def test_import_render_analysis(self):
        """测试导入分析页渲染函数"""
        from src.ui.pages.analysis import render_analysis
        assert callable(render_analysis)

    def test_import_render_actions(self):
        """测试导入操作清单页渲染函数"""
        from src.ui.pages.actions import render_actions
        assert callable(render_actions)

    def test_import_render_settings(self):
        """测试导入设置页渲染函数"""
        from src.ui.pages.settings import render_settings
        assert callable(render_settings)

    def test_import_pages_package(self):
        """测试导入pages包"""
        from src.ui.pages import (
            render_home,
            render_upload,
            render_analysis,
            render_actions,
            render_settings,
        )
        assert all([
            callable(render_home),
            callable(render_upload),
            callable(render_analysis),
            callable(render_actions),
            callable(render_settings),
        ])


class TestUIHelperFunctions:
    """测试UI辅助函数"""

    def test_home_get_dashboard_stats(self):
        """测试仪表盘统计函数"""
        from src.ui.pages.home import get_dashboard_stats

        # Mock数据库
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "term_count": 100,
            "total_spend": 500.0,
            "total_orders": 20,
            "total_sales": 1000.0,
        }
        mock_db.execute.return_value = mock_cursor

        stats = get_dashboard_stats(mock_db, product_id=1)

        assert stats["term_count"] == 100
        assert stats["total_spend"] == 500.0
        assert stats["total_orders"] == 20
        assert stats["total_sales"] == 1000.0
        assert stats["acos"] == 0.5  # 500/1000

    def test_home_get_dashboard_stats_empty(self):
        """测试空结果的仪表盘统计"""
        from src.ui.pages.home import get_dashboard_stats

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_db.execute.return_value = mock_cursor

        stats = get_dashboard_stats(mock_db, product_id=1)

        assert stats["term_count"] == 0
        assert stats["total_spend"] == 0
        assert stats["acos"] == 0

    def test_actions_calculate_acos(self):
        """测试ACOS计算"""
        from src.ui.pages.actions import calculate_acos

        item = {
            "data": {
                "total_spend": 50,
                "total_sales": 100,
            }
        }
        result = calculate_acos(item)
        assert result == "50.00%"

    def test_actions_calculate_acos_zero_sales(self):
        """测试零销售ACOS计算"""
        from src.ui.pages.actions import calculate_acos

        item = {
            "data": {
                "total_spend": 50,
                "total_sales": 0,
            }
        }
        result = calculate_acos(item)
        assert result == "N/A"

    def test_actions_suggest_match_type_exact(self):
        """测试精确匹配建议"""
        from src.ui.pages.actions import suggest_match_type

        item = {
            "data": {
                "total_orders": 5,
                "total_spend": 10,
                "total_sales": 100,
            }
        }
        result = suggest_match_type(item)
        assert result == "精确匹配"

    def test_actions_suggest_match_type_phrase(self):
        """测试短语匹配建议"""
        from src.ui.pages.actions import suggest_match_type

        item = {
            "data": {
                "total_orders": 3,
                "total_spend": 20,
                "total_sales": 100,
            }
        }
        result = suggest_match_type(item)
        assert result == "短语匹配"

    def test_actions_suggest_match_type_broad(self):
        """测试广泛匹配建议"""
        from src.ui.pages.actions import suggest_match_type

        item = {
            "data": {
                "total_orders": 1,
                "total_spend": 50,
                "total_sales": 100,
            }
        }
        result = suggest_match_type(item)
        assert result == "广泛匹配"

    def test_settings_get_default_config(self):
        """测试默认配置"""
        from src.ui.pages.settings import get_default_config

        config = get_default_config()

        assert "high_spend_threshold" in config
        assert "low_ctr_threshold" in config
        assert "min_clicks_threshold" in config
        assert "high_acos_threshold" in config
        assert "min_orders_for_manual" in config
        assert "target_acos" in config


class TestGetExporter:
    """测试get_exporter工厂函数"""

    def test_get_exporter(self, tmp_path):
        """测试获取导出器"""
        from src.export.exporter import get_exporter

        exporter = get_exporter(str(tmp_path))
        assert isinstance(exporter, ReportExporter)
        assert exporter.output_dir == tmp_path

    def test_get_exporter_default(self):
        """测试获取默认导出器"""
        from src.export.exporter import get_exporter

        exporter = get_exporter()
        assert isinstance(exporter, ReportExporter)
