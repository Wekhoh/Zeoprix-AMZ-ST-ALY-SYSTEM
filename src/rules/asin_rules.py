"""
ASIN规则模块
处理竞品ASIN的识别和分析
"""

import re
from dataclasses import dataclass

import pandas as pd

from src.config.logger import get_logger

logger = get_logger(__name__)

# ============ ASIN常量配置 ============
# 北美站ASIN前缀（可扩展支持其他站点）
ASIN_PREFIX = "B0"
# ASIN总长度（前缀 + 8位字母数字）
ASIN_LENGTH = 10
# ASIN格式正则：B0开头，共10位字母数字
ASIN_PATTERN = re.compile(rf"^{ASIN_PREFIX}[A-Z0-9]{{{ASIN_LENGTH - len(ASIN_PREFIX)}}}$")

# ============ 分析阈值配置 ============
# ACOS阈值：低于此值认为投放效果好
GOOD_ACOS_THRESHOLD = 0.3
# 花费阈值：高于此值且无订单则建议否定
HIGH_SPEND_THRESHOLD = 10.0
# 洞察报告中的Top/Bottom数量
INSIGHT_TOP_COUNT = 5


@dataclass
class ASINAnalysis:
    """ASIN分析结果"""

    asin: str
    is_valid: bool
    is_own: bool
    is_competitor: bool
    performance: dict
    suggested_action: str


def is_valid_asin(term: str) -> bool:
    """检查是否是有效的ASIN格式"""
    return bool(ASIN_PATTERN.match(term.upper()))


def analyze_asin(row: pd.Series, config: dict) -> ASINAnalysis | None:
    """
    分析ASIN搜索词

    Args:
        row: 数据行
        config: 产品配置

    Returns:
        ASIN分析结果
    """
    term = str(row.get("term", "")).upper()

    if not is_valid_asin(term):
        return None

    own_asins = [a.upper() for a in config.get("own_asins", [])]
    is_own = term in own_asins

    # 计算表现指标
    performance = {
        "impressions": row.get("total_impressions", row.get("impressions", 0)),
        "clicks": row.get("total_clicks", row.get("clicks", 0)),
        "spend": row.get("total_spend", row.get("spend", 0)),
        "orders": row.get("total_orders", row.get("orders", 0)),
        "sales": row.get("total_sales", row.get("sales", 0)),
        "acos": row.get("acos", 0),
    }

    # 确定建议动作
    if is_own:
        suggested_action = "保留"  # 自己的ASIN，继续投放
    else:
        # 竞品ASIN分析
        if performance["orders"] > 0:
            if performance["acos"] < GOOD_ACOS_THRESHOLD:
                suggested_action = "保留投放"  # 投放竞品效果好
            else:
                suggested_action = "评估"  # 效果一般，需评估
        else:
            if performance["spend"] > HIGH_SPEND_THRESHOLD:
                suggested_action = "否定"  # 高花费无转化
            else:
                suggested_action = "监控"  # 低花费，继续观察

    return ASINAnalysis(
        asin=term,
        is_valid=True,
        is_own=is_own,
        is_competitor=not is_own,
        performance=performance,
        suggested_action=suggested_action,
    )


def classify_asins(df: pd.DataFrame, config: dict) -> dict:
    """
    对ASIN类型的搜索词进行分类

    Args:
        df: 包含ASIN搜索词的DataFrame
        config: 产品配置

    Returns:
        分类结果字典
    """
    asin_df = df[df["term_type"] == "asin"].copy()

    if asin_df.empty:
        return {
            "own_asins": [],
            "competitor_asins": [],
            "negative_asins": [],
            "watch_asins": [],
        }

    results = {
        "own_asins": [],
        "competitor_asins": [],
        "negative_asins": [],
        "watch_asins": [],
    }

    for _, row in asin_df.iterrows():
        analysis = analyze_asin(row, config)
        if not analysis:
            continue

        if analysis.is_own:
            results["own_asins"].append(analysis)
        else:
            results["competitor_asins"].append(analysis)

            if analysis.suggested_action == "否定":
                results["negative_asins"].append(analysis)
            elif analysis.suggested_action in ["监控", "评估"]:
                results["watch_asins"].append(analysis)

    logger.info(
        f"ASIN分类完成: 自有{len(results['own_asins'])}个, "
        f"竞品{len(results['competitor_asins'])}个, "
        f"建议否定{len(results['negative_asins'])}个"
    )

    return results


def get_competitor_insights(competitor_asins: list[ASINAnalysis]) -> dict:
    """
    获取竞品ASIN洞察

    Args:
        competitor_asins: 竞品ASIN分析结果列表

    Returns:
        洞察字典
    """
    if not competitor_asins:
        return {
            "total_count": 0,
            "total_spend": 0,
            "total_orders": 0,
            "avg_acos": 0,
            "top_performers": [],
            "worst_performers": [],
        }

    total_spend = sum(a.performance["spend"] for a in competitor_asins)
    total_orders = sum(a.performance["orders"] for a in competitor_asins)

    # 计算平均ACOS（排除无销售的）
    acos_values = [a.performance["acos"] for a in competitor_asins if a.performance["acos"] > 0]
    avg_acos = sum(acos_values) / len(acos_values) if acos_values else 0

    # 按订单排序找出表现最好和最差的
    sorted_by_orders = sorted(competitor_asins, key=lambda a: a.performance["orders"], reverse=True)

    return {
        "total_count": len(competitor_asins),
        "total_spend": total_spend,
        "total_orders": total_orders,
        "avg_acos": avg_acos,
        "top_performers": sorted_by_orders[:INSIGHT_TOP_COUNT],
        "worst_performers": sorted_by_orders[-INSIGHT_TOP_COUNT:] if len(sorted_by_orders) > INSIGHT_TOP_COUNT else [],
    }
