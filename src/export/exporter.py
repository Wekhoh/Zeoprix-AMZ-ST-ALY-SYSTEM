"""
报告导出模块
支持导出否词表、手动词表和分析报告
"""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config.logger import get_logger
from src.rules.engine import AnalysisResult

logger = get_logger(__name__)


def secure_filename(filename: str) -> str:
    """
    清理文件名，防止路径遍历攻击

    Args:
        filename: 原始文件名

    Returns:
        安全的文件名
    """
    # 移除路径分隔符和危险字符
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # 移除前导点（防止隐藏文件）
    filename = filename.lstrip(".")
    # 移除路径遍历尝试
    filename = filename.replace("..", "_")
    # 限制长度
    if len(filename) > 200:
        filename = filename[:200]
    return filename or "unnamed"


class ReportExporter:
    """报告导出器"""

    def __init__(self, output_dir: str = None):
        """
        初始化导出器

        Args:
            output_dir: 输出目录（默认当前目录）
        """
        self.output_dir = (
            Path(output_dir).resolve() if output_dir else Path.cwd().resolve()
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _validate_output_path(self, output_path: str) -> Path:
        """
        验证并规范化输出路径，防止路径遍历攻击

        Args:
            output_path: 用户提供的输出路径

        Returns:
            安全的输出路径

        Raises:
            ValueError: 如果路径不安全
        """
        path = Path(output_path).resolve()

        # 检查是否在允许的目录内
        try:
            path.relative_to(self.output_dir)
        except ValueError:
            # 路径不在 output_dir 内，使用安全文件名放在 output_dir 中
            safe_name = secure_filename(path.name)
            path = self.output_dir / safe_name
            logger.warning(f"输出路径不在允许目录内，已重定向到: {path}")

        return path

    def _generate_filename(self, prefix: str, extension: str = "xlsx") -> Path:
        """
        生成带日期的文件名

        Args:
            prefix: 文件名前缀
            extension: 文件扩展名

        Returns:
            完整文件路径
        """
        # 清理前缀中的危险字符
        safe_prefix = secure_filename(prefix)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_prefix}_{timestamp}.{extension}"
        return self.output_dir / filename

    def export_negative_keywords(
        self,
        results: list[AnalysisResult],
        output_path: str = None,
        product_name: str = None,
    ) -> Path:
        """
        导出否词记录表

        Args:
            results: 分析结果列表
            output_path: 输出路径（可选）
            product_name: 产品名称（可选）

        Returns:
            导出文件路径
        """
        # 筛选否词类型结果
        negative_results = [r for r in results if r.action_type == "negative"]

        if not negative_results:
            logger.warning("没有需要导出的否词")
            return None

        # 构建数据
        data = []
        for r in negative_results:
            data.append(
                {
                    "关键词": r.term,
                    "类型": r.term_type,
                    "触发规则": r.triggered_rule,
                    "建议操作": r.suggested_action,
                    "否定类型": self._get_negative_type(r.suggested_action),
                    "置信度": f"{r.confidence:.2%}",
                    "需AI确认": "是" if r.need_ai_judgment else "否",
                    "花费": r.data.get("total_spend", r.data.get("spend", 0)),
                    "点击": r.data.get("total_clicks", r.data.get("clicks", 0)),
                    "订单": r.data.get("total_orders", r.data.get("orders", 0)),
                }
            )

        df = pd.DataFrame(data)

        # 确定输出路径
        if output_path:
            filepath = self._validate_output_path(output_path)
        else:
            prefix = f"{product_name}_否词表" if product_name else "否词表"
            filepath = self._generate_filename(prefix)

        # 导出到Excel
        self._export_to_excel(df, filepath, "否词记录")
        logger.info(f"否词表已导出: {filepath}")

        return filepath

    def export_manual_keywords(
        self,
        results: list[AnalysisResult],
        output_path: str = None,
        product_name: str = None,
    ) -> Path:
        """
        导出手动词追踪表

        Args:
            results: 分析结果列表
            output_path: 输出路径（可选）
            product_name: 产品名称（可选）

        Returns:
            导出文件路径
        """
        # 筛选手动投放类型结果
        manual_results = [r for r in results if r.action_type == "manual"]

        if not manual_results:
            logger.warning("没有需要导出的手动词")
            return None

        # 构建数据
        data = []
        for r in manual_results:
            spend = r.data.get("total_spend", r.data.get("spend", 0))
            orders = r.data.get("total_orders", r.data.get("orders", 0))
            sales = r.data.get("total_sales", r.data.get("sales", 0))
            acos = spend / sales if sales > 0 else 0

            data.append(
                {
                    "关键词": r.term,
                    "类型": r.term_type,
                    "触发规则": r.triggered_rule,
                    "当前ACOS": f"{acos:.2%}",
                    "订单数": orders,
                    "销售额": f"${sales:.2f}",
                    "花费": f"${spend:.2f}",
                    "点击": r.data.get("total_clicks", r.data.get("clicks", 0)),
                    "展示": r.data.get(
                        "total_impressions", r.data.get("impressions", 0)
                    ),
                    "建议出价": self._suggest_bid(r),
                    "优先级": self._calculate_priority(r),
                }
            )

        df = pd.DataFrame(data)

        # 按优先级排序
        priority_order = {"高": 0, "中": 1, "低": 2}
        df["排序键"] = df["优先级"].map(priority_order)
        df = df.sort_values("排序键").drop("排序键", axis=1)

        # 确定输出路径
        if output_path:
            filepath = self._validate_output_path(output_path)
        else:
            prefix = f"{product_name}_手动词表" if product_name else "手动词表"
            filepath = self._generate_filename(prefix)

        # 导出到Excel
        self._export_to_excel(df, filepath, "手动投放推荐")
        logger.info(f"手动词表已导出: {filepath}")

        return filepath

    def export_analysis_report(
        self,
        results: list[AnalysisResult],
        summary: dict = None,
        output_path: str = None,
        product_name: str = None,
    ) -> Path:
        """
        导出完整分析报告

        Args:
            results: 分析结果列表
            summary: 汇总数据（可选）
            output_path: 输出路径（可选）
            product_name: 产品名称（可选）

        Returns:
            导出文件路径
        """
        if not results:
            logger.warning("没有分析结果可导出")
            return None

        # 确定输出路径
        if output_path:
            filepath = self._validate_output_path(output_path)
        else:
            prefix = f"{product_name}_分析报告" if product_name else "分析报告"
            filepath = self._generate_filename(prefix)

        # 创建Excel写入器
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            # Sheet 1: 汇总
            self._write_summary_sheet(writer, results, summary)

            # Sheet 2: 否词清单
            negative_results = [r for r in results if r.action_type == "negative"]
            if negative_results:
                self._write_results_sheet(writer, negative_results, "否词清单")

            # Sheet 3: 手动词清单
            manual_results = [r for r in results if r.action_type == "manual"]
            if manual_results:
                self._write_results_sheet(writer, manual_results, "手动词推荐")

            # Sheet 4: 需AI确认
            ai_pending = [r for r in results if r.need_ai_judgment]
            if ai_pending:
                self._write_results_sheet(writer, ai_pending, "待AI确认")

            # Sheet 5: 全部结果
            self._write_results_sheet(writer, results, "全部结果")

        logger.info(f"分析报告已导出: {filepath}")
        return filepath

    def _write_summary_sheet(
        self,
        writer: pd.ExcelWriter,
        results: list[AnalysisResult],
        summary: dict = None,
    ) -> None:
        """写入汇总Sheet"""
        # 统计数据
        total_count = len(results)
        negative_count = len([r for r in results if r.action_type == "negative"])
        manual_count = len([r for r in results if r.action_type == "manual"])
        observe_count = len([r for r in results if r.action_type == "observe"])
        ai_pending_count = len([r for r in results if r.need_ai_judgment])

        # 规则触发统计
        rule_counts = {}
        for r in results:
            rule_counts[r.triggered_rule] = rule_counts.get(r.triggered_rule, 0) + 1

        # 构建汇总数据
        summary_data = {
            "指标": [
                "分析日期",
                "搜索词总数",
                "建议否定",
                "建议手动投放",
                "继续观察",
                "待AI确认",
            ],
            "数值": [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                total_count,
                negative_count,
                manual_count,
                observe_count,
                ai_pending_count,
            ],
        }

        # 添加外部汇总数据
        if summary:
            summary_data["指标"].extend(
                [
                    "",
                    "总花费",
                    "总订单",
                    "总销售额",
                    "整体ACOS",
                ]
            )
            summary_data["数值"].extend(
                [
                    "",
                    f"${summary.get('total_spend', 0):.2f}",
                    summary.get("total_orders", 0),
                    f"${summary.get('total_sales', 0):.2f}",
                    f"{summary.get('acos', 0):.2%}",
                ]
            )

        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name="汇总", index=False)

        # 规则统计
        if rule_counts:
            df_rules = pd.DataFrame(
                {
                    "规则": list(rule_counts.keys()),
                    "触发次数": list(rule_counts.values()),
                }
            )
            df_rules = df_rules.sort_values("触发次数", ascending=False)
            # 写入同一Sheet的不同区域
            df_rules.to_excel(
                writer, sheet_name="汇总", index=False, startrow=len(df_summary) + 3
            )

    def _write_results_sheet(
        self,
        writer: pd.ExcelWriter,
        results: list[AnalysisResult],
        sheet_name: str,
    ) -> None:
        """写入结果Sheet"""
        data = []
        for r in results:
            data.append(
                {
                    "关键词": r.term,
                    "类型": r.term_type,
                    "触发规则": r.triggered_rule,
                    "建议操作": r.suggested_action,
                    "动作类型": r.action_type,
                    "置信度": f"{r.confidence:.2%}",
                    "需AI确认": "是" if r.need_ai_judgment else "否",
                    "花费": r.data.get("total_spend", r.data.get("spend", 0)),
                    "点击": r.data.get("total_clicks", r.data.get("clicks", 0)),
                    "订单": r.data.get("total_orders", r.data.get("orders", 0)),
                    "销售额": r.data.get("total_sales", r.data.get("sales", 0)),
                }
            )

        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    def _export_to_excel(
        self,
        df: pd.DataFrame,
        filepath: Path,
        sheet_name: str = "Sheet1",
    ) -> None:
        """导出DataFrame到Excel"""
        df.to_excel(filepath, sheet_name=sheet_name, index=False)

    def _get_negative_type(self, suggested_action: str) -> str:
        """根据建议操作确定否定类型"""
        if "精确" in suggested_action:
            return "精确否定"
        elif "短语" in suggested_action:
            return "短语否定"
        else:
            return "精确否定"  # 默认精确否定

    def _suggest_bid(self, result: AnalysisResult) -> str:
        """建议出价"""
        acos = result.data.get("acos", 0)
        current_cpc = result.data.get("cpc", 0)

        if current_cpc > 0:
            if acos < 0.15:
                return f"${current_cpc * 1.2:.2f} (可提高20%)"
            elif acos < 0.25:
                return f"${current_cpc:.2f} (维持)"
            else:
                return f"${current_cpc * 0.8:.2f} (降低20%)"
        else:
            return "根据实际情况设定"

    def _calculate_priority(self, result: AnalysisResult) -> str:
        """计算优先级"""
        orders = result.data.get("total_orders", result.data.get("orders", 0))
        acos = result.data.get("acos", 0)

        if orders >= 5 and acos < 0.2:
            return "高"
        elif orders >= 3 and acos < 0.3:
            return "中"
        else:
            return "低"

    def export_to_csv(
        self,
        results: list[AnalysisResult],
        output_path: str = None,
        result_type: str = "all",
    ) -> Path:
        """
        导出为CSV格式（用于批量上传）

        Args:
            results: 分析结果列表
            output_path: 输出路径
            result_type: 结果类型 (all/negative/manual)

        Returns:
            导出文件路径
        """
        # 根据类型筛选
        if result_type == "negative":
            filtered = [r for r in results if r.action_type == "negative"]
        elif result_type == "manual":
            filtered = [r for r in results if r.action_type == "manual"]
        else:
            filtered = results

        if not filtered:
            logger.warning(f"没有{result_type}类型的结果可导出")
            return None

        # 构建简化数据（适合批量上传）
        data = []
        for r in filtered:
            data.append(
                {
                    "Keyword": r.term,
                    "Match Type": "Negative exact"
                    if "精确" in r.suggested_action
                    else "Negative phrase",
                }
            )

        df = pd.DataFrame(data)

        # 确定输出路径
        if output_path:
            filepath = self._validate_output_path(output_path)
        else:
            filepath = self._generate_filename(f"{result_type}_keywords", "csv")

        df.to_csv(filepath, index=False)
        logger.info(f"CSV已导出: {filepath}")

        return filepath


def get_exporter(output_dir: str = None) -> ReportExporter:
    """获取导出器实例"""
    return ReportExporter(output_dir)
