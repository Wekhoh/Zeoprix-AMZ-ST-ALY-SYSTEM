"""
搜索词分析 - 按ASIN分析模式
从 analysis.py 拆分
"""

import pandas as pd
import streamlit as st

from src.config.logger import get_logger
from src.ui.pages.analysis import AUTO_ACTION_DISPLAY

logger = get_logger(__name__)


def render_asin_analysis(db, product_id: int):
    """渲染按ASIN分析模式页面（ASIN级别聚合，如BLK、DBL）"""
    from src.rules.engine import analyze_search_terms_by_asin

    # 筛选面板
    with st.expander("筛选条件", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            action_filter = st.multiselect(
                "动作类型",
                options=["negative", "manual", "observe", "evaluate"],
                default=[],
                format_func=lambda x: {
                    "negative": "建议否定",
                    "manual": "建议手动投放",
                    "observe": "继续观察",
                    "evaluate": "需评估",
                }.get(x, x),
                key="asin_action_filter",
            )

        with col2:
            auto_action_filter = st.multiselect(
                "自动处理",
                options=["keep", "negate", "observe"],
                default=[],
                format_func=lambda x: AUTO_ACTION_DISPLAY.get(x, x),
                key="asin_auto_action_filter",
            )

        with col3:
            term_type_filter = st.multiselect(
                "词类型",
                options=["keyword", "asin"],
                default=[],
                format_func=lambda x: {
                    "keyword": "关键词",
                    "asin": "ASIN",
                }.get(x, x),
                key="asin_term_type_filter",
            )

        with col4:
            search_term = st.text_input(
                "搜索关键词",
                placeholder="输入搜索...",
                key="asin_search_term",
            )

    # 获取按ASIN分析结果
    with st.spinner("正在加载按ASIN分析数据..."):
        try:
            results = analyze_search_terms_by_asin(db, product_id)
        except Exception as e:
            logger.error(f"按ASIN分析失败: {e}")
            st.error(f"分析失败: {e}")
            return

    if not results:
        st.info("暂无按ASIN分析结果。请先上传数据。")
        return

    # 转换为字典列表以便筛选
    results_data = [
        {
            "term": r.term,
            "term_type": r.term_type,
            "asin_identifier": r.asin_identifier,
            "triggered_rule": r.triggered_rule,
            "suggested_action": r.suggested_action,
            "auto_action": r.auto_action,
            "action_type": r.action_type,
            "confidence": r.confidence,
            "clicks": r.clicks,
            "orders": r.orders,
            "spend": r.spend,
            "cvr": r.cvr,
            "acos": r.acos,
        }
        for r in results
    ]

    # 应用筛选
    filtered_results = results_data

    if action_filter:
        filtered_results = [
            r
            for r in filtered_results
            if any(af in str(r.get("action_type", "")) for af in action_filter)
        ]

    if auto_action_filter:
        filtered_results = [
            r for r in filtered_results if r.get("auto_action") in auto_action_filter
        ]

    if term_type_filter:
        filtered_results = [
            r for r in filtered_results if r.get("term_type") in term_type_filter
        ]

    if search_term:
        search_lower = search_term.lower()
        filtered_results = [
            r
            for r in filtered_results
            if search_lower in str(r.get("term", "")).lower()
            or search_lower in str(r.get("asin_identifier", "")).lower()
        ]

    # 获取所有ASIN标识
    asin_identifiers = sorted(set(r["asin_identifier"] for r in results_data))

    # ASIN筛选器（放在筛选面板之后）
    if len(asin_identifiers) > 1:
        asin_filter = st.multiselect(
            "ASIN筛选",
            options=asin_identifiers,
            default=asin_identifiers,
            key="asin_identifier_filter",
        )
        if asin_filter:
            filtered_results = [
                r for r in filtered_results if r.get("asin_identifier") in asin_filter
            ]

    # 显示结果统计
    st.subheader(f"按ASIN分析结果 ({len(filtered_results)} 条)")

    # 统计卡片
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        unique_terms = len(set(r["term"] for r in filtered_results))
        st.metric("唯一搜索词", unique_terms)

    with col2:
        unique_asins = len(set(r["asin_identifier"] for r in filtered_results))
        st.metric("ASIN变体", unique_asins)

    with col3:
        negative_count = len(
            [r for r in filtered_results if "negative" in str(r.get("action_type", ""))]
        )
        st.metric("建议否定", negative_count)

    with col4:
        keep_count = len(
            [r for r in filtered_results if r.get("auto_action") == "keep"]
        )
        st.metric("自动保留", keep_count)

    with col5:
        negate_count = len(
            [r for r in filtered_results if r.get("auto_action") == "negate"]
        )
        st.metric("自动否定", negate_count)

    with col6:
        observe_count = len(
            [r for r in filtered_results if r.get("auto_action") == "observe"]
        )
        st.metric("继续观察", observe_count)

    st.divider()

    if not filtered_results:
        st.warning("筛选后无数据")
        return

    # 结果表格
    df = pd.DataFrame(filtered_results)

    # 格式化显示
    display_df = df[
        [
            "term",
            "asin_identifier",
            "term_type",
            "triggered_rule",
            "suggested_action",
            "auto_action",
            "clicks",
            "orders",
            "cvr",
        ]
    ].copy()

    display_df.columns = [
        "搜索词",
        "ASIN",
        "类型",
        "触发规则",
        "主动作",
        "自动处理",
        "点击",
        "订单",
        "CVR",
    ]

    # 格式化auto_action为中文
    display_df["自动处理"] = display_df["自动处理"].apply(
        lambda x: AUTO_ACTION_DISPLAY.get(x, "-")
    )

    # 格式化CVR
    display_df["CVR"] = display_df["CVR"].apply(
        lambda x: f"{x:.1%}" if pd.notna(x) and x > 0 else "-"
    )

    # 显示表格
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "搜索词": st.column_config.TextColumn("搜索词", width="large"),
            "ASIN": st.column_config.TextColumn("ASIN", width="small"),
            "类型": st.column_config.TextColumn("类型", width="small"),
            "触发规则": st.column_config.TextColumn("触发规则", width="medium"),
            "主动作": st.column_config.TextColumn("主动作", width="medium"),
            "自动处理": st.column_config.TextColumn("自动处理", width="small"),
            "点击": st.column_config.NumberColumn("点击", width="small"),
            "订单": st.column_config.NumberColumn("订单", width="small"),
            "CVR": st.column_config.TextColumn("CVR", width="small"),
        },
    )

    st.divider()

    # 按ASIN对比视图
    st.subheader("按ASIN对比")

    if len(asin_identifiers) >= 2:
        # 找出在多个ASIN中出现的词
        term_asin_counts = df.groupby("term")["asin_identifier"].nunique()
        multi_asin_terms = term_asin_counts[term_asin_counts > 1].index.tolist()

        if multi_asin_terms:
            st.write(f"共 {len(multi_asin_terms)} 个词在多个ASIN中有数据")

            selected_term = st.selectbox(
                "选择查看对比",
                options=sorted(multi_asin_terms),
                index=None,
                placeholder="选择一个搜索词查看各ASIN表现...",
                key="asin_compare_term",
            )

            if selected_term:
                term_data = df[df["term"] == selected_term]

                st.write(f"**{selected_term}** 在各ASIN中的表现：")

                # 创建对比表格
                compare_data = []
                for _, row in term_data.iterrows():
                    auto_display = AUTO_ACTION_DISPLAY.get(row["auto_action"], "-")
                    cvr_display = f"{row['cvr']:.1%}" if row["cvr"] > 0 else "-"
                    compare_data.append(
                        {
                            "ASIN": row["asin_identifier"],
                            "触发规则": row["triggered_rule"],
                            "主动作": row["suggested_action"],
                            "自动处理": auto_display,
                            "点击": row["clicks"],
                            "订单": row["orders"],
                            "CVR": cvr_display,
                            "花费": f"${row['spend']:.2f}",
                        }
                    )

                compare_df = pd.DataFrame(compare_data)
                st.dataframe(compare_df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无跨ASIN的共同词汇")
    else:
        st.info("需要至少2个ASIN才能进行对比分析")

    st.divider()

    # 导出功能
    st.subheader("导出")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("导出按ASIN分析结果", key="export_asin_results"):
            export_asin_results(filtered_results)

    with col2:
        if st.button("导出否定清单（按ASIN）", key="export_asin_negatives"):
            export_asin_negatives(filtered_results)


def export_asin_results(results: list[dict]):
    """导出按ASIN分析结果"""
    import datetime

    if not results:
        st.warning("没有可导出的数据")
        return

    export_df = pd.DataFrame(
        [
            {
                "搜索词": r["term"],
                "ASIN": r["asin_identifier"],
                "类型": r["term_type"],
                "触发规则": r["triggered_rule"],
                "主动作": r["suggested_action"],
                "自动处理": AUTO_ACTION_DISPLAY.get(r.get("auto_action"), "-"),
                "点击": r["clicks"],
                "订单": r["orders"],
                "CVR": f"{r['cvr']:.1%}" if r["cvr"] > 0 else "-",
                "花费": f"${r['spend']:.2f}",
            }
            for r in results
        ]
    )

    csv_data = export_df.to_csv(index=False, encoding="utf-8-sig")
    filename = f"asin_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    st.download_button(
        label="下载CSV",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )
    st.success(f"准备导出 {len(results)} 条记录")


def export_asin_negatives(results: list[dict]):
    """导出否定清单（按ASIN分组）"""
    import datetime

    # 筛选需要否定的词
    negatives = [
        r
        for r in results
        if r.get("auto_action") == "negate"
        or "否定" in str(r.get("suggested_action", ""))
    ]

    if not negatives:
        st.warning("没有可导出的否词数据")
        return

    # 按ASIN分组
    export_df = pd.DataFrame(
        [
            {
                "ASIN": r["asin_identifier"],
                "搜索词": r["term"],
                "类型": r["term_type"],
                "触发规则": r["triggered_rule"],
                "否定来源": "自动否定"
                if r.get("auto_action") == "negate"
                else "规则否定",
                "点击": r["clicks"],
                "订单": r["orders"],
            }
            for r in negatives
        ]
    )

    # 按ASIN排序
    export_df = export_df.sort_values(["ASIN", "搜索词"])

    csv_data = export_df.to_csv(index=False, encoding="utf-8-sig")
    filename = f"asin_negatives_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    st.download_button(
        label="下载否词清单CSV",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )
    st.success(f"准备导出 {len(negatives)} 条否词记录")
