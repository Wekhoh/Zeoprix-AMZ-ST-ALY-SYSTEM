"""
多维度数据聚合模块
支持ASIN层、广告活动层、匹配类型层、关键词层聚合
"""

import pandas as pd

from src.config.logger import get_logger
from src.data.db import Database

logger = get_logger(__name__)


class DataAggregator:
    """多维度数据聚合器"""

    def __init__(self, db: Database):
        """
        初始化聚合器

        Args:
            db: 数据库实例
        """
        self.db = db

    def aggregate_by_asin(self, product_id: int = None) -> pd.DataFrame:
        """
        按ASIN层聚合

        Args:
            product_id: 产品ID（可选，用于筛选）

        Returns:
            聚合后的DataFrame
        """
        filters = {}
        if product_id:
            filters["product_id"] = product_id

        df = self.db.get_search_terms(filters)

        if df.empty:
            return pd.DataFrame()

        # 按产品ASIN聚合
        agg_df = (
            df.groupby("product_asin")
            .agg(
                product_name=("product_name", "first"),
                total_impressions=("impressions", "sum"),
                total_clicks=("clicks", "sum"),
                total_spend=("spend", "sum"),
                total_orders=("orders", "sum"),
                total_sales=("sales", "sum"),
                term_count=("term", "nunique"),
                campaign_count=("campaign_name", "nunique"),
            )
            .reset_index()
        )

        # 计算衍生指标
        agg_df["ctr"] = (agg_df["total_clicks"] / agg_df["total_impressions"]).fillna(0)
        agg_df["cpc"] = (agg_df["total_spend"] / agg_df["total_clicks"]).fillna(0)
        agg_df["acos"] = (agg_df["total_spend"] / agg_df["total_sales"]).fillna(0)
        agg_df["roas"] = (agg_df["total_sales"] / agg_df["total_spend"]).fillna(0)
        agg_df["conversion_rate"] = (agg_df["total_orders"] / agg_df["total_clicks"]).fillna(0)

        logger.debug(f"ASIN层聚合完成，共 {len(agg_df)} 个ASIN")
        return agg_df

    def aggregate_by_campaign(self, product_id: int = None, asin: str = None) -> pd.DataFrame:
        """
        按广告活动层聚合

        Args:
            product_id: 产品ID（可选）
            asin: 产品ASIN（可选）

        Returns:
            聚合后的DataFrame
        """
        filters = {}
        if product_id:
            filters["product_id"] = product_id

        df = self.db.get_search_terms(filters)

        if asin:
            df = df[df["product_asin"] == asin]

        if df.empty:
            return pd.DataFrame()

        # 按广告活动聚合
        agg_df = (
            df.groupby(["campaign_name", "match_type"])
            .agg(
                product_asin=("product_asin", "first"),
                product_name=("product_name", "first"),
                total_impressions=("impressions", "sum"),
                total_clicks=("clicks", "sum"),
                total_spend=("spend", "sum"),
                total_orders=("orders", "sum"),
                total_sales=("sales", "sum"),
                term_count=("term", "nunique"),
            )
            .reset_index()
        )

        # 计算衍生指标
        agg_df["ctr"] = (agg_df["total_clicks"] / agg_df["total_impressions"]).fillna(0)
        agg_df["cpc"] = (agg_df["total_spend"] / agg_df["total_clicks"]).fillna(0)
        agg_df["acos"] = (agg_df["total_spend"] / agg_df["total_sales"]).fillna(0)
        agg_df["roas"] = (agg_df["total_sales"] / agg_df["total_spend"]).fillna(0)
        agg_df["conversion_rate"] = (agg_df["total_orders"] / agg_df["total_clicks"]).fillna(0)

        logger.debug(f"广告活动层聚合完成，共 {len(agg_df)} 个活动")
        return agg_df

    def aggregate_by_match_type(self, product_id: int = None, campaign_id: int = None) -> pd.DataFrame:
        """
        按匹配类型层聚合

        Args:
            product_id: 产品ID（可选）
            campaign_id: 广告活动ID（可选）

        Returns:
            聚合后的DataFrame
        """
        filters = {}
        if product_id:
            filters["product_id"] = product_id
        if campaign_id:
            filters["campaign_id"] = campaign_id

        df = self.db.get_search_terms(filters)

        if df.empty:
            return pd.DataFrame()

        # 按匹配类型聚合
        agg_df = (
            df.groupby("match_type")
            .agg(
                total_impressions=("impressions", "sum"),
                total_clicks=("clicks", "sum"),
                total_spend=("spend", "sum"),
                total_orders=("orders", "sum"),
                total_sales=("sales", "sum"),
                term_count=("term", "nunique"),
                campaign_count=("campaign_name", "nunique"),
            )
            .reset_index()
        )

        # 计算衍生指标
        agg_df["ctr"] = (agg_df["total_clicks"] / agg_df["total_impressions"]).fillna(0)
        agg_df["cpc"] = (agg_df["total_spend"] / agg_df["total_clicks"]).fillna(0)
        agg_df["acos"] = (agg_df["total_spend"] / agg_df["total_sales"]).fillna(0)
        agg_df["roas"] = (agg_df["total_sales"] / agg_df["total_spend"]).fillna(0)
        agg_df["conversion_rate"] = (agg_df["total_orders"] / agg_df["total_clicks"]).fillna(0)

        logger.debug(f"匹配类型层聚合完成，共 {len(agg_df)} 种类型")
        return agg_df

    def aggregate_by_term(self, product_id: int = None, term_type: str = None) -> pd.DataFrame:
        """
        按关键词/ASIN层聚合（最细粒度）

        Args:
            product_id: 产品ID（可选）
            term_type: 类型筛选（keyword/asin）

        Returns:
            聚合后的DataFrame
        """
        filters = {}
        if product_id:
            filters["product_id"] = product_id
        if term_type:
            filters["term_type"] = term_type

        df = self.db.get_search_terms(filters)

        if df.empty:
            return pd.DataFrame()

        # 按搜索词聚合（跨活动汇总）
        agg_df = (
            df.groupby(["term", "term_type"])
            .agg(
                total_impressions=("impressions", "sum"),
                total_clicks=("clicks", "sum"),
                total_spend=("spend", "sum"),
                total_orders=("orders", "sum"),
                total_sales=("sales", "sum"),
                campaign_count=("campaign_name", "nunique"),
                campaigns=("campaign_name", lambda x: ", ".join(x.unique())),
            )
            .reset_index()
        )

        # 计算衍生指标
        agg_df["ctr"] = (agg_df["total_clicks"] / agg_df["total_impressions"]).fillna(0)
        agg_df["cpc"] = (agg_df["total_spend"] / agg_df["total_clicks"]).fillna(0)
        agg_df["acos"] = (agg_df["total_spend"] / agg_df["total_sales"]).fillna(0)
        agg_df["roas"] = (agg_df["total_sales"] / agg_df["total_spend"]).fillna(0)
        agg_df["conversion_rate"] = (agg_df["total_orders"] / agg_df["total_clicks"]).fillna(0)

        # 按花费降序排序
        agg_df = agg_df.sort_values("total_spend", ascending=False)

        logger.debug(f"关键词层聚合完成，共 {len(agg_df)} 个词")
        return agg_df

    def cross_campaign_analysis(self, term: str, product_id: int = None) -> pd.DataFrame:
        """
        跨活动对比分析同一关键词

        Args:
            term: 搜索词
            product_id: 产品ID（可选）

        Returns:
            该词在各活动中的表现DataFrame
        """
        filters = {}
        if product_id:
            filters["product_id"] = product_id

        df = self.db.get_search_terms(filters)

        # 筛选特定词
        df = df[df["term"] == term]

        if df.empty:
            logger.warning(f"未找到搜索词: {term}")
            return pd.DataFrame()

        # 按活动分组
        result = (
            df.groupby(["campaign_name", "match_type"])
            .agg(
                impressions=("impressions", "sum"),
                clicks=("clicks", "sum"),
                spend=("spend", "sum"),
                orders=("orders", "sum"),
                sales=("sales", "sum"),
            )
            .reset_index()
        )

        # 计算指标
        result["ctr"] = (result["clicks"] / result["impressions"]).fillna(0)
        result["acos"] = (result["spend"] / result["sales"]).fillna(0)
        result["conversion_rate"] = (result["orders"] / result["clicks"]).fillna(0)

        # 标记表现差异
        if len(result) > 1:
            avg_acos = result["acos"].mean()
            result["performance"] = result["acos"].apply(
                lambda x: "优于平均" if x < avg_acos else "低于平均" if x > avg_acos else "平均"
            )
            result["has_conflict"] = len(result["performance"].unique()) > 1
        else:
            result["performance"] = "唯一活动"
            result["has_conflict"] = False

        logger.debug(f"跨活动分析 '{term}'，涉及 {len(result)} 个活动")
        return result

    def get_high_spend_zero_orders(self, threshold: float = 10.0, product_id: int = None) -> pd.DataFrame:
        """
        获取高花费零转化的搜索词

        Args:
            threshold: 花费阈值
            product_id: 产品ID（可选）

        Returns:
            符合条件的搜索词DataFrame
        """
        df = self.aggregate_by_term(product_id)

        if df.empty:
            return pd.DataFrame()

        # 筛选高花费零订单
        result = df[(df["total_spend"] >= threshold) & (df["total_orders"] == 0)]

        logger.info(f"高花费零转化词: {len(result)} 个（阈值 ${threshold}）")
        return result

    def get_high_acos_keywords(self, acos_threshold: float = 0.5, spend_threshold: float = 10.0, product_id: int = None) -> pd.DataFrame:
        """
        获取高ACOS的搜索词

        Args:
            acos_threshold: ACOS阈值
            spend_threshold: 花费阈值
            product_id: 产品ID（可选）

        Returns:
            符合条件的搜索词DataFrame
        """
        df = self.aggregate_by_term(product_id)

        if df.empty:
            return pd.DataFrame()

        # 筛选高ACOS高花费
        result = df[(df["acos"] >= acos_threshold) & (df["total_spend"] >= spend_threshold)]

        logger.info(f"高ACOS词: {len(result)} 个（ACOS>={acos_threshold}, 花费>=${spend_threshold}）")
        return result

    def get_high_conversion_keywords(self, acos_threshold: float = 0.25, min_orders: int = 3, product_id: int = None) -> pd.DataFrame:
        """
        获取高转化的搜索词

        Args:
            acos_threshold: ACOS阈值（低于此值为高转化）
            min_orders: 最小订单数
            product_id: 产品ID（可选）

        Returns:
            符合条件的搜索词DataFrame
        """
        df = self.aggregate_by_term(product_id)

        if df.empty:
            return pd.DataFrame()

        # 筛选低ACOS高订单
        result = df[(df["acos"] <= acos_threshold) & (df["acos"] > 0) & (df["total_orders"] >= min_orders)]

        logger.info(f"高转化词: {len(result)} 个（ACOS<={acos_threshold}, 订单>={min_orders}）")
        return result
