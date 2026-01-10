"""
搜索词分析页面
核心分析界面，支持多维筛选和AI分析
"""

import streamlit as st
import pandas as pd

from src.config.logger import get_logger

logger = get_logger(__name__)


def render_analysis():
    """渲染搜索词分析页面"""
    st.title("🔍 搜索词分析")

    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    if not product_id:
        st.warning("请先选择产品")
        return

    # 筛选面板
    with st.expander("🔧 筛选条件", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            action_filter = st.multiselect(
                "动作类型",
                options=["negative", "manual", "observe", "evaluate"],
                default=[],
                format_func=lambda x: {
                    "negative": "🔴 建议否定",
                    "manual": "🟢 建议手动投放",
                    "observe": "🟡 继续观察",
                    "evaluate": "🔵 需评估",
                }.get(x, x),
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
            )

        with col3:
            ai_filter = st.selectbox(
                "AI确认状态",
                options=["全部", "待AI确认", "已确认"],
                index=0,
            )

        with col4:
            search_term = st.text_input("搜索关键词", placeholder="输入搜索...")

    # 获取分析结果
    results = get_analysis_results(
        db,
        product_id,
        action_filter=action_filter,
        term_type_filter=term_type_filter,
        ai_filter=ai_filter,
        search_term=search_term,
    )

    if not results:
        st.info("暂无分析结果。请先上传数据并运行分析。")

        if st.button("运行分析"):
            with st.spinner("正在分析..."):
                run_full_analysis(db, product_id)
                st.success("分析完成！")
                st.rerun()
        return

    # 显示结果统计
    st.subheader(f"📊 分析结果 ({len(results)} 条)")

    # 统计卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        negative_count = len([r for r in results if r["action_type"] == "negative"])
        st.metric("建议否定", negative_count)
    with col2:
        manual_count = len([r for r in results if r["action_type"] == "manual"])
        st.metric("建议手动投放", manual_count)
    with col3:
        observe_count = len([r for r in results if r["action_type"] == "observe"])
        st.metric("继续观察", observe_count)
    with col4:
        ai_pending = len([r for r in results if r["need_ai_judgment"]])
        st.metric("待AI确认", ai_pending)

    st.divider()

    # 结果表格
    df = pd.DataFrame(results)

    # 格式化显示
    display_df = df[["term", "term_type", "triggered_rule", "suggested_action", "action_type", "confidence"]].copy()
    display_df.columns = ["搜索词", "类型", "触发规则", "建议操作", "动作类型", "置信度"]
    display_df["置信度"] = display_df["置信度"].apply(lambda x: f"{x:.0%}")

    # 使用 data_editor 支持选择
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "搜索词": st.column_config.TextColumn("搜索词", width="large"),
            "类型": st.column_config.TextColumn("类型", width="small"),
            "触发规则": st.column_config.TextColumn("触发规则", width="medium"),
            "建议操作": st.column_config.TextColumn("建议操作", width="medium"),
            "动作类型": st.column_config.TextColumn("动作类型", width="small"),
            "置信度": st.column_config.TextColumn("置信度", width="small"),
        },
    )

    st.divider()

    # 批量操作
    st.subheader("🔧 批量操作")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🤖 AI分析待确认项", use_container_width=True):
            ai_pending_items = [r for r in results if r["need_ai_judgment"]]
            if ai_pending_items:
                with st.spinner("AI正在分析..."):
                    analyze_with_ai(db, product_id, ai_pending_items)
                    st.success("AI分析完成！")
                    st.rerun()
            else:
                st.info("没有待AI确认的项目")

    with col2:
        if st.button("📥 导出否词表", use_container_width=True):
            export_results(db, product_id, "negative")

    with col3:
        if st.button("📥 导出手动词表", use_container_width=True):
            export_results(db, product_id, "manual")

    # 详情面板
    st.divider()
    st.subheader("📋 详情查看")

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
        results = db.get_analysis_results(product_id=product_id)

        # 应用筛选
        if action_filter:
            results = [r for r in results if r["action_type"] in action_filter]

        if term_type_filter:
            results = [r for r in results if r["term_type"] in term_type_filter]

        if ai_filter == "待AI确认":
            results = [r for r in results if r["need_ai_judgment"]]
        elif ai_filter == "已确认":
            results = [r for r in results if not r["need_ai_judgment"]]

        if search_term:
            search_lower = search_term.lower()
            results = [r for r in results if search_lower in r["term"].lower()]

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

    # 清除旧结果
    db.execute("DELETE FROM analysis_results WHERE product_id = ?", (product_id,))
    db.commit()

    # 保存新结果
    for result in results:
        db.save_analysis_result(
            product_id=product_id,
            term=result.term,
            term_type=result.term_type,
            triggered_rule=result.triggered_rule,
            suggested_action=result.suggested_action,
            action_type=result.action_type,
            confidence=result.confidence,
            need_ai_judgment=result.need_ai_judgment,
            data=result.data,
        )


def analyze_with_ai(db, product_id: int, items: list[dict]):
    """使用AI分析待确认项"""
    try:
        from src.ai.analyzer import AIAnalyzer

        # 获取产品配置
        product = db.get_product(product_id)
        product_context = product.get("config", {}) if product else {}
        product_context["name"] = product.get("name", "") if product else ""

        analyzer = AIAnalyzer()

        for item in items:
            result = analyzer.judge_relevance(
                keyword=item["term"],
                product_context=product_context,
            )

            # 更新分析结果
            new_action = result.suggested_action
            db.execute(
                """
                UPDATE analysis_results
                SET suggested_action = ?, need_ai_judgment = 0, ai_reasoning = ?
                WHERE product_id = ? AND term = ?
                """,
                (new_action, result.reason, product_id, item["term"]),
            )

        db.commit()

    except Exception as e:
        logger.error(f"AI分析失败: {e}")
        st.error(f"AI分析失败: {str(e)}")


def export_results(db, product_id: int, result_type: str):
    """导出结果"""
    try:
        from src.export.exporter import ReportExporter
        from src.rules.engine import AnalysisResult

        results_data = db.get_analysis_results(product_id=product_id)

        # 转换为 AnalysisResult 对象
        results = []
        for r in results_data:
            results.append(AnalysisResult(
                term=r["term"],
                term_type=r["term_type"],
                triggered_rule=r["triggered_rule"],
                suggested_action=r["suggested_action"],
                action_type=r["action_type"],
                confidence=r["confidence"],
                need_ai_judgment=r["need_ai_judgment"],
                data=r.get("data", {}),
            ))

        exporter = ReportExporter()

        if result_type == "negative":
            filepath = exporter.export_negative_keywords(results)
        else:
            filepath = exporter.export_manual_keywords(results)

        if filepath:
            st.success(f"✅ 导出成功: {filepath}")

            # 提供下载
            with open(filepath, "rb") as f:
                st.download_button(
                    label="📥 点击下载",
                    data=f.read(),
                    file_name=filepath.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        else:
            st.warning("没有可导出的数据")

    except Exception as e:
        logger.error(f"导出失败: {e}")
        st.error(f"导出失败: {str(e)}")


def render_detail_panel(result: dict):
    """渲染详情面板"""
    col1, col2 = st.columns(2)

    with col1:
        st.write("**基本信息**")
        st.write(f"• 搜索词: `{result['term']}`")
        st.write(f"• 类型: {result['term_type']}")
        st.write(f"• 触发规则: {result['triggered_rule']}")
        st.write(f"• 建议操作: {result['suggested_action']}")
        st.write(f"• 置信度: {result['confidence']:.0%}")

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
