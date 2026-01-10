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
            df = self._parse_csv(file)
        elif file_type in ["xlsx", "xls"]:
            df = self._parse_excel(file)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

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

    def _parse_csv(self, file: BinaryIO) -> pd.DataFrame:
        """解析CSV文件"""
        file.seek(0)
        content = file.read()

        # 尝试不同编码
        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]

        for encoding in encodings:
            try:
                text = content.decode(encoding)
                df = pd.read_csv(io.StringIO(text))
                logger.debug(f"使用编码 {encoding} 成功解析CSV")
                return df
            except (UnicodeDecodeError, pd.errors.EmptyDataError):
                continue

        raise ValueError("无法解析CSV文件，请检查文件编码")

    def _parse_excel(self, file: BinaryIO, sheet_name: int | str = 0) -> pd.DataFrame:
        """
        解析Excel文件

        Args:
            file: 文件对象
            sheet_name: Sheet名称或索引，默认第一个

        Returns:
            DataFrame
        """
        file.seek(0)
        df = pd.read_excel(file, sheet_name=sheet_name)
        logger.debug(f"解析Excel，Sheet: {sheet_name}")
        return df

    def map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        映射列名到标准字段

        Args:
            df: 原始DataFrame

        Returns:
            列名映射后的DataFrame
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
        """转换百分比列"""

        def convert(val):
            if pd.isna(val):
                return 0.0
            if isinstance(val, (int, float)):
                # 如果值大于1，假设是百分比形式
                return val / 100 if val > 1 else val
            if isinstance(val, str):
                val = val.strip().replace("%", "")
                if val == "" or val == "-":
                    return 0.0
                try:
                    num = float(val)
                    return num / 100 if num > 1 else num
                except ValueError:
                    return 0.0
            return 0.0

        return series.apply(convert)


def parse_file(file: BinaryIO, filename: str = None) -> pd.DataFrame:
    """便捷函数：解析文件"""
    parser = FileParser()
    return parser.parse(file, filename)
