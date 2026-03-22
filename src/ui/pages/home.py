"""
首页/仪表盘
展示关键指标和快速入口
"""

import altair as alt
import pandas as pd
import streamlit as st

from src.analysis.truth_replay import (
    get_truth_first_overview_distribution,
    get_truth_first_pending_stats,
)
from src.config.logger import get_logger
from src.rules.engine import analyze_search_terms

logger = get_logger(__name__)


# 缓存时间（秒）
CACHE_TTL = 60


def _build_overview_chart(chart_data: dict[str, int]) -> alt.Chart:
    """构建首页概览柱状图。"""
    df = pd.DataFrame(
        {
            "分类": list(chart_data.keys()),
            "数量": list(chart_data.values()),
        }
    )

    return (
        alt.Chart(df)
        .mark_bar(
            color="#2563EB",
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=alt.X(
                "分类:N",
                axis=alt.Axis(
                    labelAngle=0,
                    labelFontSize=12,
                    titleFontSize=13,
                    titleFontWeight="bold",
                ),
                sort=alt.EncodingSortField(field="数量", order="descending"),
            ),
            y=alt.Y(
                "数量:Q",
                axis=alt.Axis(
                    labelFontSize=11,
                    titleFontSize=13,
                    titleFontWeight="bold",
                ),
            ),
            tooltip=["分类", "数量"],
        )
        .properties(height=350)
        .configure_view(strokeWidth=0)
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_all_dashboard_data(_db, product_id: int = None) -> dict:
    """
    批量获取仪表盘所有统计数据（减少数据库往返次数）

    Args:
        _db: 数据库连接（前缀_表示不参与缓存key计算）
        product_id: 产品ID

    Returns:
        包含 dashboard_stats, pending_stats, rule_stats 的字典
    """
    dashboard_stats = _get_dashboard_stats_impl(_db, product_id)
    pending_stats = _get_pending_stats_impl(_db, product_id)
    overview_chart = (
        _get_overview_chart_impl(_db, product_id)
        if dashboard_stats["term_count"] > 0
        else {"x_label": "规则", "title": "数据概览", "data": {}}
    )

    return {
        "dashboard_stats": dashboard_stats,
        "pending_stats": pending_stats,
        "overview_chart": overview_chart,
    }


def render_home():
    """渲染首页"""
    st.title("搜索词分析仪表盘")

    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    # 批量获取所有统计数据（单次缓存调用替代3次独立查询）
    all_data = get_all_dashboard_data(db, product_id)
    stats = all_data["dashboard_stats"]

    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="总花费",
            value=f"${stats['total_spend']:.2f}",
            delta=None,
        )

    with col2:
        st.metric(
            label="总订单",
            value=f"{stats['total_orders']}",
            delta=None,
        )

    with col3:
        st.metric(
            label="整体ACOS",
            value=f"{stats['acos']:.2%}" if stats["acos"] > 0 else "N/A",
            delta=None,
        )

    with col4:
        st.metric(
            label="搜索词数",
            value=f"{stats['term_count']}",
            delta=None,
        )

    st.divider()

    # 待处理项
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("待处理项")

        pending_stats = all_data["pending_stats"]

        if pending_stats["negative_count"] > 0:
            st.warning(f"{pending_stats['negative_count']} 个词需要否定")

        if pending_stats["manual_count"] > 0:
            st.success(f"{pending_stats['manual_count']} 个高转化词待投放")

        if pending_stats["ai_pending_count"] > 0:
            st.info(f"{pending_stats['ai_pending_count']} 个词待AI确认")

        # v2.0: 显示待审核相关性的词
        if pending_stats.get("review_pending_count", 0) > 0:
            st.info(f"{pending_stats['review_pending_count']} 个词待审核相关性")

        if sum(pending_stats.values()) == 0:
            st.success("暂无待处理项")

    with col_right:
        st.subheader("快速操作")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("上传新数据", width="stretch"):
                st.session_state.nav_page = "文件上传"
                st.rerun()

            if st.button("查看操作清单", width="stretch"):
                st.session_state.nav_page = "操作清单"
                st.rerun()

            # v2.0: 相关性审核入口
            if st.button("相关性审核", width="stretch"):
                st.session_state.nav_page = "相关性审核"
                st.rerun()

        with col_btn2:
            if st.button("分析搜索词", width="stretch"):
                st.session_state.nav_page = "搜索词分析"
                st.rerun()

            if st.button("系统设置", width="stretch"):
                st.session_state.nav_page = "系统设置"
                st.rerun()

    st.divider()

    overview_chart = all_data["overview_chart"]
    st.subheader(overview_chart.get("title", "数据概览"))

    if stats["term_count"] > 0:
        chart_data = {
            key: value
            for key, value in overview_chart.get("data", {}).items()
            if value > 0
        }

        if chart_data:
            chart = _build_overview_chart(chart_data)
            st.altair_chart(chart, width="stretch")
    else:
        st.info("暂无数据，请先上传搜索词报告")


def _get_dashboard_stats_impl(db, product_id: int = None) -> dict:
    """获取仪表盘统计数据（内部实现）"""
    try:
        # search_terms 表没有 product_id，需要通过 campaigns 关联
        if product_id:
            query = """
                SELECT
                    COUNT(DISTINCT st.term) as term_count,
                    COALESCE(SUM(st.spend), 0) as total_spend,
                    COALESCE(SUM(st.orders), 0) as total_orders,
                    COALESCE(SUM(st.sales), 0) as total_sales
                FROM search_terms st
                JOIN campaigns c ON st.campaign_id = c.id
                WHERE c.product_id = ?
            """
            params = (product_id,)
        else:
            query = """
                SELECT
                    COUNT(DISTINCT term) as term_count,
                    COALESCE(SUM(spend), 0) as total_spend,
                    COALESCE(SUM(orders), 0) as total_orders,
                    COALESCE(SUM(sales), 0) as total_sales
                FROM search_terms
            """
            params = ()

        cursor = db.execute(query, params)
        row = cursor.fetchone()

        if not row:
            return {
                "term_count": 0,
                "total_spend": 0,
                "total_orders": 0,
                "total_sales": 0,
                "acos": 0,
            }

        total_spend = row["total_spend"] or 0
        total_sales = row["total_sales"] or 0

        return {
            "term_count": row["term_count"] or 0,
            "total_spend": total_spend,
            "total_orders": row["total_orders"] or 0,
            "total_sales": total_sales,
            "acos": total_spend / total_sales if total_sales > 0 else 0,
        }
    except Exception as e:
        logger.error(f"获取仪表盘统计失败: {e}")
        return {
            "term_count": 0,
            "total_spend": 0,
            "total_orders": 0,
            "total_sales": 0,
            "acos": 0,
        }


def _get_pending_stats_impl(db, product_id: int = None) -> dict:
    """获取待处理项统计（使用实时分析结果）"""
    try:
        truth_stats = get_truth_first_pending_stats(db, product_id)
        if truth_stats is not None:
            return truth_stats

        # 使用规则引擎实时分析，与搜索词分析页面保持一致
        results = analyze_search_terms(db, product_id)

        stats = {
            "negative_count": 0,
            "manual_count": 0,
            "ai_pending_count": 0,
            "review_pending_count": 0,  # v2.0: 待审核相关性词数
        }

        for result in results:
            # action_type 可能是 negative_exact, negative_phrase, manual_exact 等
            action = result.action_type or ""
            if action.startswith("negative"):
                stats["negative_count"] += 1
            elif action.startswith("manual"):
                stats["manual_count"] += 1
            # 用 confidence < 1.0 判断是否需要AI确认
            if result.confidence < 1.0:
                stats["ai_pending_count"] += 1
            # v2.0: 统计需要审核相关性的词
            if getattr(result, "needs_review", False):
                stats["review_pending_count"] += 1

        return stats
    except Exception as e:
        logger.error(f"获取待处理统计失败: {e}")
        return {
            "negative_count": 0,
            "manual_count": 0,
            "ai_pending_count": 0,
            "review_pending_count": 0,  # v2.0: 待审核相关性词数
        }


def _get_overview_chart_impl(db, product_id: int = None) -> dict:
    """获取首页数据概览图表数据。"""
    try:
        truth_distribution = get_truth_first_overview_distribution(db, product_id)
        if truth_distribution is not None:
            return {
                "x_label": "分类",
                "title": "数据概览（真相优先）",
                "data": truth_distribution,
            }

        # 使用规则引擎实时分析，与搜索词分析页面保持一致
        results = analyze_search_terms(db, product_id)

        rule_counts = {}
        for result in results:
            rule = result.triggered_rule
            rule_counts[rule] = rule_counts.get(rule, 0) + 1

        # 按数量降序排列，取前10
        sorted_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]
        return {
            "x_label": "规则",
            "title": "数据概览",
            "data": dict(sorted_rules),
        }
    except Exception as e:
        logger.error(f"获取规则统计失败: {e}")
        return {"x_label": "规则", "title": "数据概览", "data": {}}


# 公开API（向后兼容）
def get_dashboard_stats(db, product_id: int = None) -> dict:
    """获取仪表盘统计数据（公开API，用于测试）"""
    return _get_dashboard_stats_impl(db, product_id)


def get_pending_stats(db, product_id: int = None) -> dict:
    """获取待处理项统计（公开API，用于测试）"""
    return _get_pending_stats_impl(db, product_id)


def get_rule_stats(db, product_id: int = None) -> dict:
    """获取首页数据概览图表分布（公开API，用于测试）"""
    return _get_overview_chart_impl(db, product_id)["data"]
