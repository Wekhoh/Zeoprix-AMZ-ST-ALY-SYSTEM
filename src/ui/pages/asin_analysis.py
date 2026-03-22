"""
ASIN分析页面
支持多ASIN对比分析、冲突检测、跨ASIN智能分析
"""

import pandas as pd
import streamlit as st

from src.analysis.asin_analyzer import ASINAnalyzer
from src.config.logger import get_logger

logger = get_logger(__name__)


def build_unified_negation_export_payload(unified_neg: list):
    """构建统一否词建议的直接下载载荷。"""
    import datetime

    if not unified_neg:
        return None

    export_df = pd.DataFrame(
        [
            {
                "搜索词": item["term"],
                "总花费($)": f"{item['total_spend']:.2f}",
                "涉及ASIN数": item["asin_count"],
                "涉及ASIN": ", ".join(item.get("asins", [])),
            }
            for item in unified_neg
        ]
    )

    csv_data = export_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    filename = (
        f"unified_negation_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    return {"data": csv_data, "file_name": filename, "mime": "text/csv"}


def _render_metric_card(label: str, value: str):
    """渲染单个指标卡片，标签更醒目"""
    st.markdown(
        f"""
        <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid #1f77b4;">
            <div style="color: #333; font-size: 14px; font-weight: 600; margin-bottom: 4px;">{label}</div>
            <div style="color: #1f77b4; font-size: 24px; font-weight: bold;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_asin_analysis():
    """渲染ASIN分析页面"""
    st.title("ASIN分析")

    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    if not product_id:
        st.warning("请先选择产品")
        return

    # 初始化分析器
    analyzer = ASINAnalyzer(db)

    # 获取ASIN列表
    asin_ids = analyzer.get_all_asin_ids(product_id)

    if not asin_ids:
        st.info("暂无数据。请先上传广告数据。")
        return

    st.caption(f"已识别 {len(asin_ids)} 个ASIN: {', '.join(asin_ids)}")

    st.divider()

    # 层次一+二: 汇总和对比
    render_summary_section(analyzer, product_id, asin_ids)

    st.divider()

    # 层次三+四: 详细分析标签页
    tab_names = ["关键词分布", "冲突检测", "Top/Bottom", "跨ASIN智能"]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        render_keyword_distribution(analyzer, product_id, asin_ids)

    with tabs[1]:
        render_conflict_detection(analyzer, product_id, asin_ids)

    with tabs[2]:
        render_top_bottom(analyzer, product_id, asin_ids)

    with tabs[3]:
        render_cross_asin_analysis(analyzer, product_id)


def render_summary_section(analyzer: ASINAnalyzer, product_id: int, asin_ids: list):
    """渲染汇总和对比部分（层次一+二）"""
    st.subheader("ASIN总览")

    # 获取汇总数据
    summary_df = analyzer.get_asin_summary(product_id)

    if summary_df.empty:
        st.warning("无汇总数据")
        return

    # 创建汇总卡片
    cols = st.columns(len(asin_ids))

    for idx, asin_id in enumerate(asin_ids):
        asin_data = summary_df[summary_df["asin_id"] == asin_id]
        if asin_data.empty:
            continue

        row = asin_data.iloc[0]

        with cols[idx]:
            st.markdown(f"### {asin_id}")
            # 使用自定义样式让指标标签更醒目
            _render_metric_card("展示量", f"{row['impressions']:,.0f}")
            _render_metric_card("点击量", f"{row['clicks']:,.0f}")
            _render_metric_card("花费", f"${row['spend']:,.2f}")
            _render_metric_card("订单", f"{row['orders']:,.0f}")
            _render_metric_card("销售额", f"${row['sales']:,.2f}")
            _render_metric_card("CTR", f"{row['ctr'] * 100:.2f}%")
            _render_metric_card("CVR", f"{row['cvr'] * 100:.2f}%")
            _render_metric_card("ACOS", f"{row['acos'] * 100:.1f}%")

    # 汇总表格
    st.subheader("汇总表格")

    display_df = summary_df[
        [
            "asin_id",
            "impressions",
            "clicks",
            "spend",
            "orders",
            "sales",
            "ctr",
            "cvr",
            "acos",
            "cpc",
            "roas",
        ]
    ].copy()

    display_df.columns = [
        "ASIN",
        "展示量",
        "点击量",
        "花费($)",
        "订单",
        "销售额($)",
        "CTR",
        "CVR",
        "ACOS",
        "CPC($)",
        "ROAS",
    ]

    # 格式化
    display_df["CTR"] = display_df["CTR"].apply(lambda x: f"{x * 100:.2f}%")
    display_df["CVR"] = display_df["CVR"].apply(lambda x: f"{x * 100:.2f}%")
    display_df["ACOS"] = display_df["ACOS"].apply(lambda x: f"{x * 100:.1f}%")
    display_df["CPC($)"] = display_df["CPC($)"].apply(lambda x: f"{x:.2f}")
    display_df["ROAS"] = display_df["ROAS"].apply(lambda x: f"{x:.2f}")
    display_df["花费($)"] = display_df["花费($)"].apply(lambda x: f"{x:,.2f}")
    display_df["销售额($)"] = display_df["销售额($)"].apply(lambda x: f"{x:,.2f}")

    st.dataframe(display_df, width="stretch", hide_index=True)

    # 对比洞察
    if len(asin_ids) >= 2:
        st.subheader("对比洞察")

        insights = analyzer.get_comparison_insights(product_id)

        if insights.get("metrics_comparison"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**指标胜出对比**")
                for comp in insights["metrics_comparison"]:
                    metric = comp["metric"]
                    winner = comp["winner"]
                    values_str = ", ".join(
                        [f"{k}: {v}" for k, v in comp["values"].items()]
                    )
                    st.write(f"- {metric}: **{winner}** 胜出 ({values_str})")

            with col2:
                st.markdown("**效率排名 (按ROAS)**")
                for rank in insights["efficiency_ranking"]:
                    st.write(f"- {rank['asin_id']}: ROAS {rank['roas']:.2f}")

        if insights.get("budget_suggestion"):
            st.info(insights["budget_suggestion"])


def render_keyword_distribution(
    analyzer: ASINAnalyzer, product_id: int, asin_ids: list
):
    """渲染关键词分布（层次三）"""
    st.subheader("关键词操作分布")

    # ASIN选择器
    selected_asin = st.selectbox(
        "选择ASIN", options=["全部"] + asin_ids, key="kw_dist_asin_select"
    )

    if selected_asin == "全部":
        distribution = analyzer.get_keyword_distribution_summary(product_id)
    else:
        distribution = analyzer.get_keyword_distribution(product_id, selected_asin)

    if not distribution:
        st.info("暂无分布数据")
        return

    # 显示各ASIN的分布
    for asin_id, action_counts in distribution.items():
        st.markdown(f"### {asin_id}")

        total = sum(action_counts.values())

        # 使用4列布局，避免列太窄导致截断
        if total > 0:
            # 按数量排序
            sorted_actions = sorted(
                action_counts.items(), key=lambda x: x[1], reverse=True
            )

            # 最多显示4个指标卡片（前4个）
            display_count = min(4, len(sorted_actions))
            cols = st.columns(display_count)
            for idx in range(display_count):
                action, count = sorted_actions[idx]
                with cols[idx]:
                    pct = count / total * 100
                    st.metric(action, count, f"{pct:.1f}%")

        # 完整表格
        st.caption("完整分布明细:")
        dist_df = pd.DataFrame(
            [
                {
                    "操作类型": action,
                    "数量": count,
                    "占比": f"{count / total * 100:.1f}%" if total > 0 else "0%",
                }
                for action, count in sorted(
                    action_counts.items(), key=lambda x: x[1], reverse=True
                )
            ]
        )
        st.dataframe(dist_df, width="stretch", hide_index=True)

        st.divider()


def render_conflict_detection(analyzer: ASINAnalyzer, product_id: int, asin_ids: list):
    """渲染冲突检测（层次三）"""
    st.subheader("决策冲突检测")

    # ASIN选择器
    selected_asin = st.selectbox(
        "选择ASIN", options=["全部"] + asin_ids, key="conflict_asin_select"
    )

    asin_filter = None if selected_asin == "全部" else selected_asin

    conflicts_df = analyzer.detect_conflicts(product_id, asin_filter)

    if conflicts_df.empty:
        st.success("未检测到决策冲突")
        return

    st.warning(f"检测到 {len(conflicts_df)} 个冲突关键词")

    # 按严重程度分组显示
    severity_order = ["严重", "中等", "轻微"]

    for severity in severity_order:
        severity_conflicts = conflicts_df[conflicts_df["severity"] == severity]
        if severity_conflicts.empty:
            continue

        severity_label = {
            "严重": "[严重] 完全相反的决策（否定 vs 保留）",
            "中等": "[中等] 否定 vs 观察",
            "轻微": "[轻微] 细节差异",
        }

        with st.expander(
            f"{severity_label.get(severity, severity)} ({len(severity_conflicts)}个)",
            expanded=(severity == "严重"),
        ):
            for _, row in severity_conflicts.iterrows():
                st.markdown(f"**{row['term']}** (ASIN: {row['asin_id']})")

                # 显示各广告组的详细决策
                decisions = row["campaign_decisions"]
                if isinstance(decisions, dict):
                    # 创建表格展示详细信息
                    decision_data = []
                    for campaign, detail in decisions.items():
                        if isinstance(detail, dict):
                            decision_data.append(
                                {
                                    "广告组": campaign,
                                    "决策": detail.get("action", "未知"),
                                    "依据": detail.get("reason", ""),
                                    "点击": detail.get("clicks", 0),
                                    "订单": detail.get("orders", 0),
                                    "花费($)": f"{detail.get('spend', 0):.2f}",
                                    "CVR": f"{detail.get('cvr', 0) * 100:.1f}%",
                                }
                            )
                        else:
                            # 兼容旧格式
                            decision_data.append(
                                {
                                    "广告组": campaign,
                                    "决策": detail,
                                    "依据": "",
                                    "点击": "-",
                                    "订单": "-",
                                    "花费($)": "-",
                                    "CVR": "-",
                                }
                            )

                    if decision_data:
                        decision_df = pd.DataFrame(decision_data)
                        st.dataframe(
                            decision_df, width="stretch", hide_index=True
                        )
                st.divider()


def render_top_bottom(analyzer: ASINAnalyzer, product_id: int, asin_ids: list):
    """渲染Top/Bottom表现词（层次三）"""
    st.subheader("Top/Bottom表现词")

    # ASIN选择器
    selected_asin = st.selectbox(
        "选择ASIN", options=["全部"] + asin_ids, key="topbottom_asin_select"
    )

    # 数量选择
    n = st.slider("显示数量", min_value=3, max_value=10, value=5, key="topbottom_n")

    asin_filter = None if selected_asin == "全部" else selected_asin

    top_bottom = analyzer.get_top_bottom_keywords(product_id, asin_filter, n)

    if not top_bottom:
        st.info("暂无数据")
        return

    for asin_id, data in top_bottom.items():
        st.markdown(f"### {asin_id}")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Top表现词 (高CVR)**")
            if data.get("top"):
                top_df = pd.DataFrame(data["top"])
                top_df.columns = ["搜索词", "CVR", "订单", "花费($)"]
                top_df["CVR"] = top_df["CVR"].apply(lambda x: f"{x * 100:.1f}%")
                top_df["花费($)"] = top_df["花费($)"].apply(lambda x: f"{x:.2f}")
                st.dataframe(top_df, width="stretch", hide_index=True)
            else:
                st.info("暂无高效词")

        with col2:
            st.markdown("**Bottom表现词 (高花费零转化)**")
            if data.get("bottom"):
                bottom_df = pd.DataFrame(data["bottom"])
                bottom_df.columns = ["搜索词", "CVR", "订单", "花费($)"]
                bottom_df["CVR"] = bottom_df["CVR"].apply(lambda x: f"{x * 100:.1f}%")
                bottom_df["花费($)"] = bottom_df["花费($)"].apply(lambda x: f"{x:.2f}")
                st.dataframe(bottom_df, width="stretch", hide_index=True)
            else:
                st.info("暂无低效词")

        st.divider()


def render_cross_asin_analysis(analyzer: ASINAnalyzer, product_id: int):
    """渲染跨ASIN智能分析（层次四）"""
    st.subheader("跨ASIN智能分析")

    cross_analysis = analyzer.cross_asin_analysis(product_id)

    if cross_analysis.get("message"):
        st.info(cross_analysis["message"])
        return

    # 1. 词效差异
    st.markdown("#### 词效差异分析")
    st.caption("同一关键词在不同ASIN间CVR差异超过30%的词")

    perf_diff = cross_analysis.get("performance_diff", [])
    if perf_diff:
        diff_df = pd.DataFrame(perf_diff)
        diff_df = diff_df[
            ["term", "best_asin", "best_cvr", "worst_asin", "worst_cvr", "diff_ratio"]
        ]
        diff_df.columns = [
            "搜索词",
            "最佳ASIN",
            "最佳CVR",
            "最差ASIN",
            "最差CVR",
            "差异比",
        ]
        diff_df["最佳CVR"] = diff_df["最佳CVR"].apply(lambda x: f"{x * 100:.1f}%")
        diff_df["最差CVR"] = diff_df["最差CVR"].apply(lambda x: f"{x * 100:.1f}%")
        diff_df["差异比"] = diff_df["差异比"].apply(lambda x: f"{x * 100:.0f}%")
        st.dataframe(diff_df, width="stretch", hide_index=True)
    else:
        st.info("未发现显著词效差异")

    st.divider()

    # 2. 互补机会
    st.markdown("#### 互补机会")
    st.caption("某ASIN独有的高效词，建议扩展到其他ASIN测试")

    complementary = cross_analysis.get("complementary", {})
    unique_good = complementary.get("unique_good", {})

    if unique_good:
        for asin_id, terms in unique_good.items():
            st.markdown(f"**{asin_id} 独有高效词:**")
            for term_info in terms:
                st.write(
                    f"  - {term_info['term']} (订单: {term_info['orders']}, CVR: {term_info['cvr'] * 100:.1f}%)"
                )
    else:
        st.info("未发现互补机会")

    # 扩展建议
    expansion = complementary.get("expansion_suggestions", [])
    if expansion:
        st.markdown("**扩展建议:**")
        for sug in expansion[:5]:
            st.write(
                f"  - 将 '{sug['term']}' 从 {sug['from_asin']} 扩展到 {sug['to_asin']} 测试"
            )

    st.divider()

    # 3. 统一否词建议
    st.markdown("#### 统一否词建议")
    st.caption("在所有ASIN都表现差（高花费零转化）的词，建议统一否定")

    unified_neg = cross_analysis.get("unified_negation", [])
    if unified_neg:
        neg_df = pd.DataFrame(unified_neg)
        neg_df = neg_df[["term", "total_spend", "asin_count"]]
        neg_df.columns = ["搜索词", "总花费($)", "涉及ASIN数"]
        neg_df["总花费($)"] = neg_df["总花费($)"].apply(lambda x: f"{x:.2f}")
        st.dataframe(neg_df, width="stretch", hide_index=True)

        payload = build_unified_negation_export_payload(unified_neg)
        if payload:
            st.download_button(
                label="导出统一否词清单",
                data=payload["data"],
                file_name=payload["file_name"],
                mime=payload["mime"],
                key="download_unified_neg",
            )
        else:
            st.button("导出统一否词清单", disabled=True, width="stretch")
    else:
        st.success("未发现需要统一否定的词")
