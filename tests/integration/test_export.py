"""
集成测试：导出功能
测试 分析结果→Excel/CSV导出→文件验证
"""

import tempfile

import pandas as pd

from src.data.models import ActionType
from src.rules.engine import AnalysisResult


def build_result(
    term: str,
    action_type: str,
    suggested_action: str,
    term_type: str = "keyword",
    **data,
) -> AnalysisResult:
    return AnalysisResult(
        term=term,
        term_type=term_type,
        triggered_rule="测试规则",
        suggested_action=suggested_action,
        action_type=action_type,
        confidence=0.9,
        data={
            "total_spend": data.get("total_spend", 12.5),
            "total_clicks": data.get("total_clicks", 18),
            "total_orders": data.get("total_orders", 3),
            "total_sales": data.get("total_sales", 60.0),
            "acos": data.get("acos", 0.2),
            "cpc": data.get("cpc", 0.8),
            "impressions": data.get("impressions", 150),
        },
    )


class TestExportIntegration:
    """导出功能集成测试"""

    def test_export_negative_keywords_to_excel(self, db_with_data, product_id):
        """测试否词导出到Excel"""
        from src.export.exporter import ReportExporter
        from src.rules.engine import analyze_search_terms

        results = analyze_search_terms(db_with_data, product_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            filepath = exporter.export_negative_keywords(results, product_name="旅行枕")

            if filepath is None:
                return

            assert filepath.exists()
            assert filepath.suffix == ".xlsx"
            assert "旅行枕" in filepath.stem

            df = pd.read_excel(filepath)
            assert len(df) > 0
            assert "关键词" in df.columns
            assert "否定类型" in df.columns

    def test_export_analysis_report_multi_sheet(self, db_with_data, product_id):
        """测试完整分析报告导出（多Sheet）"""
        from src.export.exporter import ReportExporter
        from src.rules.engine import analyze_search_terms

        results = analyze_search_terms(db_with_data, product_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            filepath = exporter.export_analysis_report(
                results,
                summary={
                    "total_spend": 127.5,
                    "total_orders": 17,
                    "total_sales": 255.0,
                    "acos": 0.5,
                },
                product_name="旅行枕",
            )

            assert filepath is not None
            assert filepath.exists()

            xl = pd.ExcelFile(filepath)
            sheet_names = xl.sheet_names
            xl.close()
            assert "汇总" in sheet_names
            assert "全部结果" in sheet_names

            summary_df = pd.read_excel(filepath, sheet_name="汇总")
            assert len(summary_df) > 0

            all_df = pd.read_excel(filepath, sheet_name="全部结果")
            assert len(all_df) == len(results)

    def test_export_to_csv(self, db_with_data, product_id):
        """测试CSV导出（用于批量上传）"""
        from src.export.exporter import ReportExporter
        from src.rules.engine import analyze_search_terms

        results = analyze_search_terms(db_with_data, product_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            filepath = exporter.export_to_csv(results, result_type="negative")

            if filepath is None:
                return

            assert filepath.exists()
            assert filepath.suffix == ".csv"

            df = pd.read_csv(filepath)
            assert "Keyword" in df.columns
            assert "Match Type" in df.columns

    def test_export_manual_keywords(self, db_with_data, product_id):
        """测试手动投放词导出"""
        from src.export.exporter import ReportExporter
        from src.rules.engine import analyze_search_terms

        results = analyze_search_terms(db_with_data, product_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            filepath = exporter.export_manual_keywords(results, product_name="旅行枕")

            if filepath is None:
                return

            assert filepath.exists()
            df = pd.read_excel(filepath)
            assert "关键词" in df.columns
            assert "优先级" in df.columns
            assert "建议出价" in df.columns

    def test_export_negative_keywords_supports_new_action_types(self):
        """negative_exact / negative_phrase 也应进入否词导出。"""
        from src.export.exporter import ReportExporter

        results = [
            build_result(
                term="pillows",
                action_type=ActionType.NEGATIVE_EXACT,
                suggested_action="自动直接否定精准",
            ),
            build_result(
                term="travel blanket",
                action_type=ActionType.NEGATIVE_PHRASE,
                suggested_action="否定词组",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            filepath = exporter.export_negative_keywords(results, product_name="旅行枕")

            assert filepath is not None
            df = pd.read_excel(filepath)
            assert set(df["关键词"]) == {"pillows", "travel blanket"}
            assert set(df["否定类型"]) == {"精确否定", "短语否定"}

    def test_export_manual_keywords_supports_new_action_types(self):
        """manual_* 新动作类型也应进入手动词导出。"""
        from src.export.exporter import ReportExporter

        results = [
            build_result(
                term="travel pillow for airplane",
                action_type=ActionType.MANUAL_EXACT_WITH_NEG,
                suggested_action="去拉手动精准，同时自动否定",
                total_orders=6,
                total_sales=120.0,
                acos=0.18,
            ),
            build_result(
                term="B01IEJHJWK",
                action_type=ActionType.MANUAL_PRODUCT_NO_NEG,
                suggested_action="手动商品定位",
                term_type="asin",
                total_orders=4,
                total_sales=90.0,
                acos=0.22,
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            filepath = exporter.export_manual_keywords(results, product_name="旅行枕")

            assert filepath is not None
            df = pd.read_excel(filepath)
            assert set(df["关键词"]) == {"travel pillow for airplane", "B01IEJHJWK"}
            assert "优先级" in df.columns

    def test_export_analysis_report_includes_negative_and_manual_sheets_for_new_types(self):
        """完整报告应为新动作类型生成否词/手动 Sheet。"""
        from src.export.exporter import ReportExporter

        results = [
            build_result(
                term="pillows",
                action_type=ActionType.NEGATIVE_EXACT,
                suggested_action="自动直接否定精准",
            ),
            build_result(
                term="travel pillow for airplane",
                action_type=ActionType.MANUAL_EXACT_NO_NEG,
                suggested_action="去拉手动精准，先不否",
                total_orders=5,
                total_sales=110.0,
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            filepath = exporter.export_analysis_report(results, product_name="旅行枕")

            assert filepath is not None
            excel_file = pd.ExcelFile(filepath)
            sheet_names = set(excel_file.sheet_names)
            excel_file.close()
            assert {"否词清单", "手动词推荐", "全部结果"}.issubset(sheet_names)

    def test_export_to_csv_supports_new_negative_action_types(self):
        """CSV 导出也应识别 negative_exact / negative_phrase。"""
        from src.export.exporter import ReportExporter

        results = [
            build_result(
                term="pillows",
                action_type=ActionType.NEGATIVE_EXACT,
                suggested_action="自动直接否定精准",
            ),
            build_result(
                term="travel blanket",
                action_type=ActionType.NEGATIVE_PHRASE,
                suggested_action="否定词组",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            filepath = exporter.export_to_csv(results, result_type="negative")

            assert filepath is not None
            df = pd.read_csv(filepath)
            assert set(df["Keyword"]) == {"pillows", "travel blanket"}

    def test_export_empty_results_returns_none(self):
        """测试空结果导出返回None"""
        from src.export.exporter import ReportExporter

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            result = exporter.export_negative_keywords([])
            assert result is None

    def test_secure_filename(self):
        """测试文件名安全清理"""
        from src.export.exporter import secure_filename

        assert secure_filename("test<>file") == "test__file"
        assert secure_filename("../../../etc/passwd") == "_____etc_passwd"
        assert secure_filename("") == "unnamed"
        assert len(secure_filename("a" * 300)) <= 200
