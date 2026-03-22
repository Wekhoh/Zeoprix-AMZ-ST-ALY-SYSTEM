"""
ASIN分析模块
支持多ASIN对比分析、冲突检测、跨ASIN智能分析
"""

from typing import Optional

import numpy as np
import pandas as pd

from src.analysis.truth_replay import action_type_to_label, has_reviewed_truth
from src.config.logger import get_logger
from src.data.db import Database
from src.data.models import ActionType

logger = get_logger(__name__)


class ASINAnalyzer:
    """
    ASIN分析器

    提供四个层次的分析能力:
    - 层次一: 基础汇总 (ASIN级别核心指标聚合)
    - 层次二: 对比洞察 (ASIN间胜负对比、效率排名)
    - 层次三: 决策支撑 (关键词分布、冲突检测、Top/Bottom词)
    - 层次四: 跨ASIN智能 (词效差异、互补机会、统一否词)
    """

    def __init__(self, db: Database):
        """
        初始化ASIN分析器

        Args:
            db: 数据库实例
        """
        self.db = db

    @staticmethod
    def extract_asin_identifier(campaign_name: str) -> str:
        """
        从广告活动名称提取ASIN标识

        规则: 提取第一个"-"前的部分作为ASIN标识
        例如: "BLK-1.2bid" -> "BLK", "DBL-1.88bid" -> "DBL"

        Args:
            campaign_name: 广告活动名称

        Returns:
            ASIN标识 (大写)
        """
        if not campaign_name or not isinstance(campaign_name, str):
            return "UNKNOWN"

        parts = campaign_name.split("-")
        if parts and parts[0]:
            return parts[0].strip().upper()
        return campaign_name.strip().upper()

    def get_raw_data(self, product_id: int) -> pd.DataFrame:
        """
        获取产品的原始搜索词数据

        Args:
            product_id: 产品ID

        Returns:
            原始数据DataFrame
        """
        filters = {"product_id": product_id}
        df = self.db.get_search_terms(filters)

        if df.empty:
            return pd.DataFrame()

        # 添加ASIN标识列
        df["asin_id"] = df["campaign_name"].apply(self.extract_asin_identifier)

        return df

    # ==================== 层次一: 基础汇总 ====================

    def get_asin_summary(self, product_id: int) -> pd.DataFrame:
        """
        层次一: 获取ASIN基础汇总表

        按ASIN标识聚合核心指标

        Args:
            product_id: 产品ID

        Returns:
            ASIN汇总DataFrame，包含:
            - asin_id: ASIN标识 (如 BLK, DBL)
            - impressions, clicks, spend, orders, sales
            - ctr, cvr, acos, cpc, roas
        """
        df = self.get_raw_data(product_id)

        if df.empty:
            logger.warning(f"产品 {product_id} 无数据")
            return pd.DataFrame()

        # 按ASIN标识聚合
        agg_df = (
            df.groupby("asin_id")
            .agg(
                impressions=("impressions", "sum"),
                clicks=("clicks", "sum"),
                spend=("spend", "sum"),
                orders=("orders", "sum"),
                sales=("sales", "sum"),
                term_count=("term", "nunique"),
                campaign_count=("campaign_name", "nunique"),
            )
            .reset_index()
        )

        # 计算衍生指标
        agg_df["ctr"] = (
            (agg_df["clicks"] / agg_df["impressions"])
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )
        agg_df["cvr"] = (
            (agg_df["orders"] / agg_df["clicks"])
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )
        agg_df["cpc"] = (
            (agg_df["spend"] / agg_df["clicks"]).replace([np.inf, -np.inf], 0).fillna(0)
        )
        agg_df["acos"] = (
            (agg_df["spend"] / agg_df["sales"]).replace([np.inf, -np.inf], 0).fillna(0)
        )
        agg_df["roas"] = (
            (agg_df["sales"] / agg_df["spend"]).replace([np.inf, -np.inf], 0).fillna(0)
        )

        # 按花费降序排序
        agg_df = agg_df.sort_values("spend", ascending=False)

        logger.info(f"ASIN汇总完成，共 {len(agg_df)} 个ASIN")
        return agg_df

    # ==================== 层次二: 对比洞察 ====================

    def get_comparison_insights(self, product_id: int) -> dict:
        """
        层次二: 获取ASIN对比洞察

        比较各ASIN的表现，给出胜负判断和建议

        Args:
            product_id: 产品ID

        Returns:
            dict包含:
            - metrics_comparison: 各指标的胜负对比
            - efficiency_ranking: 效率排名
            - budget_suggestion: 预算建议
        """
        summary = self.get_asin_summary(product_id)

        if summary.empty or len(summary) < 2:
            return {
                "metrics_comparison": [],
                "efficiency_ranking": [],
                "budget_suggestion": "数据不足，无法进行对比分析",
            }

        # 指标对比 (越高越好: ctr, cvr, roas; 越低越好: acos, cpc)
        higher_better = ["ctr", "cvr", "roas", "orders", "sales"]
        lower_better = ["acos", "cpc"]

        metrics_comparison = []

        for metric in higher_better:
            if metric in summary.columns:
                best_idx = summary[metric].idxmax()
                best_asin = summary.loc[best_idx, "asin_id"]

                # 格式化显示
                if metric in ["ctr", "cvr"]:
                    display_values = {
                        row["asin_id"]: f"{row[metric] * 100:.2f}%"
                        for _, row in summary.iterrows()
                    }
                elif metric in ["roas"]:
                    display_values = {
                        row["asin_id"]: f"{row[metric]:.2f}"
                        for _, row in summary.iterrows()
                    }
                else:
                    display_values = {
                        row["asin_id"]: f"{row[metric]:,.0f}"
                        for _, row in summary.iterrows()
                    }

                metrics_comparison.append(
                    {
                        "metric": metric.upper(),
                        "winner": best_asin,
                        "values": display_values,
                        "type": "higher_better",
                    }
                )

        for metric in lower_better:
            if metric in summary.columns:
                # 排除0值（无意义）
                valid = summary[summary[metric] > 0]
                if not valid.empty:
                    best_idx = valid[metric].idxmin()
                    best_asin = valid.loc[best_idx, "asin_id"]

                    if metric == "acos":
                        display_values = {
                            row["asin_id"]: f"{row[metric] * 100:.1f}%"
                            for _, row in summary.iterrows()
                        }
                    else:
                        display_values = {
                            row["asin_id"]: f"${row[metric]:.2f}"
                            for _, row in summary.iterrows()
                        }

                    metrics_comparison.append(
                        {
                            "metric": metric.upper(),
                            "winner": best_asin,
                            "values": display_values,
                            "type": "lower_better",
                        }
                    )

        # 效率排名 (按ROAS)
        efficiency_ranking = summary.sort_values("roas", ascending=False)[
            ["asin_id", "roas", "spend", "sales"]
        ].to_dict("records")

        # 预算建议
        if len(summary) >= 2:
            best_roas_asin = summary.loc[summary["roas"].idxmax(), "asin_id"]
            worst_roas_asin = summary.loc[summary["roas"].idxmin(), "asin_id"]
            budget_suggestion = (
                f"建议考虑将预算从 {worst_roas_asin} 转移到 {best_roas_asin}"
            )
        else:
            budget_suggestion = "仅有单个ASIN，无法给出预算调整建议"

        return {
            "metrics_comparison": metrics_comparison,
            "efficiency_ranking": efficiency_ranking,
            "budget_suggestion": budget_suggestion,
        }

    # ==================== 层次三: 决策支撑 ====================

    def get_keyword_distribution(
        self, product_id: int, asin_id: Optional[str] = None
    ) -> dict:
        """
        层次三: 获取关键词操作分布

        统计各ASIN的关键词操作类型分布

        Args:
            product_id: 产品ID
            asin_id: 指定ASIN标识（可选，None则返回所有ASIN的分布）

        Returns:
            dict，key为asin_id，value为操作类型计数
        """
        if has_reviewed_truth(self.db, product_id):
            from src.rules.engine import analyze_search_terms_by_asin

            distribution: dict[str, dict[str, int]] = {}
            for result in analyze_search_terms_by_asin(self.db, product_id):
                truth_data = (getattr(result, "data", {}) or {}).get("truth_replay")
                if not truth_data:
                    continue
                current_asin = getattr(result, "asin_identifier", None) or "UNKNOWN"
                if asin_id and current_asin != asin_id:
                    continue
                label = action_type_to_label(result.action_type)
                distribution.setdefault(current_asin, {})
                distribution[current_asin][label] = (
                    distribution[current_asin].get(label, 0) + 1
                )
            return distribution

        df = self.get_raw_data(product_id)

        if df.empty:
            return {}

        if asin_id:
            df = df[df["asin_id"] == asin_id]

        # 按ASIN和关键词聚合，获取每个词的汇总数据
        term_df = (
            df.groupby(["asin_id", "term", "term_type"])
            .agg(
                clicks=("clicks", "sum"),
                orders=("orders", "sum"),
                spend=("spend", "sum"),
                sales=("sales", "sum"),
            )
            .reset_index()
        )

        # 计算CVR
        term_df["cvr"] = (
            (term_df["orders"] / term_df["clicks"])
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )

        # 简单分类逻辑（实际应该用规则引擎，这里简化处理）
        def classify_action(row):
            if row["orders"] == 0 and row["spend"] >= 10:
                return "否定"
            elif row["orders"] > 0 and row["cvr"] >= 0.10:
                return "手动精准"
            elif row["orders"] > 0 and row["cvr"] < 0.05:
                return "观察"
            elif row["clicks"] < 10:
                return "样本不足"
            else:
                return "继续观察"

        term_df["action"] = term_df.apply(classify_action, axis=1)

        # 按ASIN统计分布
        result = {}
        for aid in term_df["asin_id"].unique():
            asin_terms = term_df[term_df["asin_id"] == aid]
            action_counts = asin_terms["action"].value_counts().to_dict()
            result[aid] = action_counts

        return result

    def detect_conflicts(
        self, product_id: int, asin_id: Optional[str] = None
    ) -> pd.DataFrame:
        """
        层次三: 检测同一关键词在不同广告组的决策冲突

        Args:
            product_id: 产品ID
            asin_id: 指定ASIN标识（可选）

        Returns:
            DataFrame包含冲突的关键词及各广告组的决策
        """
        if has_reviewed_truth(self.db, product_id):
            from src.rules.engine import analyze_search_terms_by_campaign

            rows = []
            for result in analyze_search_terms_by_campaign(self.db, product_id):
                truth_data = (getattr(result, "data", {}) or {}).get("truth_replay")
                if not truth_data:
                    continue
                current_asin = self.extract_asin_identifier(result.campaign_name)
                if asin_id and current_asin != asin_id:
                    continue
                rows.append(
                    {
                        "asin_id": current_asin,
                        "term": result.term,
                        "campaign_name": result.campaign_name,
                        "action_type": result.action_type,
                        "decision": action_type_to_label(result.action_type),
                        "decision_reason": result.suggested_action,
                        "clicks": int(result.clicks or 0),
                        "orders": int(result.orders or 0),
                        "spend": float(result.spend or 0),
                        "cvr": float(result.cvr or 0),
                    }
                )

            if not rows:
                return pd.DataFrame()

            def get_action_category(action_type: str) -> str:
                if ActionType.is_negative(action_type):
                    return "否定类"
                if ActionType.is_manual(action_type):
                    return "保留类"
                return "观察类"

            conflicts = []
            truth_df = pd.DataFrame(rows)
            for (aid, term), group in truth_df.groupby(["asin_id", "term"]):
                categories = {
                    get_action_category(action_type)
                    for action_type in group["action_type"].tolist()
                }
                if len(categories) <= 1:
                    continue

                if "否定类" in categories and "保留类" in categories:
                    severity = "严重"
                elif "否定类" in categories and "观察类" in categories:
                    severity = "中等"
                else:
                    severity = "轻微"

                campaign_decisions = {}
                for _, row in group.iterrows():
                    campaign_decisions[row["campaign_name"]] = {
                        "action": row["decision"],
                        "reason": row["decision_reason"],
                        "clicks": row["clicks"],
                        "orders": row["orders"],
                        "spend": row["spend"],
                        "cvr": row["cvr"],
                    }

                conflicts.append(
                    {
                        "asin_id": aid,
                        "term": term,
                        "campaign_decisions": campaign_decisions,
                        "severity": severity,
                        "campaign_count": len(group),
                    }
                )

            if not conflicts:
                return pd.DataFrame()

            return pd.DataFrame(conflicts).sort_values(
                ["severity", "asin_id", "term"],
                key=lambda x: x.map({"严重": 0, "中等": 1, "轻微": 2})
                if x.name == "severity"
                else x,
            )

        df = self.get_raw_data(product_id)

        if df.empty:
            return pd.DataFrame()

        if asin_id:
            df = df[df["asin_id"] == asin_id]

        # 按ASIN和关键词+广告活动聚合
        campaign_term_df = (
            df.groupby(["asin_id", "term", "campaign_name"])
            .agg(
                clicks=("clicks", "sum"),
                orders=("orders", "sum"),
                spend=("spend", "sum"),
                sales=("sales", "sum"),
            )
            .reset_index()
        )

        # 计算CVR
        campaign_term_df["cvr"] = (
            (campaign_term_df["orders"] / campaign_term_df["clicks"])
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )

        # 详细决策逻辑 - 返回决策类型和依据
        def get_detailed_decision(row):
            clicks = row["clicks"]
            orders = row["orders"]
            spend = row["spend"]
            cvr = row["cvr"]

            # 决策逻辑（与规则引擎对齐）
            if orders == 0 and spend >= 20:
                action = "否定精准"
                reason = f"0单/${spend:.1f}花费"
            elif orders == 0 and spend >= 10:
                action = "评估否定"
                reason = f"0单/${spend:.1f}花费"
            elif orders >= 1 and cvr >= 0.10:
                action = "手动精准"
                reason = f"{orders}单/CVR {cvr * 100:.1f}%"
            elif orders >= 1 and clicks >= 20 and cvr < 0.05:
                action = "手动精准+自动否定"
                reason = f"{orders}单/{clicks}点击/CVR {cvr * 100:.1f}%"
            elif orders >= 1 and cvr >= 0.05:
                action = "手动精准测试"
                reason = f"{orders}单/CVR {cvr * 100:.1f}%"
            elif clicks < 10:
                action = "样本不足"
                reason = f"{clicks}点击"
            else:
                action = "继续观察"
                reason = f"{clicks}点击/{orders}单"

            return action, reason

        # 应用决策逻辑
        campaign_term_df[["decision", "decision_reason"]] = campaign_term_df.apply(
            lambda row: pd.Series(get_detailed_decision(row)), axis=1
        )

        # 定义决策类别（用于冲突判断）
        negative_actions = {"否定精准", "否定词组", "评估否定", "手动精准+自动否定"}
        keep_actions = {"手动精准", "手动精准测试", "手动精准测试+自动先不否"}
        observe_actions = {"继续观察", "样本不足", "监控"}

        def get_action_category(action):
            if action in negative_actions:
                return "否定类"
            elif action in keep_actions:
                return "保留类"
            elif action in observe_actions:
                return "观察类"
            else:
                return "观察类"  # 未知决策默认为观察类

        campaign_term_df["action_category"] = campaign_term_df["decision"].apply(
            get_action_category
        )

        # 找出有多个广告活动且决策不一致的词
        conflicts = []
        for (aid, term), group in campaign_term_df.groupby(["asin_id", "term"]):
            if len(group) > 1:
                categories = group["action_category"].unique()
                if len(categories) > 1:
                    # 判断冲突严重程度
                    if "否定类" in categories and "保留类" in categories:
                        severity = "严重"
                    elif "否定类" in categories and "观察类" in categories:
                        severity = "中等"
                    else:
                        severity = "轻微"

                    # 收集各活动的详细决策（包含决策类型+依据+数据）
                    campaign_decisions = {}
                    for _, row in group.iterrows():
                        campaign_decisions[row["campaign_name"]] = {
                            "action": row["decision"],
                            "reason": row["decision_reason"],
                            "clicks": int(row["clicks"]),
                            "orders": int(row["orders"]),
                            "spend": float(row["spend"]),
                            "cvr": float(row["cvr"]),
                        }

                    conflicts.append(
                        {
                            "asin_id": aid,
                            "term": term,
                            "campaign_decisions": campaign_decisions,
                            "severity": severity,
                            "campaign_count": len(group),
                        }
                    )

        if not conflicts:
            return pd.DataFrame()

        result = pd.DataFrame(conflicts)
        result = result.sort_values(
            ["severity", "asin_id"],
            key=lambda x: x.map({"严重": 0, "中等": 1, "轻微": 2})
            if x.name == "severity"
            else x,
        )

        logger.info(f"检测到 {len(result)} 个冲突关键词")
        return result

    def get_top_bottom_keywords(
        self, product_id: int, asin_id: Optional[str] = None, n: int = 5
    ) -> dict:
        """
        层次三: 获取各ASIN的Top/Bottom表现关键词

        Args:
            product_id: 产品ID
            asin_id: 指定ASIN标识（可选）
            n: 返回数量

        Returns:
            dict，key为asin_id，value包含top和bottom列表
        """
        df = self.get_raw_data(product_id)

        if df.empty:
            return {}

        if asin_id:
            df = df[df["asin_id"] == asin_id]

        # 按ASIN和关键词聚合
        term_df = (
            df.groupby(["asin_id", "term"])
            .agg(
                clicks=("clicks", "sum"),
                orders=("orders", "sum"),
                spend=("spend", "sum"),
                sales=("sales", "sum"),
            )
            .reset_index()
        )

        # 计算指标
        term_df["cvr"] = (
            (term_df["orders"] / term_df["clicks"])
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )
        term_df["acos"] = (
            (term_df["spend"] / term_df["sales"])
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )

        result = {}
        for aid in term_df["asin_id"].unique():
            asin_terms = term_df[term_df["asin_id"] == aid].copy()

            # Top: 有订单且CVR高
            top_terms = asin_terms[asin_terms["orders"] > 0].nlargest(n, "cvr")
            top_list = [
                {
                    "term": row["term"],
                    "cvr": row["cvr"],
                    "orders": row["orders"],
                    "spend": row["spend"],
                }
                for _, row in top_terms.iterrows()
            ]

            # Bottom: 高花费低转化
            bottom_terms = asin_terms[
                (asin_terms["spend"] >= 5) & (asin_terms["orders"] == 0)
            ].nlargest(n, "spend")
            bottom_list = [
                {"term": row["term"], "cvr": 0, "orders": 0, "spend": row["spend"]}
                for _, row in bottom_terms.iterrows()
            ]

            result[aid] = {"top": top_list, "bottom": bottom_list}

        return result

    # ==================== 层次四: 跨ASIN智能分析 ====================

    def cross_asin_analysis(self, product_id: int) -> dict:
        """
        层次四: 跨ASIN智能分析

        分析同一关键词在不同ASIN间的表现差异，
        找出互补机会和统一否词建议

        Args:
            product_id: 产品ID

        Returns:
            dict包含:
            - performance_diff: 词效差异分析
            - complementary: 互补机会
            - unified_negation: 统一否词建议
        """
        df = self.get_raw_data(product_id)

        if df.empty:
            return {
                "performance_diff": [],
                "complementary": {"unique_good": {}, "expansion_suggestions": []},
                "unified_negation": [],
            }

        asin_ids = df["asin_id"].unique()

        if len(asin_ids) < 2:
            return {
                "performance_diff": [],
                "complementary": {"unique_good": {}, "expansion_suggestions": []},
                "unified_negation": [],
                "message": "仅有单个ASIN，无法进行跨ASIN分析",
            }

        # 按ASIN和关键词聚合
        term_df = (
            df.groupby(["asin_id", "term"])
            .agg(
                clicks=("clicks", "sum"),
                orders=("orders", "sum"),
                spend=("spend", "sum"),
                sales=("sales", "sum"),
            )
            .reset_index()
        )

        term_df["cvr"] = (
            (term_df["orders"] / term_df["clicks"])
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )

        # 1. 词效差异分析
        performance_diff = []
        all_terms = term_df["term"].unique()

        for term in all_terms:
            term_data = term_df[term_df["term"] == term]
            if len(term_data) >= 2:
                # 同一词在多个ASIN都有数据
                cvr_values = term_data.set_index("asin_id")["cvr"].to_dict()

                # 找出CVR差异大的
                cvr_list = list(cvr_values.values())
                if len(cvr_list) >= 2 and max(cvr_list) > 0:
                    diff_ratio = (
                        (max(cvr_list) - min(cvr_list)) / max(cvr_list)
                        if max(cvr_list) > 0
                        else 0
                    )
                    if diff_ratio > 0.3:  # CVR差异超过30%
                        best_asin = max(cvr_values, key=cvr_values.get)
                        worst_asin = min(cvr_values, key=cvr_values.get)
                        performance_diff.append(
                            {
                                "term": term,
                                "best_asin": best_asin,
                                "best_cvr": cvr_values[best_asin],
                                "worst_asin": worst_asin,
                                "worst_cvr": cvr_values[worst_asin],
                                "diff_ratio": diff_ratio,
                            }
                        )

        # 按差异程度排序
        performance_diff.sort(key=lambda x: x["diff_ratio"], reverse=True)

        # 2. 互补机会分析
        unique_good = {}  # 每个ASIN独有的高效词
        for aid in asin_ids:
            asin_terms = term_df[(term_df["asin_id"] == aid) & (term_df["orders"] > 0)]
            other_asins_terms = set(term_df[term_df["asin_id"] != aid]["term"].unique())

            unique_terms = []
            for _, row in asin_terms.iterrows():
                if (
                    row["term"] not in other_asins_terms
                    or term_df[
                        (term_df["term"] == row["term"]) & (term_df["asin_id"] != aid)
                    ]["orders"].sum()
                    == 0
                ):
                    unique_terms.append(
                        {
                            "term": row["term"],
                            "orders": row["orders"],
                            "cvr": row["cvr"],
                        }
                    )

            if unique_terms:
                unique_good[aid] = sorted(
                    unique_terms, key=lambda x: x["orders"], reverse=True
                )[:5]

        # 生成扩展建议
        expansion_suggestions = []
        for aid, terms in unique_good.items():
            other_asins = [a for a in asin_ids if a != aid]
            for term_info in terms:
                for other_aid in other_asins:
                    expansion_suggestions.append(
                        {
                            "from_asin": aid,
                            "to_asin": other_aid,
                            "term": term_info["term"],
                            "source_orders": term_info["orders"],
                        }
                    )

        # 3. 统一否词建议
        unified_negation = []
        for term in all_terms:
            term_data = term_df[term_df["term"] == term]
            if len(term_data) >= 2:
                # 所有ASIN都有数据且都无转化
                total_orders = term_data["orders"].sum()
                total_spend = term_data["spend"].sum()
                if total_orders == 0 and total_spend >= 10:
                    unified_negation.append(
                        {
                            "term": term,
                            "total_spend": total_spend,
                            "asin_count": len(term_data),
                            "asins": term_data["asin_id"].tolist(),
                        }
                    )

        # 按花费排序
        unified_negation.sort(key=lambda x: x["total_spend"], reverse=True)

        return {
            "performance_diff": performance_diff[:10],  # 返回前10个差异最大的
            "complementary": {
                "unique_good": unique_good,
                "expansion_suggestions": expansion_suggestions[:10],
            },
            "unified_negation": unified_negation[:20],  # 返回前20个统一否词建议
        }

    def get_all_asin_ids(self, product_id: int) -> list:
        """
        获取产品下所有的ASIN标识列表

        Args:
            product_id: 产品ID

        Returns:
            ASIN标识列表
        """
        df = self.get_raw_data(product_id)
        if df.empty:
            return []
        return sorted(df["asin_id"].unique().tolist())
