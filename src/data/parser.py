"""
文件解析模块
解析亚马逊后台导出的CSV/Excel文件
"""

import io
from typing import BinaryIO

import pandas as pd

from src.config.logger import get_logger

logger = get_logger(__name__)

# 亚马逊报告列名映射（英文 -> 标准字段）
COLUMN_MAPPING = {
    # 英文列名
    "Customer Search Term": "term",
    "Search Term": "term",
    "Keyword": "term",
    "Impressions": "impressions",
    "Clicks": "clicks",
    "Click-Thru Rate (CTR)": "ctr",
    "CTR": "ctr",
    "Spend": "spend",
    "Cost Per Click (CPC)": "cpc",
    "CPC": "cpc",
    "7 Day Total Orders (#)": "orders",
    "Orders": "orders",
    "Total Orders": "orders",
    "7 Day Total Sales": "sales",
    "Sales": "sales",
    "Total Advertising Cost of Sales (ACOS)": "acos",
    "ACOS": "acos",
    "Total Return on Advertising Spend (ROAS)": "roas",
    "ROAS": "roas",
    "7 Day Conversion Rate": "conversion_rate",
    "Conversion Rate": "conversion_rate",
    "Campaign Name": "campaign_name",
    "Ad Group Name": "ad_group_name",
    "Targeting": "targeting",
    "Match Type": "match_type",
    "Start Date": "start_date",
    "End Date": "end_date",
    # 中文列名
    "客户搜索词": "term",
    "搜索词": "term",
    "关键词": "term",
    "展示量": "impressions",
    "点击量": "clicks",
    "点击率": "ctr",
    "花费": "spend",
    "每次点击成本": "cpc",
    "订单": "orders",
    "销售额": "sales",
    "广告销售成本": "acos",
    "广告投资回报率": "roas",
    "转化率": "conversion_rate",
    "广告活动名称": "campaign_name",
    "广告组名称": "ad_group_name",
    "投放": "targeting",
    "匹配类型": "match_type",
}


class FileParser:
    """文件解析器"""

    def __init__(self):
        self.supported_types = ["csv", "xlsx", "xls"]

    def parse(self, file: BinaryIO, filename: str = None) -> pd.DataFrame:
        """
        解析上传的文件

        Args:
            file: 文件对象（二进制模式）
            filename: 文件名（用于判断类型）

        Returns:
            解析后的DataFrame
        """
        file_type = self.detect_file_type(file, filename)
        logger.info(f"检测到文件类型: {file_type}")

        if file_type == "csv":
            df = self._parse_csv(file, filename)
        elif file_type in ["xlsx", "xls"]:
            df = self._parse_excel(file, filename=filename)
        else:
            supported = ", ".join(self.supported_types)
            raise ValueError(
                f"不支持的文件类型: {file_type}。"
                f"支持的格式: {supported}。"
                f"请上传亚马逊后台导出的CSV或Excel文件。"
            )

        # 列名映射
        df = self.map_columns(df)

        # 数据清洗
        df = self.clean_data(df)

        logger.info(f"解析完成，共 {len(df)} 行数据")
        return df

    def detect_file_type(self, file: BinaryIO, filename: str = None) -> str:
        """
        检测文件类型

        Args:
            file: 文件对象
            filename: 文件名

        Returns:
            文件类型（csv/xlsx/xls）
        """
        if filename:
            ext = filename.lower().split(".")[-1]
            if ext in self.supported_types:
                return ext

        # 读取文件头判断
        file.seek(0)
        header = file.read(4)
        file.seek(0)

        # Excel文件的魔数
        if header[:2] == b"PK":  # xlsx (ZIP格式)
            return "xlsx"
        elif header[:4] == b"\xd0\xcf\x11\xe0":  # xls (OLE格式)
            return "xls"
        else:
            return "csv"

    def _parse_csv(self, file: BinaryIO, filename: str = None) -> pd.DataFrame:
        """解析CSV文件"""
        file.seek(0)
        content = file.read()

        # 尝试不同编码
        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]
        last_error = None

        for encoding in encodings:
            try:
                text = content.decode(encoding)
                df = pd.read_csv(io.StringIO(text))
                if df.empty:
                    continue
                logger.debug(f"使用编码 {encoding} 成功解析CSV")
                return df
            except UnicodeDecodeError as e:
                last_error = f"编码 {encoding}: 解码失败"
                continue
            except pd.errors.EmptyDataError:
                last_error = f"编码 {encoding}: 文件内容为空"
                continue
            except pd.errors.ParserError as e:
                last_error = f"编码 {encoding}: CSV格式错误 - {str(e)[:100]}"
                continue

        file_info = f" (文件: {filename})" if filename else ""
        raise ValueError(
            f"无法解析CSV文件{file_info}。"
            f"已尝试编码: {', '.join(encodings)}。"
            f"最后错误: {last_error or '未知'}。"
            f"请确保文件是有效的CSV格式，或尝试用Excel打开后另存为UTF-8编码的CSV。"
        )

    def _parse_excel(
        self,
        file: BinaryIO,
        sheet_name: int | str = 0,
        filename: str = None,
    ) -> pd.DataFrame:
        """
        解析Excel文件

        Args:
            file: 文件对象
            sheet_name: Sheet名称或索引，默认第一个
            filename: 文件名（用于错误消息）

        Returns:
            DataFrame
        """
        file.seek(0)
        try:
            df = pd.read_excel(file, sheet_name=sheet_name)
            logger.debug(f"解析Excel，Sheet: {sheet_name}")
            return df
        except Exception as e:
            file_info = f" (文件: {filename})" if filename else ""
            raise ValueError(
                f"无法解析Excel文件{file_info}。"
                f"错误: {str(e)[:200]}。"
                f"请确保文件是有效的Excel格式（.xlsx或.xls），且未被加密或损坏。"
            ) from e

    def map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        映射列名到标准字段

        Args:
            df: 原始DataFrame

        Returns:
            列名映射后的DataFrame

        Raises:
            ValueError: 当没有找到必要的列时
        """
        # 创建列名映射
        rename_map = {}
        for col in df.columns:
            col_str = str(col).strip()
            if col_str in COLUMN_MAPPING:
                rename_map[col] = COLUMN_MAPPING[col_str]

        if rename_map:
            df = df.rename(columns=rename_map)
            logger.debug(f"列名映射: {rename_map}")
        else:
            # 没有找到任何已知列，记录警告但不阻止处理
            logger.warning(
                f"未识别到任何标准列名。"
                f"文件列名: {list(df.columns)[:10]}{'...' if len(df.columns) > 10 else ''}。"
                f"建议使用亚马逊后台原版导出的搜索词报告。"
            )

        # 检查是否有必要的列（term 是最基础的必需列）
        if "term" not in df.columns:
            sample_cols = list(df.columns)[:5]
            logger.warning(
                f"未找到搜索词列（term）。当前列: {sample_cols}。"
                f"可能需要手动指定列映射。"
            )

        return df

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗和标准化数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        df = df.copy()

        # 去除全空行
        df = df.dropna(how="all")

        # 百分比列（需要特殊处理，先于普通数值列）
        percent_columns = ["ctr", "acos", "conversion_rate"]
        for col in percent_columns:
            if col in df.columns:
                df[col] = self._convert_percent(df[col])

        # 处理数值列（不包括已处理的百分比列）
        numeric_columns = {
            "impressions": (int, 0),
            "clicks": (int, 0),
            "orders": (int, 0),
            "spend": (float, 0.0),
            "cpc": (float, 0.0),
            "sales": (float, 0.0),
            "roas": (float, 0.0),
        }

        for col, (dtype, default) in numeric_columns.items():
            if col in df.columns:
                df[col] = self._convert_numeric(df[col], dtype, default)

        # 处理term列
        if "term" in df.columns:
            df["term"] = df["term"].fillna("").astype(str).str.strip()
            # 过滤空term
            df = df[df["term"] != ""]

        # 去除重复行
        df = df.drop_duplicates()

        logger.debug(f"数据清洗完成，剩余 {len(df)} 行")
        return df

    def _convert_numeric(self, series: pd.Series, dtype: type, default) -> pd.Series:
        """转换数值列"""

        def convert(val):
            if pd.isna(val):
                return default
            if isinstance(val, (int, float)):
                return dtype(val)
            if isinstance(val, str):
                # 去除货币符号和逗号
                val = val.replace("$", "").replace(",", "").replace("￥", "").strip()
                if val == "" or val == "-":
                    return default
                try:
                    return dtype(float(val))
                except ValueError:
                    return default
            return default

        return series.apply(convert)

    def _convert_percent(self, series: pd.Series) -> pd.Series:
        """
        转换百分比列

        处理逻辑：
        - 字符串带%符号（如"1.5%", "150%"）：直接除以100
        - 字符串不带%符号：大于100才除以100
        - 纯数值：大于100才除以100（保守策略）
        """

        def convert(val):
            if pd.isna(val):
                return 0.0
            if isinstance(val, str):
                original = val.strip()
                # 检查是否包含百分号
                has_percent_sign = "%" in original
                val_clean = original.replace("%", "")
                if val_clean == "" or val_clean == "-":
                    return 0.0
                try:
                    num = float(val_clean)
                    # 如果有百分号，直接除以100（例如 "0.5%" -> 0.005, "150%" -> 1.5）
                    if has_percent_sign:
                        return num / 100
                    # 如果没有百分号，只有大于100的值才除以100
                    return num / 100 if num > 100 else num
                except ValueError:
                    return 0.0
            if isinstance(val, (int, float)):
                # 纯数值：只有大于100的值才除以100
                # 保守策略：认为 <= 100 的值可能已经是小数或百分比形式
                return val / 100 if val > 100 else val
            return 0.0

        return series.apply(convert)


def parse_file(file: BinaryIO, filename: str = None) -> pd.DataFrame:
    """便捷函数：解析文件"""
    parser = FileParser()
    return parser.parse(file, filename)
