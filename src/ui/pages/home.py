"""
首页/仪表盘
展示关键指标和快速入口
"""

import streamlit as st

from src.config.logger import get_logger

logger = get_logger(__name__)


def render_home():
    """渲染首页"""
    st.title("📊 搜索词分析仪表盘")

    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    # 获取统计数据
    stats = get_dashboard_stats(db, product_id)

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
            value=f"{stats['acos']:.1%}" if stats['acos'] > 0 else "N/A",
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
        st.subheader("⚠️ 待处理项")

        pending_stats = get_pending_stats(db, product_id)

        if pending_stats["negative_count"] > 0:
            st.warning(f"🔴 {pending_stats['negative_count']} 个词需要否定")

        if pending_stats["manual_count"] > 0:
            st.success(f"🟢 {pending_stats['manual_count']} 个高转化词待投放")

        if pending_stats["ai_pending_count"] > 0:
            st.info(f"🤖 {pending_stats['ai_pending_count']} 个词待AI确认")

        if sum(pending_stats.values()) == 0:
            st.success("✅ 暂无待处理项")

    with col_right:
        st.subheader("🚀 快速操作")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("📤 上传新数据", use_container_width=True):
                st.session_state.page = "文件上传"
                st.rerun()

            if st.button("📋 查看操作清单", use_container_width=True):
                st.session_state.page = "操作清单"
                st.rerun()

        with col_btn2:
            if st.button("🔍 分析搜索词", use_container_width=True):
                st.session_state.page = "搜索词分析"
                st.rerun()

            if st.button("⚙️ 系统设置", use_container_width=True):
                st.session_state.page = "系统设置"
                st.rerun()

    st.divider()

    # 最近活动
    st.subheader("📈 数据概览")

    if stats["term_count"] > 0:
        # 按规则分类统计
        rule_stats = get_rule_stats(db, product_id)

        if rule_stats:
            chart_data = {
                "规则": list(rule_stats.keys()),
                "数量": list(rule_stats.values()),
            }
            st.bar_chart(chart_data, x="规则", y="数量")
    else:
        st.info("暂无数据，请先上传搜索词报告")


def get_dashboard_stats(db, product_id: int = None) -> dict:
    """获取仪表盘统计数据"""
    try:
        query = """
            SELECT
                COUNT(DISTINCT term) as term_count,
                COALESCE(SUM(spend), 0) as total_spend,
                COALESCE(SUM(orders), 0) as total_orders,
                COALESCE(SUM(sales), 0) as total_sales
            FROM search_terms
        """
        params = ()

        if product_id:
            query += " WHERE product_id = ?"
            params = (product_id,)

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


def get_pending_stats(db, product_id: int = None) -> dict:
    """获取待处理项统计"""
    try:
        query = """
            SELECT
                action_type,
                need_ai_judgment,
                COUNT(*) as count
            FROM analysis_results
        """
        params = ()

        if product_id:
            query += " WHERE product_id = ?"
            params = (product_id,)

        query += " GROUP BY action_type, need_ai_judgment"

        cursor = db.execute(query, params)
        rows = cursor.fetchall()

        stats = {
            "negative_count": 0,
            "manual_count": 0,
            "ai_pending_count": 0,
        }

        for row in rows:
            if row["action_type"] == "negative":
                stats["negative_count"] += row["count"]
            elif row["action_type"] == "manual":
                stats["manual_count"] += row["count"]
            if row["need_ai_judgment"]:
                stats["ai_pending_count"] += row["count"]

        return stats
    except Exception as e:
        logger.error(f"获取待处理统计失败: {e}")
        return {
            "negative_count": 0,
            "manual_count": 0,
            "ai_pending_count": 0,
        }


def get_rule_stats(db, product_id: int = None) -> dict:
    """获取规则触发统计"""
    try:
        query = """
            SELECT triggered_rule, COUNT(*) as count
            FROM analysis_results
        """
        params = ()

        if product_id:
            query += " WHERE product_id = ?"
            params = (product_id,)

        query += " GROUP BY triggered_rule ORDER BY count DESC LIMIT 10"

        cursor = db.execute(query, params)
        rows = cursor.fetchall()

        return {row["triggered_rule"]: row["count"] for row in rows}
    except Exception as e:
        logger.error(f"获取规则统计失败: {e}")
        return {}
