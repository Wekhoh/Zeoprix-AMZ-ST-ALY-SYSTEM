"""
搜索词分析 - 按活动分析模式
从 analysis.py 拆分
"""

import pandas as pd
import streamlit as st

from src.config.logger import get_logger
from src.ui.pages.analysis import AUTO_ACTION_DISPLAY, save_campaign_review_changes

logger = get_logger(__name__)


def _matches_campaign_action_filter(action_type: str, filters: list[str]) -> bool:
    if not filters:
        return True
    if "negative" in str(action_type):
        return "negative" in filters
    if "manual" in str(action_type):
        return "manual" in filters
    if action_type == "observe":
        return "observe" in filters
    return "evaluate" in filters


def render_campaign_analysis(db, product_id: int):
    """渲染按活动分析模式页面"""
    from src.rules.engine import analyze_search_terms_by_campaign
    from src.analysis.truth_replay import get_truth_first_campaign_rows

    truth_rows = get_truth_first_campaign_rows(db, product_id)
    if truth_rows is not None:
        _render_truth_first_campaign_analysis(truth_rows)
        return

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
                key="campaign_action_filter",
            )

        with col2:
            auto_action_filter = st.multiselect(
                "自动处理",
                options=["keep", "negate", "observe"],
                default=[],
                format_func=lambda x: AUTO_ACTION_DISPLAY.get(x, x),
                key="campaign_auto_action_filter",
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
                key="campaign_term_type_filter",
            )

        with col4:
            search_term = st.text_input(
                "搜索关键词",
                placeholder="输入搜索...",
                key="campaign_search_term",
            )

    # 获取按活动分析结果
    with st.spinner("正在加载按活动分析数据..."):
        try:
            results = analyze_search_terms_by_campaign(db, product_id)
        except Exception as e:
            logger.error(f"按活动分析失败: {e}")
            st.error(f"分析失败: {e}")
            return

    if not results:
        st.info("暂无按活动分析结果。请先上传数据。")
        return

    # 转换为字典列表以便筛选
    results_data = [
        {
            "term": r.term,
            "term_type": r.term_type,
            "campaign_id": r.campaign_id,
            "campaign_name": r.campaign_name,
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
            if _matches_campaign_action_filter(r.get("action_type"), action_filter)
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
            or search_lower in str(r.get("campaign_name", "")).lower()
        ]

    # 显示结果统计
    st.subheader(f"按活动分析结果 ({len(filtered_results)} 条)")

    # 获取已有的审核记录（提前获取用于统计）
    existing_reviews = db.get_manual_reviews(product_id)

    # 计算当前筛选结果中的审核状态
    reviewed_in_results = len(
        [
            r
            for r in filtered_results
            if existing_reviews.get((r["term"], r["campaign_id"]), {}).get(
                "reviewed", 0
            )
            == 1
        ]
    )

    # 统计卡片
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        unique_terms = len(set(r["term"] for r in filtered_results))
        st.metric("唯一搜索词", unique_terms)

    with col2:
        unique_campaigns = len(set(r["campaign_id"] for r in filtered_results))
        st.metric("涉及活动", unique_campaigns)

    with col3:
        keep_count = len(
            [r for r in filtered_results if r.get("auto_action") == "keep"]
        )
        st.metric("自动保留", keep_count)

    with col4:
        negate_count = len(
            [r for r in filtered_results if r.get("auto_action") == "negate"]
        )
        st.metric("自动否定", negate_count)

    with col5:
        observe_count = len(
            [r for r in filtered_results if r.get("auto_action") == "observe"]
        )
        st.metric("继续观察", observe_count)

    with col6:
        st.metric("已审核", f"{reviewed_in_results}/{len(filtered_results)}")

    st.divider()

    if not filtered_results:
        st.warning("筛选后无数据")
        return

    # 结果表格
    df = pd.DataFrame(filtered_results)

    # 格式化显示（纯文字，无emoji）
    display_df = df[
        [
            "term",
            "campaign_name",
            "campaign_id",
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
        "广告活动",
        "活动ID",
        "类型",
        "触发规则",
        "主动作",
        "自动处理",
        "点击",
        "订单",
        "CVR",
    ]

    # 格式化auto_action为中文（纯文字）
    display_df["自动处理"] = display_df["自动处理"].apply(
        lambda x: AUTO_ACTION_DISPLAY.get(x, "-")
    )

    # 格式化CVR
    display_df["CVR"] = display_df["CVR"].apply(
        lambda x: f"{x:.1%}" if pd.notna(x) and x > 0 else "-"
    )

    # 添加已审核列（按活动模式：使用 term + campaign_id 作为键）
    display_df["已审核"] = display_df.apply(
        lambda row: existing_reviews.get((row["搜索词"], row["活动ID"]), {}).get(
            "reviewed", 0
        )
        == 1,
        axis=1,
    )

    # 使用 data_editor 支持勾选
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "搜索词",
            "广告活动",
            "活动ID",
            "类型",
            "触发规则",
            "主动作",
            "自动处理",
            "点击",
            "订单",
            "CVR",
        ],
        column_config={
            "已审核": st.column_config.CheckboxColumn(
                "已审核",
                help="勾选表示已人工确认此建议",
                width="small",
            ),
            "搜索词": st.column_config.TextColumn("搜索词", width="medium"),
            "广告活动": st.column_config.TextColumn("广告活动", width="large"),
            "活动ID": None,  # 隐藏活动ID列
            "类型": st.column_config.TextColumn("类型", width="small"),
            "触发规则": st.column_config.TextColumn("触发规则", width="medium"),
            "主动作": st.column_config.TextColumn("主动作", width="medium"),
            "自动处理": st.column_config.TextColumn("自动处理", width="small"),
            "点击": st.column_config.NumberColumn("点击", width="small"),
            "订单": st.column_config.NumberColumn("订单", width="small"),
            "CVR": st.column_config.TextColumn("CVR", width="small"),
        },
        column_order=[
            "已审核",
            "搜索词",
            "广告活动",
            "类型",
            "触发规则",
            "主动作",
            "自动处理",
            "点击",
            "订单",
            "CVR",
        ],
        key="campaign_review_editor",
    )

    # 保存审核状态变更（按活动模式）
    save_campaign_review_changes(
        db, product_id, display_df, edited_df, filtered_results
    )

    st.divider()

    # 按关键词分组视图
    st.subheader("按关键词分组查看")

    # 找出在多个活动中出现的词
    term_counts = df.groupby("term").size()
    multi_campaign_terms = term_counts[term_counts > 1].index.tolist()

    # 也包含有auto_action的单活动词
    single_with_action = (
        df[
            (~df["term"].isin(multi_campaign_terms))
            & (df["auto_action"].notna())
            & (df["auto_action"] != "")
        ]["term"]
        .unique()
        .tolist()
    )

    highlight_terms = list(set(multi_campaign_terms + single_with_action))

    if highlight_terms:
        selected_term = st.selectbox(
            "选择查看详情",
            options=sorted(highlight_terms),
            index=None,
            placeholder="选择一个搜索词查看各活动表现...",
            key="campaign_selected_term",
        )

        if selected_term:
            term_data = df[df["term"] == selected_term]

            st.write(f"**{selected_term}** 在 {len(term_data)} 个活动中的表现：")

            for _, row in term_data.iterrows():
                auto_display = AUTO_ACTION_DISPLAY.get(row["auto_action"], "-")
                cvr_display = f"{row['cvr']:.1%}" if row["cvr"] > 0 else "-"

                st.write(
                    f"- **{row['campaign_name']}**: "
                    f"{row['triggered_rule']} -> {row['suggested_action']} | "
                    f"自动处理: {auto_display} | "
                    f"点击: {row['clicks']}, 订单: {row['orders']}, CVR: {cvr_display}"
                )
    else:
        st.info("暂无多活动词或有复合动作的词")

    st.divider()

    # 批量审核操作
    st.subheader("批量操作")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("全部标记为已审核", key="campaign_mark_all_reviewed"):
            count = 0
            for r in filtered_results:
                try:
                    db.upsert_manual_review(
                        product_id=product_id,
                        term=r["term"],
                        term_type=r.get("term_type", "keyword"),
                        campaign_id=r["campaign_id"],
                        system_action=r.get("suggested_action"),
                        final_action=r.get("suggested_action"),
                        reviewed=True,
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"标记审核失败: {e}")
            if count > 0:
                st.success(f"已将 {count} 条记录标记为已审核")
                st.rerun()

    with col2:
        if st.button("清除所有审核标记", key="campaign_clear_all_reviewed"):
            count = 0
            for r in filtered_results:
                try:
                    db.upsert_manual_review(
                        product_id=product_id,
                        term=r["term"],
                        term_type=r.get("term_type", "keyword"),
                        campaign_id=r["campaign_id"],
                        system_action=r.get("suggested_action"),
                        final_action=r.get("suggested_action"),
                        reviewed=False,
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"清除审核失败: {e}")
            if count > 0:
                st.success(f"已清除 {count} 条记录的审核标记")
                st.rerun()

    with col3:
        pass  # 预留

    # 导出功能
    st.subheader("导出（仅导出已审核项）")

    col4, col5 = st.columns(2)

    with col4:
        if st.button("导出按活动分析结果", key="export_campaign_results"):
            export_campaign_reviewed_results(filtered_results, existing_reviews)

    with col5:
        if st.button("导出否定清单（按活动）", key="export_campaign_negatives"):
            export_campaign_reviewed_negatives(filtered_results, existing_reviews)


def _render_truth_first_campaign_analysis(rows: list[dict]) -> None:
    """渲染广告组级 truth-first 视图。"""
    with st.expander("筛选条件", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            action_filter = st.multiselect(
                "动作类型",
                options=["negative", "manual", "observe"],
                default=[],
                format_func=lambda x: {
                    "negative": "建议否定",
                    "manual": "建议手动投放",
                    "observe": "继续观察",
                }.get(x, x),
                key="campaign_truth_action_filter",
            )

        with col2:
            auto_action_filter = st.multiselect(
                "自动处理",
                options=["keep", "negate", "observe"],
                default=[],
                format_func=lambda x: AUTO_ACTION_DISPLAY.get(x, x),
                key="campaign_truth_auto_action_filter",
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
                key="campaign_truth_term_type_filter",
            )

        with col4:
            search_term = st.text_input(
                "搜索关键词",
                placeholder="输入搜索...",
                key="campaign_truth_search_term",
            )

    filtered_rows = rows

    if action_filter:
        filtered_rows = [
            row
            for row in filtered_rows
            if _matches_campaign_action_filter(row.get("action_type"), action_filter)
        ]

    if auto_action_filter:
        filtered_rows = [
            row for row in filtered_rows if row.get("auto_action") in auto_action_filter
        ]

    if term_type_filter:
        filtered_rows = [
            row for row in filtered_rows if row.get("term_type") in term_type_filter
        ]

    if search_term:
        search_lower = search_term.lower()
        filtered_rows = [
            row
            for row in filtered_rows
            if search_lower in str(row.get("term", "")).lower()
            or search_lower in str(row.get("campaign_name", "")).lower()
        ]

    st.info("已检测到广告组 workbook truth，当前展示已切换为真相优先活动视图。")
    st.subheader(f"按活动真相视图 ({len(filtered_rows)} 条)")

    if not filtered_rows:
        st.warning("筛选后无数据")
        return

    unique_terms = len({row["term"] for row in filtered_rows})
    unique_campaigns = len({row["campaign_id"] for row in filtered_rows})
    keep_count = len([row for row in filtered_rows if row.get("auto_action") == "keep"])
    negate_count = len(
        [row for row in filtered_rows if row.get("auto_action") == "negate"]
    )
    observe_count = len(
        [row for row in filtered_rows if row.get("auto_action") == "observe"]
    )

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("唯一搜索词", unique_terms)
    with col2:
        st.metric("涉及活动", unique_campaigns)
    with col3:
        st.metric("自动保留", keep_count)
    with col4:
        st.metric("自动否定", negate_count)
    with col5:
        st.metric("继续观察", observe_count)
    with col6:
        st.metric("已审核", f"{len(filtered_rows)}/{len(filtered_rows)}")

    st.divider()

    display_df = pd.DataFrame(filtered_rows)[
        [
            "term",
            "campaign_name",
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
        "广告活动",
        "类型",
        "触发规则",
        "主动作",
        "自动处理",
        "点击",
        "订单",
        "CVR",
    ]
    display_df["自动处理"] = display_df["自动处理"].apply(
        lambda value: AUTO_ACTION_DISPLAY.get(value, "-")
    )
    display_df["CVR"] = display_df["CVR"].apply(
        lambda value: f"{value:.1%}" if pd.notna(value) and value > 0 else "-"
    )
    display_df["已审核"] = True

    st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "已审核",
            "搜索词",
            "广告活动",
            "类型",
            "触发规则",
            "主动作",
            "自动处理",
            "点击",
            "订单",
            "CVR",
        ],
        column_config={
            "已审核": st.column_config.CheckboxColumn("已审核", width="small"),
            "搜索词": st.column_config.TextColumn("搜索词", width="medium"),
            "广告活动": st.column_config.TextColumn("广告活动", width="large"),
            "类型": st.column_config.TextColumn("类型", width="small"),
            "触发规则": st.column_config.TextColumn("触发规则", width="medium"),
            "主动作": st.column_config.TextColumn("主动作", width="medium"),
            "自动处理": st.column_config.TextColumn("自动处理", width="small"),
            "点击": st.column_config.NumberColumn("点击", width="small"),
            "订单": st.column_config.NumberColumn("订单", width="small"),
            "CVR": st.column_config.TextColumn("CVR", width="small"),
        },
        column_order=[
            "已审核",
            "搜索词",
            "广告活动",
            "类型",
            "触发规则",
            "主动作",
            "自动处理",
            "点击",
            "订单",
            "CVR",
        ],
        key="campaign_truth_editor",
    )


def export_campaign_results(results: list[dict]):
    """导出按活动分析结果"""
    import datetime

    if not results:
        st.warning("没有可导出的数据")
        return

    export_df = pd.DataFrame(
        [
            {
                "搜索词": r["term"],
                "广告活动": r["campaign_name"],
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
    filename = (
        f"campaign_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    st.download_button(
        label="下载CSV",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )
    st.success(f"准备导出 {len(results)} 条记录")


def export_campaign_negatives(results: list[dict]):
    """导出否定清单（按活动分组）"""
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

    # 按活动分组
    export_df = pd.DataFrame(
        [
            {
                "广告活动": r["campaign_name"],
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

    # 按活动名称排序
    export_df = export_df.sort_values(["广告活动", "搜索词"])

    csv_data = export_df.to_csv(index=False, encoding="utf-8-sig")
    filename = (
        f"campaign_negatives_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    st.download_button(
        label="下载否词清单CSV",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )
    st.success(f"准备导出 {len(negatives)} 条否词记录")


def export_campaign_reviewed_results(results: list[dict], existing_reviews: dict):
    """导出按活动分析结果（仅已审核项）"""
    import datetime

    # 筛选已审核的项目
    reviewed_results = [
        r
        for r in results
        if existing_reviews.get((r.get("term"), r.get("campaign_id")), {}).get(
            "reviewed", 0
        )
        == 1
    ]

    if not reviewed_results:
        st.warning("没有已审核的项目可导出。请先在表格中勾选需要导出的项目。")
        return

    export_df = pd.DataFrame(
        [
            {
                "搜索词": r["term"],
                "广告活动": r["campaign_name"],
                "类型": r["term_type"],
                "触发规则": r["triggered_rule"],
                "主动作": r["suggested_action"],
                "自动处理": AUTO_ACTION_DISPLAY.get(r.get("auto_action"), "-"),
                "点击": r["clicks"],
                "订单": r["orders"],
                "CVR": f"{r['cvr']:.1%}" if r["cvr"] > 0 else "-",
                "花费": f"${r['spend']:.2f}",
            }
            for r in reviewed_results
        ]
    )

    csv_data = export_df.to_csv(index=False, encoding="utf-8-sig")
    filename = (
        f"campaign_reviewed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    st.download_button(
        label=f"下载CSV ({len(export_df)}条)",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )
    st.success(f"准备导出 {len(reviewed_results)} 条已审核记录")


def export_campaign_reviewed_negatives(results: list[dict], existing_reviews: dict):
    """导出否定清单（仅已审核项，按活动分组）"""
    import datetime

    # 筛选已审核的项目
    reviewed_results = [
        r
        for r in results
        if existing_reviews.get((r.get("term"), r.get("campaign_id")), {}).get(
            "reviewed", 0
        )
        == 1
    ]

    # 从已审核中筛选需要否定的词
    negatives = [
        r
        for r in reviewed_results
        if r.get("auto_action") == "negate"
        or "否定" in str(r.get("suggested_action", ""))
    ]

    if not negatives:
        st.warning("没有已审核的否词项目可导出。请先在表格中勾选需要否定的项目。")
        return

    # 按活动分组
    export_df = pd.DataFrame(
        [
            {
                "广告活动": r["campaign_name"],
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

    # 按活动名称排序
    export_df = export_df.sort_values(["广告活动", "搜索词"])

    csv_data = export_df.to_csv(index=False, encoding="utf-8-sig")
    filename = f"campaign_negatives_reviewed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    st.download_button(
        label=f"下载否词清单CSV ({len(export_df)}条)",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )
    st.success(f"准备导出 {len(negatives)} 条已审核否词记录")
