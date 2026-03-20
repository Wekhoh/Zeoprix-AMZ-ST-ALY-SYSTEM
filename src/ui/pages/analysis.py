"""
搜索词分析页面
核心分析界面，支持多维筛选和AI分析
支持汇总模式和按活动分析模式
"""

import pandas as pd
import streamlit as st

from src.config.logger import get_logger
from src.ui.utils import safe_error

logger = get_logger(__name__)


def save_review_changes(
    db,
    product_id: int,
    original_df: pd.DataFrame,
    edited_df: pd.DataFrame,
    results: list[dict],
    campaign_id: int = None,
):
    """
    保存审核状态变更

    Args:
        db: 数据库实例
        product_id: 产品ID
        original_df: 原始DataFrame
        edited_df: 编辑后的DataFrame
        results: 原始分析结果列表
        campaign_id: 活动ID（按活动模式时使用）
    """
    # 比较变更
    changed_count = 0
    for idx in range(len(original_df)):
        original_reviewed = original_df.iloc[idx]["已审核"]
        edited_reviewed = edited_df.iloc[idx]["已审核"]

        if original_reviewed != edited_reviewed:
            term = original_df.iloc[idx]["搜索词"]
            # 找到对应的原始结果
            result = next((r for r in results if r.get("term") == term), None)
            if result:
                try:
                    db.upsert_manual_review(
                        product_id=product_id,
                        term=term,
                        term_type=result.get("term_type", "keyword"),
                        campaign_id=campaign_id,
                        system_action=result.get("suggested_action"),
                        final_action=result.get("suggested_action"),
                        reviewed=edited_reviewed,
                    )
                    changed_count += 1
                except Exception as e:
                    logger.error(f"保存审核状态失败 [{term}]: {e}")

    if changed_count > 0:
        logger.info(f"已保存 {changed_count} 条审核状态变更")


def save_campaign_review_changes(
    db,
    product_id: int,
    original_df: pd.DataFrame,
    edited_df: pd.DataFrame,
    results: list[dict],
):
    """
    保存按活动模式的审核状态变更

    Args:
        db: 数据库实例
        product_id: 产品ID
        original_df: 原始DataFrame
        edited_df: 编辑后的DataFrame
        results: 原始分析结果列表
    """
    # 比较变更
    changed_count = 0
    for idx in range(len(original_df)):
        original_reviewed = original_df.iloc[idx]["已审核"]
        edited_reviewed = edited_df.iloc[idx]["已审核"]

        if original_reviewed != edited_reviewed:
            term = original_df.iloc[idx]["搜索词"]
            campaign_id = original_df.iloc[idx]["活动ID"]
            # 找到对应的原始结果
            result = next(
                (
                    r
                    for r in results
                    if r.get("term") == term and r.get("campaign_id") == campaign_id
                ),
                None,
            )
            if result:
                try:
                    db.upsert_manual_review(
                        product_id=product_id,
                        term=term,
                        term_type=result.get("term_type", "keyword"),
                        campaign_id=campaign_id,
                        system_action=result.get("suggested_action"),
                        final_action=result.get("suggested_action"),
                        reviewed=edited_reviewed,
                    )
                    changed_count += 1
                except Exception as e:
                    logger.error(f"保存审核状态失败 [{term}@{campaign_id}]: {e}")

    if changed_count > 0:
        logger.info(f"已保存 {changed_count} 条按活动审核状态变更")


# auto_action 显示映射（纯文字，无emoji）
AUTO_ACTION_DISPLAY = {
    "keep": "保留",
    "negate": "否定",
    "observe": "观察",
    None: "-",
    "": "-",
}


def render_analysis():
    """渲染搜索词分析页面"""
    st.title("搜索词分析")

    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    if not product_id:
        st.warning("请先选择产品")
        return

    # 分析模式选择（放在页面顶部）
    analysis_mode = st.radio(
        "分析模式",
        options=["汇总模式", "按活动模式", "按ASIN模式"],
        horizontal=True,
        help="汇总模式：跨活动聚合分析；按活动模式：保留活动维度；按ASIN模式：按ASIN标识聚合（如BLK、DBL）",
    )

    st.divider()

    # 根据模式渲染不同视图
    if analysis_mode == "按活动模式":
        render_campaign_analysis(db, product_id)
    elif analysis_mode == "按ASIN模式":
        render_asin_analysis(db, product_id)
    else:
        render_summary_analysis(db, product_id)


def render_summary_analysis(db, product_id: int):
    """渲染汇总模式分析页面（使用实时计算避免数据重复）"""
    from src.rules.engine import analyze_search_terms

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
                key="summary_action_filter",
            )

        with col2:
            term_type_filter = st.multiselect(
                "词类型",
                options=["keyword", "asin"],
                default=[],
                format_func=lambda x: {
                    "keyword": "关键词",
                    "asin": "ASIN",
                }.get(x, x),
                key="summary_term_type_filter",
            )

        with col3:
            ai_filter = st.selectbox(
                "AI确认状态",
                options=["全部", "待AI确认", "已确认"],
                index=0,
                key="summary_ai_filter",
            )

        with col4:
            search_term = st.text_input(
                "搜索关键词",
                placeholder="输入搜索...",
                key="summary_search_term",
            )

    # 使用实时计算获取分析结果（避免数据库重复数据问题）
    with st.spinner("正在加载汇总分析数据..."):
        try:
            raw_results = analyze_search_terms(db, product_id)
        except Exception as e:
            logger.error(f"汇总分析失败: {e}")
            st.error(f"分析失败: {e}")
            return

    if not raw_results:
        st.info("暂无分析结果。请先上传数据。")
        return

    # 转换为字典列表以便筛选
    results = [
        {
            "term": r.term,
            "term_type": r.term_type,
            "triggered_rule": r.triggered_rule,
            "suggested_action": r.suggested_action,
            "action_type": r.action_type,
            "confidence": r.confidence,
            "need_ai_judgment": r.need_ai_judgment,
            "ai_reasoning": getattr(r, "ai_reasoning", None),
            "data": r.data,
        }
        for r in raw_results
    ]

    # 应用筛选
    if action_filter:
        # 支持多种action_type格式
        results = [
            r
            for r in results
            if any(af in str(r.get("action_type", "")) for af in action_filter)
        ]

    if term_type_filter:
        results = [r for r in results if r.get("term_type") in term_type_filter]

    if ai_filter == "待AI确认":
        results = [
            r
            for r in results
            if r.get("need_ai_judgment", False) or r.get("confidence", 1.0) < 1.0
        ]
    elif ai_filter == "已确认":
        results = [
            r
            for r in results
            if not r.get("need_ai_judgment", False) and r.get("confidence", 1.0) >= 1.0
        ]

    if search_term:
        search_lower = search_term.lower()
        results = [r for r in results if search_lower in str(r.get("term", "")).lower()]

    # 显示结果统计
    st.subheader(f"分析结果 ({len(results)} 条)")

    if not results:
        st.warning("筛选后无数据")
        return

    # 获取已有的审核记录（提前获取用于统计）
    existing_reviews = db.get_manual_reviews(product_id)

    # 计算当前筛选结果中的审核状态
    reviewed_terms = set(
        term
        for (term, cid), review in existing_reviews.items()
        if cid is None and review.get("reviewed", 0) == 1
    )
    reviewed_in_results = len([r for r in results if r.get("term") in reviewed_terms])

    # 统计卡片（支持多种action_type格式：negative, negative_exact, negative_phrase等）
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        negative_count = len(
            [r for r in results if "negative" in str(r.get("action_type", ""))]
        )
        st.metric("建议否定", negative_count)
    with col2:
        manual_count = len(
            [r for r in results if "manual" in str(r.get("action_type", ""))]
        )
        st.metric("建议手动投放", manual_count)
    with col3:
        observe_count = len([r for r in results if r.get("action_type") == "observe"])
        st.metric("继续观察", observe_count)
    with col4:
        ai_pending = len(
            [
                r
                for r in results
                if r.get("need_ai_judgment", False) or r.get("confidence", 1.0) < 1.0
            ]
        )
        st.metric("待AI确认", ai_pending)
    with col5:
        st.metric("已审核", f"{reviewed_in_results}/{len(results)}")

    st.divider()

    # 结果表格
    df = pd.DataFrame(results)

    # 格式化显示（添加审核列）
    display_df = df[
        [
            "term",
            "term_type",
            "triggered_rule",
            "suggested_action",
            "action_type",
            "confidence",
        ]
    ].copy()
    display_df.columns = [
        "搜索词",
        "类型",
        "触发规则",
        "建议操作",
        "动作类型",
        "置信度",
    ]
    display_df["置信度"] = display_df["置信度"].apply(lambda x: f"{x:.2%}")

    # 添加已审核列（从数据库加载已有状态）
    display_df["已审核"] = display_df["搜索词"].apply(
        lambda term: existing_reviews.get((term, None), {}).get("reviewed", 0) == 1
    )

    # 使用 data_editor 支持勾选
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        disabled=["搜索词", "类型", "触发规则", "建议操作", "动作类型", "置信度"],
        column_config={
            "已审核": st.column_config.CheckboxColumn(
                "已审核",
                help="勾选表示已人工确认此建议",
                width="small",
            ),
            "搜索词": st.column_config.TextColumn("搜索词", width="large"),
            "类型": st.column_config.TextColumn("类型", width="small"),
            "触发规则": st.column_config.TextColumn("触发规则", width="medium"),
            "建议操作": st.column_config.TextColumn("建议操作", width="medium"),
            "动作类型": st.column_config.TextColumn("动作类型", width="small"),
            "置信度": st.column_config.TextColumn("置信度", width="small"),
        },
        column_order=[
            "已审核",
            "搜索词",
            "类型",
            "触发规则",
            "建议操作",
            "动作类型",
            "置信度",
        ],
        key="summary_review_editor",
    )

    # 保存审核状态变更
    save_review_changes(db, product_id, display_df, edited_df, results)

    st.divider()

    # AI 洞察报告
    product = db.get_product(product_id)
    product_name = product.get("name", "") if product else ""
    _render_ai_insights(results, product_name=product_name)

    st.divider()

    # 批量操作
    st.subheader("批量操作")

    # 审核操作行
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("全部标记为已审核", key="mark_all_reviewed"):
            # 将当前筛选结果中所有项标记为已审核
            count = 0
            for r in results:
                try:
                    db.upsert_manual_review(
                        product_id=product_id,
                        term=r["term"],
                        term_type=r.get("term_type", "keyword"),
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
            else:
                st.info("没有可标记的项目")

    with col2:
        if st.button("清除所有审核标记", key="clear_all_reviewed"):
            # 清除当前筛选结果中所有项的审核标记
            count = 0
            for r in results:
                try:
                    db.upsert_manual_review(
                        product_id=product_id,
                        term=r["term"],
                        term_type=r.get("term_type", "keyword"),
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
            else:
                st.info("没有可清除的项目")

    with col3:
        if st.button("AI分析待确认项", key="ai_analyze"):
            # need_ai_judgment 列不存在，用 confidence < 1.0 判断
            ai_pending_items = [r for r in results if r.get("confidence", 1.0) < 1.0]
            if ai_pending_items:
                # 使用进度条显示分析进度
                total = len(ai_pending_items)
                progress_bar = st.progress(0, text=f"AI分析中... 0/{total}")
                success_count = analyze_with_ai(
                    db, product_id, ai_pending_items, progress_bar
                )
                progress_bar.progress(1.0, text=f"分析完成: {success_count}/{total}")
                st.success(f"AI分析完成！成功分析 {success_count}/{total} 个关键词")
                st.rerun()
            else:
                st.info("没有待AI确认的项目")

    # 导出操作行
    st.caption("导出（仅导出已审核项）")
    col4, col5, col6 = st.columns(3)

    with col4:
        if st.button("导出否词表", key="export_negative"):
            export_reviewed_results(
                db, product_id, results, existing_reviews, "negative"
            )

    with col5:
        if st.button("导出手动词表", key="export_manual"):
            export_reviewed_results(db, product_id, results, existing_reviews, "manual")

    with col6:
        if st.button("导出全部结果", key="export_all"):
            export_reviewed_results(db, product_id, results, existing_reviews, "all")

    # 详情面板
    st.divider()
    st.subheader("详情查看")

    selected_term = st.selectbox(
        "选择查看详情",
        options=[r["term"] for r in results[:50]],  # 限制选项数量
        index=None,
        placeholder="选择一个搜索词查看详情...",
    )

    if selected_term:
        result = next((r for r in results if r["term"] == selected_term), None)
        if result:
            render_detail_panel(result)


def get_analysis_results(
    db,
    product_id: int,
    action_filter: list = None,
    term_type_filter: list = None,
    ai_filter: str = "全部",
    search_term: str = None,
) -> list[dict]:
    """获取分析结果"""
    try:
        df = db.get_analysis_results(filters={"product_id": product_id})

        if df.empty:
            return []

        results = df.to_dict("records")

        # 应用筛选
        if action_filter:
            results = [r for r in results if r.get("action_type") in action_filter]

        if term_type_filter:
            results = [r for r in results if r.get("term_type") in term_type_filter]

        # 注意：analysis_results表没有need_ai_judgment列，改为检查confidence
        if ai_filter == "待AI确认":
            results = [r for r in results if r.get("confidence", 1.0) < 1.0]
        elif ai_filter == "已确认":
            results = [r for r in results if r.get("confidence", 1.0) >= 1.0]

        if search_term:
            search_lower = search_term.lower()
            results = [
                r for r in results if search_lower in str(r.get("term", "")).lower()
            ]

        return results
    except Exception as e:
        logger.error(f"获取分析结果失败: {e}")
        return []


def run_full_analysis(db, product_id: int):
    """运行完整分析"""
    from src.data.aggregator import DataAggregator
    from src.rules.engine import RuleEngine

    # 聚合数据
    aggregator = DataAggregator(db)
    df = aggregator.aggregate_by_term(product_id)

    if df.empty:
        return

    # 规则分析
    engine = RuleEngine(db, product_id)
    results = engine.analyze(df)

    # 清除旧结果 - 通过search_term_id关联删除
    db.execute(
        """
        DELETE FROM analysis_results
        WHERE search_term_id IN (
            SELECT st.id FROM search_terms st
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ?
        )
        """,
        (product_id,),
    )
    db.commit()

    # 保存新结果
    for result in results:
        db.save_analysis_result_by_term(
            product_id=product_id,
            term=result.term,
            triggered_rule=result.triggered_rule,
            suggested_action=result.suggested_action,
            action_type=result.action_type,
            confidence=result.confidence,
            ai_reasoning=result.ai_reasoning,
        )


def analyze_with_ai(
    db,
    product_id: int,
    items: list[dict],
    progress_bar=None,
) -> int:
    """
    使用AI分析待确认项

    Args:
        db: 数据库实例
        product_id: 产品ID
        items: 待分析项目列表
        progress_bar: Streamlit进度条对象（可选）

    Returns:
        成功分析的项目数量
    """
    success_count = 0
    total = len(items)

    try:
        from src.ai.analyzer import AIAnalyzer

        # 获取产品配置
        product = db.get_product(product_id)
        product_context = product.get("config", {}) if product else {}
        product_context["name"] = product.get("name", "") if product else ""

        analyzer = AIAnalyzer()

        for idx, item in enumerate(items):
            term = item["term"]

            # 更新进度条
            if progress_bar is not None:
                progress = (idx + 1) / total
                progress_bar.progress(
                    progress,
                    text=f"AI分析中... {idx + 1}/{total}: {term[:30]}{'...' if len(term) > 30 else ''}",
                )

            try:
                result = analyzer.judge_relevance(
                    keyword=term,
                    product_context=product_context,
                )

                # 更新分析结果 - 通过 search_term_id 关联更新
                new_action = result.suggested_action
                db.execute(
                    """
                    UPDATE analysis_results
                    SET suggested_action = ?, confidence = 1.0, ai_reasoning = ?
                    WHERE search_term_id IN (
                        SELECT st.id FROM search_terms st
                        JOIN campaigns c ON st.campaign_id = c.id
                        WHERE c.product_id = ? AND st.term = ?
                    )
                    """,
                    (new_action, result.reason, product_id, term),
                )
                success_count += 1

            except Exception as e:
                logger.warning(f"分析关键词 '{term}' 失败: {e}")
                # 单个失败不影响其他项目的分析

        db.commit()

    except Exception as e:
        safe_error("AI分析", e)

    return success_count


def export_reviewed_results(
    db,
    product_id: int,
    results: list[dict],
    existing_reviews: dict,
    result_type: str,
):
    """
    导出已审核的结果

    Args:
        db: 数据库实例
        product_id: 产品ID
        results: 分析结果列表
        existing_reviews: 已有审核记录
        result_type: 导出类型 (negative/manual/all)
    """
    import datetime

    # 筛选已审核的项目
    reviewed_results = [
        r
        for r in results
        if existing_reviews.get((r.get("term"), None), {}).get("reviewed", 0) == 1
    ]

    if not reviewed_results:
        st.warning("没有已审核的项目可导出。请先在表格中勾选需要导出的项目。")
        return

    # 根据类型进一步筛选
    if result_type == "negative":
        filtered = [
            r
            for r in reviewed_results
            if "negative" in str(r.get("action_type", ""))
            or "否定" in str(r.get("suggested_action", ""))
        ]
        if not filtered:
            st.warning("没有已审核的否词项目")
            return
        export_df = pd.DataFrame(
            [
                {
                    "搜索词": r["term"],
                    "类型": r.get("term_type", "keyword"),
                    "触发规则": r.get("triggered_rule", ""),
                    "建议操作": r.get("suggested_action", ""),
                    "动作类型": r.get("action_type", ""),
                }
                for r in filtered
            ]
        )
        filename = (
            f"negative_reviewed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

    elif result_type == "manual":
        filtered = [
            r
            for r in reviewed_results
            if "manual" in str(r.get("action_type", ""))
            or "手动" in str(r.get("suggested_action", ""))
        ]
        if not filtered:
            st.warning("没有已审核的手动投放项目")
            return
        export_df = pd.DataFrame(
            [
                {
                    "搜索词": r["term"],
                    "类型": r.get("term_type", "keyword"),
                    "触发规则": r.get("triggered_rule", ""),
                    "建议操作": r.get("suggested_action", ""),
                    "动作类型": r.get("action_type", ""),
                }
                for r in filtered
            ]
        )
        filename = (
            f"manual_reviewed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

    else:  # all
        export_df = pd.DataFrame(
            [
                {
                    "搜索词": r["term"],
                    "类型": r.get("term_type", "keyword"),
                    "触发规则": r.get("triggered_rule", ""),
                    "建议操作": r.get("suggested_action", ""),
                    "动作类型": r.get("action_type", ""),
                    "置信度": f"{r.get('confidence', 1.0):.2%}",
                }
                for r in reviewed_results
            ]
        )
        filename = (
            f"all_reviewed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

    csv_data = export_df.to_csv(index=False, encoding="utf-8-sig")

    st.download_button(
        label=f"下载CSV ({len(export_df)}条)",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )
    st.success(f"准备导出 {len(export_df)} 条已审核记录")


def export_results(db, product_id: int, result_type: str):
    """导出结果

    修复v2.1: 使用实时计算代替数据库读取，确保导出数据与UI显示一致
    """
    try:
        from src.export.exporter import ReportExporter
        from src.rules.engine import AnalysisResult, analyze_search_terms

        # v2.1修复: 使用实时计算获取分析结果，而不是读取可能不完整的数据库
        raw_results = analyze_search_terms(db, product_id)

        if not raw_results:
            st.warning("没有可导出的数据")
            return

        # 转换为 AnalysisResult 对象（如果不是的话）
        results = []
        for r in raw_results:
            if isinstance(r, AnalysisResult):
                results.append(r)
            else:
                # 兼容dict格式
                need_ai = r.get("confidence", 1.0) < 1.0
                results.append(
                    AnalysisResult(
                        term=r["term"],
                        term_type=r["term_type"],
                        triggered_rule=r["triggered_rule"],
                        suggested_action=r["suggested_action"],
                        action_type=r.get("action_type"),
                        confidence=r.get("confidence", 1.0),
                        need_ai_judgment=need_ai,
                        data={},
                    )
                )

        exporter = ReportExporter()

        if result_type == "negative":
            filepath = exporter.export_negative_keywords(results)
            if filepath:
                st.success(f"导出成功: {filepath}")
                with open(filepath, "rb") as f:
                    st.download_button(
                        label="点击下载",
                        data=f.read(),
                        file_name=filepath.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
            else:
                st.warning("没有可导出的否词数据")
        elif result_type == "manual":
            filepath = exporter.export_manual_keywords(results)
            if filepath:
                st.success(f"导出成功: {filepath}")
                with open(filepath, "rb") as f:
                    st.download_button(
                        label="点击下载",
                        data=f.read(),
                        file_name=filepath.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
            else:
                st.warning("没有可导出的手动词数据")
        elif result_type == "all":
            # 导出全部结果为CSV
            import datetime

            export_df = pd.DataFrame(
                [
                    {
                        "搜索词": r.term,
                        "类型": r.term_type,
                        "触发规则": r.triggered_rule,
                        "建议操作": r.suggested_action,
                        "动作类型": r.action_type,
                        "置信度": f"{r.confidence:.2%}",
                    }
                    for r in results
                ]
            )

            csv_data = export_df.to_csv(index=False, encoding="utf-8-sig")
            filename = (
                f"all_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

            st.download_button(
                label="下载全部结果CSV",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
            )
            st.success(f"准备导出 {len(results)} 条记录")

    except Exception as e:
        safe_error("导出", e)


def _render_ai_insights(results: list, product_name: str = ""):
    """渲染AI洞察报告区块"""
    with st.expander("AI 洞察报告", expanded=False):
        if not results:
            st.info("暂无分析数据")
            return

        # 检查缓存
        cache_key = f"insight_report_{len(results)}_{product_name}"
        cached = st.session_state.get(cache_key)

        if cached:
            _display_insight_report(cached)
            if st.button("重新生成", key="regen_insights"):
                del st.session_state[cache_key]
                st.rerun()
            return

        if st.button("生成 AI 洞察报告", key="gen_insights"):
            with st.spinner("正在分析数据..."):
                try:
                    from src.ai.analyzer import AIAnalyzer
                    from src.ai.client import GeminiClient
                    from src.config.settings import get_settings

                    settings = get_settings()
                    if settings.is_api_configured:
                        client = GeminiClient(api_key=settings.gemini_api_key)
                    else:
                        client = None

                    analyzer = AIAnalyzer(client=client)
                    report = analyzer.generate_insights(
                        results,
                        product_context={"name": product_name},
                    )

                    st.session_state[cache_key] = report
                    _display_insight_report(report)

                except Exception as e:
                    safe_error("AI洞察报告生成", e)
        else:
            st.caption("点击按钮，AI 将基于当前分析结果生成洞察报告")


def _display_insight_report(report):
    """展示洞察报告内容"""
    if report.summary:
        st.markdown(f"**摘要:** {report.summary}")

    if report.key_findings:
        st.markdown("**关键发现:**")
        for finding in report.key_findings:
            st.markdown(f"- {finding}")

    if report.recommendations:
        st.markdown("**优化建议:**")
        for rec in report.recommendations:
            st.markdown(f"- {rec}")

    if report.statistics:
        stats = report.statistics
        cols = st.columns(4)
        with cols[0]:
            st.metric("搜索词总数", stats.get("total_terms", 0))
        with cols[1]:
            st.metric("建议否定", stats.get("negative_count", 0))
        with cols[2]:
            st.metric("建议手动", stats.get("manual_count", 0))
        with cols[3]:
            acos_val = stats.get("acos", 0)
            st.metric("整体ACOS", f"{acos_val:.1%}" if acos_val else "N/A")


def render_detail_panel(result: dict):
    """渲染详情面板"""
    col1, col2 = st.columns(2)

    with col1:
        st.write("**基本信息**")
        st.write(f"• 搜索词: `{result['term']}`")
        st.write(f"• 类型: {result['term_type']}")
        st.write(f"• 触发规则: {result['triggered_rule']}")
        st.write(f"• 建议操作: {result['suggested_action']}")
        st.write(f"• 置信度: {result['confidence']:.2%}")

    with col2:
        st.write("**表现数据**")
        data = result.get("data", {})
        if data:
            st.write(f"• 花费: ${data.get('total_spend', data.get('spend', 0)):.2f}")
            st.write(f"• 点击: {data.get('total_clicks', data.get('clicks', 0))}")
            st.write(f"• 订单: {data.get('total_orders', data.get('orders', 0))}")
            st.write(f"• 销售额: ${data.get('total_sales', data.get('sales', 0)):.2f}")

    if result.get("ai_reasoning"):
        st.write("**AI分析**")
        st.info(result["ai_reasoning"])


def render_campaign_analysis(db, product_id: int):
    """渲染按活动分析模式页面"""
    from src.rules.engine import analyze_search_terms_by_campaign

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
            r for r in filtered_results if r.get("action_type") in action_filter
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
