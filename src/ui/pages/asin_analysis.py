"""
ASIN分析页面
支持多ASIN对比分析、冲突检测、跨ASIN智能分析
"""

from html import escape

import pandas as pd
import streamlit as st

from src.analysis.asin_analyzer import ASINAnalyzer
from src.config.logger import get_logger

logger = get_logger(__name__)

ASIN_ANALYSIS_CSS = """
<style>
.asin-hero {
    padding: 1.2rem 1.35rem;
    border-radius: 22px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(248,250,252,0.92) 100%);
    box-shadow: 0 16px 38px rgba(15, 23, 42, 0.05);
    margin-bottom: 1rem;
}
.asin-hero__eyebrow {
    display: inline-flex;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
    background: rgba(37, 99, 235, 0.08);
    color: #2563EB;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.asin-hero h1 {
    margin: 0.8rem 0 0.3rem 0 !important;
}
.asin-hero p {
    margin: 0;
    color: #64748B;
    font-size: 0.96rem;
    line-height: 1.6;
}
.asin-hero__chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: 1rem;
}
.asin-hero__chip {
    padding: 0.56rem 0.82rem;
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    background: rgba(255,255,255,0.9);
    color: #334155;
    font-size: 0.84rem;
    font-weight: 600;
}
.asin-summary-shell {
    padding: 1rem 1.05rem;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.15);
    background: rgba(255,255,255,0.9);
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
    margin-bottom: 1rem;
}
.asin-summary-shell strong {
    display: block;
    color: #0F172A;
    margin-bottom: 0.25rem;
}
.asin-summary-shell span {
    color: #64748B;
    font-size: 0.92rem;
    line-height: 1.5;
}
.asin-summary-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
    margin: 1rem 0 1.1rem 0;
}
.asin-summary-card {
    padding: 1.1rem 1.15rem;
    border-radius: 20px;
    border: 1px solid rgba(226, 232, 240, 0.9);
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.95) 100%);
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
}
.asin-summary-card h3 {
    margin: 0 0 0.8rem 0;
    font-size: 1.1rem;
    color: #0F172A;
}
.asin-summary-card__metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
}
.asin-summary-card__metric {
    padding: 0.72rem 0.8rem;
    border-radius: 14px;
    background: rgba(248,250,252,0.92);
    border: 1px solid rgba(226,232,240,0.8);
}
.asin-summary-card__metric span {
    display: block;
    color: #64748B;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 0.3rem;
}
.asin-summary-card__metric strong {
    color: #1E3A8A;
    font-size: 1.25rem;
    line-height: 1.1;
}
.asin-section-note {
    color: #64748B;
    font-size: 0.9rem;
    line-height: 1.5;
    margin: 0.15rem 0 0.75rem 0;
}
@media (max-width: 1180px) {
    .asin-summary-grid {
        grid-template-columns: 1fr;
    }
}
@media (max-width: 960px) {
    .asin-summary-card__metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
</style>
"""


def _build_asin_hero_meta(asin_ids: list[str]) -> dict[str, list[str] | str]:
    """构建 ASIN 分析页顶部工作台文案。"""
    asin_preview = " / ".join(asin_ids[:2]) if asin_ids else "暂无 ASIN"
    return {
        "title": "ASIN分析",
        "description": "把变体对比、分歧检测和跨 ASIN 洞察放在同一块工作面板里，先看谁更强，再决定下一步动作。",
        "chips": [
            f"已识别 {len(asin_ids)} 个 ASIN",
            f"当前重点：{asin_preview}",
            "Top/Bottom 与跨ASIN智能属于洞察页",
        ],
    }


def _build_asin_summary_cards(summary_df: pd.DataFrame) -> list[dict]:
    """统一生成 ASIN 总览卡片的数据结构，便于页面渲染和测试。"""
    cards: list[dict] = []
    for _, row in summary_df.iterrows():
        cards.append(
            {
                "asin_id": row["asin_id"],
                "metrics": [
                    {"label": "展示量", "value": f"{row['impressions']:,.0f}"},
                    {"label": "点击量", "value": f"{row['clicks']:,.0f}"},
                    {"label": "花费", "value": f"${row['spend']:,.2f}"},
                    {"label": "订单", "value": f"{row['orders']:,.0f}"},
                    {"label": "销售额", "value": f"${row['sales']:,.2f}"},
                    {"label": "CTR", "value": f"{row['ctr'] * 100:.2f}%"},
                    {"label": "CVR", "value": f"{row['cvr'] * 100:.2f}%"},
                    {"label": "ACOS", "value": f"{row['acos'] * 100:.1f}%"},
                ],
            }
        )
    return cards


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

    st.markdown(ASIN_ANALYSIS_CSS, unsafe_allow_html=True)
    hero_meta = _build_asin_hero_meta(asin_ids)
    hero_chips = "".join(
        f'<span class="asin-hero__chip">{escape(chip)}</span>'
        for chip in hero_meta["chips"]
    )
    st.markdown(
        f"""
        <div class="asin-hero">
            <span class="asin-hero__eyebrow">对比工作台</span>
            <h1>{escape(hero_meta['title'])}</h1>
            <p>{escape(hero_meta['description'])}</p>
            <div class="asin-hero__chips">{hero_chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    st.markdown(
        '<p class="asin-section-note">先看各 ASIN 的核心表现，再看汇总表和对比洞察，避免在长页面里来回切换视角。</p>',
        unsafe_allow_html=True,
    )

    # 获取汇总数据
    summary_df = analyzer.get_asin_summary(product_id)

    if summary_df.empty:
        st.warning("无汇总数据")
        return

    cards_html = "".join(
        (
            f'<div class="asin-summary-card"><h3>{escape(card["asin_id"])}</h3>'
            + '<div class="asin-summary-card__metrics">'
            + "".join(
                (
                    f'<div class="asin-summary-card__metric"><span>{escape(metric["label"])}</span>'
                    f'<strong>{escape(metric["value"])}</strong></div>'
                )
                for metric in card["metrics"]
            )
            + "</div></div>"
        )
        for card in _build_asin_summary_cards(summary_df)
    )
    st.markdown(
        f'<div class="asin-summary-grid">{cards_html}</div>',
        unsafe_allow_html=True,
    )

    # 汇总表格
    st.subheader("汇总表格")
    st.markdown(
        '<p class="asin-section-note">用于核对原始表现指标；如果想做执行动作判断，请优先看下方的分布、冲突和跨 ASIN 洞察。</p>',
        unsafe_allow_html=True,
    )

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
        st.markdown(
            '<p class="asin-section-note">这里给的是“谁更强、强在哪”的横向比较，帮助你快速判断预算倾斜和扩量方向。</p>',
            unsafe_allow_html=True,
        )

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
    st.markdown(
        '<p class="asin-section-note">先选 ASIN 范围，再看动作分布；“全部”现在是合计视图，不再是某一个 ASIN 伪装的总计。</p>',
        unsafe_allow_html=True,
    )

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
    st.markdown(
        '<p class="asin-section-note">这里专门展示同一词在不同广告组或 ASIN 下的冲突决策，适合人工拍板，而不是直接执行。</p>',
        unsafe_allow_html=True,
    )

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
    st.markdown(
        '<p class="asin-section-note">这是洞察视角，不是最终动作页；适合快速找高效词和高花费零转化词。</p>',
        unsafe_allow_html=True,
    )

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
    st.markdown(
        '<p class="asin-section-note">这里是跨 ASIN 的策略洞察：看差异、看互补、看统一否词，不直接替代最终执行清单。</p>',
        unsafe_allow_html=True,
    )

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
