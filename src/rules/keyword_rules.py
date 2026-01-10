"""
关键词规则定义
定义各种关键词分析规则的逻辑
"""

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from src.config.logger import get_logger

logger = get_logger(__name__)


@dataclass
class KeywordRule:
    """关键词规则"""

    name: str
    rule_type: str
    priority: int
    condition: Callable[[pd.Series, dict], bool]
    action: str
    description: str


def high_spend_zero_orders(row: pd.Series, config: dict) -> bool:
    """
    高花费零转化规则

    条件：花费超过阈值但订单为0
    """
    threshold = config.get("spend_threshold", 10.0)
    spend = row.get("total_spend", row.get("spend", 0))
    orders = row.get("total_orders", row.get("orders", 0))

    return spend >= threshold and orders == 0


def low_conversion_high_spend(row: pd.Series, config: dict) -> bool:
    """
    低转化高花费规则

    条件：ACOS过高且花费超过阈值
    """
    acos_threshold = config.get("acos_threshold", 0.5)
    spend_threshold = config.get("spend_threshold", 15.0)

    spend = row.get("total_spend", row.get("spend", 0))
    acos = row.get("acos", 0)

    return acos >= acos_threshold and spend >= spend_threshold


def high_conversion(row: pd.Series, config: dict) -> bool:
    """
    高转化规则

    条件：ACOS低于阈值且订单达到最小数量
    """
    acos_threshold = config.get("acos_threshold", 0.25)
    min_orders = config.get("min_orders", 3)

    acos = row.get("acos", 0)
    orders = row.get("total_orders", row.get("orders", 0))

    # ACOS必须大于0（有销售）且小于阈值
    return 0 < acos <= acos_threshold and orders >= min_orders


def low_relevance(row: pd.Series, config: dict) -> bool:
    """
    低相关性规则

    条件：不在核心关键词列表中
    注意：此规则需要AI进一步判断
    """
    core_keywords = config.get("core_keywords", [])
    related_keywords = config.get("related_keywords", [])
    term = str(row.get("term", "")).lower()

    # 如果在核心或相关词列表中，不触发此规则
    all_known = [k.lower() for k in core_keywords + related_keywords]

    if term in all_known:
        return False

    # 检查是否包含任何核心词
    for keyword in core_keywords:
        if keyword.lower() in term:
            return False

    # 需要AI进一步判断
    return True


def conflict_detection(row: pd.Series, config: dict) -> bool:
    """
    分歧检测规则

    条件：同一关键词在多个活动中表现差异大
    """
    # 检查是否有分歧标记
    has_conflict = row.get("has_conflict", False)
    campaign_count = row.get("campaign_count", 1)

    return has_conflict or campaign_count > 1


def is_competitor_asin(row: pd.Series, config: dict) -> bool:
    """
    竞品ASIN规则

    条件：是ASIN类型且不是自己的ASIN
    """
    term_type = row.get("term_type", "keyword")
    if term_type != "asin":
        return False

    term = row.get("term", "")
    own_asins = config.get("own_asins", [])

    return term not in own_asins


# 预定义规则列表
KEYWORD_RULES = [
    KeywordRule(
        name="高花费零转化",
        rule_type="keyword",
        priority=10,
        condition=high_spend_zero_orders,
        action="精确否定",
        description="花费超过阈值但没有产生任何订单的搜索词",
    ),
    KeywordRule(
        name="低转化高花费",
        rule_type="keyword",
        priority=20,
        condition=low_conversion_high_spend,
        action="评估否定",
        description="ACOS过高且花费超过阈值的搜索词",
    ),
    KeywordRule(
        name="高转化词",
        rule_type="keyword",
        priority=30,
        condition=high_conversion,
        action="手动投放",
        description="ACOS低于阈值且有足够订单的高转化搜索词",
    ),
    KeywordRule(
        name="低相关性",
        rule_type="keyword",
        priority=40,
        condition=low_relevance,
        action="短语否定",
        description="与产品可能不相关的搜索词，需AI确认",
    ),
    KeywordRule(
        name="分歧处理",
        rule_type="keyword",
        priority=50,
        condition=conflict_detection,
        action="待AI分析",
        description="在多个活动中表现差异大的搜索词",
    ),
]

ASIN_RULES = [
    KeywordRule(
        name="竞品ASIN",
        rule_type="asin",
        priority=50,
        condition=is_competitor_asin,
        action="监控",
        description="竞争对手的ASIN",
    ),
]


def get_all_rules() -> list[KeywordRule]:
    """获取所有规则"""
    return KEYWORD_RULES + ASIN_RULES


def apply_rules(row: pd.Series, config: dict) -> tuple[str, str] | None:
    """
    应用规则到单行数据

    Args:
        row: 数据行
        config: 产品配置

    Returns:
        (规则名称, 建议动作) 或 None
    """
    all_rules = get_all_rules()

    # 按优先级排序
    all_rules.sort(key=lambda r: r.priority)

    term_type = row.get("term_type", "keyword")

    for rule in all_rules:
        # 类型匹配
        if rule.rule_type != term_type and rule.rule_type != "all":
            continue

        # 条件匹配
        if rule.condition(row, config):
            return rule.name, rule.action

    return None
