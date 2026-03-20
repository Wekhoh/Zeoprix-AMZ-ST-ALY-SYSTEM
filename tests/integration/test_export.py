"""
集成测试：导出功能
测试 分析结果→Excel/CSV导出→文件验证
"""

import tempfile
from pathlib import Path

import pandas as pd


class TestExportIntegration:
    """导出功能集成测试"""

    def test_export_negative_keywords_to_excel(self, db_with_data, product_id):
        """测试否词导出到Excel"""
        from src.rules.engine import analyze_search_terms
        from src.export.exporter import ReportExporter

        results = analyze_search_terms(db_with_data, product_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            filepath = exporter.export_negative_keywords(results, product_name="旅行枕")

            if filepath is None:
                # 如果没有否定类结果，跳过
                return

            assert filepath.exists()
            assert filepath.suffix == ".xlsx"
            assert "旅行枕" in filepath.stem

            # 验证Excel文件可读
            df = pd.read_excel(filepath)
            assert len(df) > 0
            assert "关键词" in df.columns
            assert "否定类型" in df.columns

    def test_export_analysis_report_multi_sheet(self, db_with_data, product_id):
        """测试完整分析报告导出（多Sheet）"""
        from src.rules.engine import analyze_search_terms
        from src.export.exporter import ReportExporter

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

            # 验证多个Sheet存在（显式关闭避免Windows文件锁）
            xl = pd.ExcelFile(filepath)
            sheet_names = xl.sheet_names
            xl.close()
            assert "汇总" in sheet_names
            assert "全部结果" in sheet_names

            # 验证汇总Sheet有数据
            summary_df = pd.read_excel(filepath, sheet_name="汇总")
            assert len(summary_df) > 0

            # 验证全部结果Sheet
            all_df = pd.read_excel(filepath, sheet_name="全部结果")
            assert len(all_df) == len(results)

    def test_export_to_csv(self, db_with_data, product_id):
        """测试CSV导出（用于批量上传）"""
        from src.rules.engine import analyze_search_terms
        from src.export.exporter import ReportExporter

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
        from src.rules.engine import analyze_search_terms
        from src.export.exporter import ReportExporter

        results = analyze_search_terms(db_with_data, product_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(output_dir=tmpdir)
            filepath = exporter.export_manual_keywords(results, product_name="旅行枕")

            if filepath is None:
                # 可能没有手动投放类结果
                return

            assert filepath.exists()
            df = pd.read_excel(filepath)
            assert "关键词" in df.columns
            assert "优先级" in df.columns
            assert "建议出价" in df.columns

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
