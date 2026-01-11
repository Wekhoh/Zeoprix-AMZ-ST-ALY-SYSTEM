"""
规则引擎核心模块
根据配置的规则分析搜索词数据
"""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.config.logger import get_logger
from src.data.db import Database

logger = get_logger(__name__)


# 置信度常量
class Confidence:
    """规则分析置信度常量"""
    FULL = 1.0  # 完全确定（规则直接匹配）
    AI_JUDGMENT = 0.7  # 需要AI判断
    DEFAULT = 0.5  # 默认值（无规则匹配）


@dataclass
class AnalysisResult:
    """分析结果"""

    term: str
    term_type: str
    triggered_rule: str
    suggested_action: str
    action_type: str
    confidence: float = 1.0
    need_ai_judgment: bool = False
    has_conflict: bool = False
    ai_reasoning: str = None
    data: dict = field(default_factory=dict)


class RuleEngine:
    """规则引擎"""

    def __init__(self, db: Database, product_id: int = None):
        """
        初始化规则引擎

        Args:
            db: 数据库实例
            product_id: 产品ID（用于加载产品特定规则）
        """
        self.db = db
        self.product_id = product_id
        self.rules = self._load_rules()
        self.product_config = self._load_product_config()

    def _load_rules(self) -> list[dict]:
        """加载规则配置（按优先级排序）"""
        rules = self.db.get_rules(self.product_id)
        logger.debug(f"加载 {len(rules)} 条规则")
        return rules

    def _load_product_config(self) -> dict:
        """加载产品配置"""
        if self.product_id:
            product = self.db.get_product(self.product_id)
            if product:
                return product.get("config", {})
        return {}

    def analyze(self, df: pd.DataFrame) -> list[AnalysisResult]:
        """
        分析数据，返回分析结果列表

        Args:
            df: 聚合后的搜索词DataFrame

        Returns:
            分析结果列表
        """
        if df.empty:
            return []

        results = []

        for _, row in df.iterrows():
            result = self._analyze_row(row)
            if result:
                results.append(result)

        logger.info(f"分析完成，生成 {len(results)} 条结果")
        return results

    def _analyze_row(self, row: pd.Series) -> AnalysisResult | None:
        """
        分析单条数据

        使用 first-match-wins 策略：按优先级遍历规则，
        第一个匹配的规则生成结果，后续规则不再检查。
        """
        term = row.get("term", "")
        term_type = row.get("term_type", "keyword")

        # 按优先级遍历规则（优先级数值越小越先检查）
        for rule in self.rules:
            if self._match_rule(row, rule):
                logger.debug(
                    f"搜索词 '{term}' 匹配规则 '{rule.get('name')}' "
                    f"(优先级: {rule.get('priority')})"
                )
                return self._create_result(row, rule)

        # 没有匹配任何规则，标记为观察
        logger.debug(f"搜索词 '{term}' 无匹配规则，标记为观察")
        return AnalysisResult(
            term=term,
            term_type=term_type,
            triggered_rule="无匹配规则",
            suggested_action="观察",
            action_type="observe",
            confidence=Confidence.DEFAULT,
            data=row.to_dict(),
        )

    def _match_rule(self, row: pd.Series, rule: dict) -> bool:
        """
        检查单条数据是否匹配规则

        Args:
            row: 数据行
            rule: 规则配置

        Returns:
            是否匹配
        """
        conditions = rule.get("conditions", {})
        term_type = row.get("term_type", "keyword")
        rule_type = rule.get("rule_type", "keyword")

        # 安全检查：空条件规则不应匹配任何数据
        if not conditions:
            logger.warning(
                f"规则 '{rule.get('name')}' 没有定义任何条件，跳过匹配"
            )
            return False

        # 类型不匹配跳过
        if rule_type != term_type and rule_type != "all":
            return False

        # 检查各种条件
        spend = row.get("total_spend", row.get("spend", 0))
        orders = row.get("total_orders", row.get("orders", 0))
        acos = row.get("acos", 0)
        clicks = row.get("total_clicks", row.get("clicks", 0))

        # 花费条件
        if "spend_min" in conditions and spend < conditions["spend_min"]:
            return False

        # 订单条件
        if "orders_max" in conditions and orders > conditions["orders_max"]:
            return False
        if "orders_min" in conditions and orders < conditions["orders_min"]:
            return False

        # ACOS条件
        if "acos_min" in conditions and acos < conditions["acos_min"]:
            return False
        if "acos_max" in conditions and acos > conditions["acos_max"]:
            return False

        # 需要AI判断的规则
        if conditions.get("need_ai_judgment"):
            # 检查是否在核心关键词列表中
            core_keywords = self.product_config.get("core_keywords", [])
            term = row.get("term", "")
            if term.lower() in [k.lower() for k in core_keywords]:
                return False  # 核心关键词不需要AI判断

        # 竞品ASIN条件
        if conditions.get("is_competitor"):
            term = row.get("term", "")
            own_asins = self.product_config.get("own_asins", [])
            if term in own_asins:
                return False  # 自己的ASIN不是竞品

        return True

    def _create_result(self, row: pd.Series, rule: dict) -> AnalysisResult:
        """根据规则创建分析结果"""
        conditions = rule.get("conditions", {})
        need_ai = conditions.get("need_ai_judgment", False)

        return AnalysisResult(
            term=row.get("term", ""),
            term_type=row.get("term_type", "keyword"),
            triggered_rule=rule.get("name", ""),
            suggested_action=rule.get("action", ""),
            action_type=self._get_action_type(rule.get("action", "")),
            confidence=Confidence.AI_JUDGMENT if need_ai else Confidence.FULL,
            need_ai_judgment=need_ai,
            has_conflict=row.get("has_conflict", False) if "has_conflict" in row else False,
            data=row.to_dict(),
        )

    def _get_action_type(self, action: str) -> str:
        """根据建议动作确定动作类型"""
        action_lower = action.lower()

        if "否定" in action or "negative" in action_lower:
            return "negative"
        elif "手动" in action or "manual" in action_lower:
            return "manual"
        elif "监控" in action or "observe" in action_lower or "watch" in action_lower:
            return "observe"
        elif "评估" in action or "evaluate" in action_lower:
            return "evaluate"
        else:
            return "other"

    def get_negative_keywords(self, results: list[AnalysisResult]) -> list[AnalysisResult]:
        """获取需要否定的关键词"""
        return [r for r in results if r.action_type == "negative"]

    def get_manual_keywords(self, results: list[AnalysisResult]) -> list[AnalysisResult]:
        """获取推荐手动投放的关键词"""
        return [r for r in results if r.action_type == "manual"]

    def get_ai_pending(self, results: list[AnalysisResult]) -> list[AnalysisResult]:
        """获取需要AI判断的结果"""
        return [r for r in results if r.need_ai_judgment or r.has_conflict]


def analyze_search_terms(db: Database, product_id: int = None) -> list[AnalysisResult]:
    """便捷函数：分析搜索词"""
    from src.data.aggregator import DataAggregator

    # 获取聚合数据
    aggregator = DataAggregator(db)
    df = aggregator.aggregate_by_term(product_id)

    # 规则分析
    engine = RuleEngine(db, product_id)
    return engine.analyze(df)
