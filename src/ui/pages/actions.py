"""
操作清单页面
展示待执行的否词和手动投放操作
"""

import pandas as pd
import streamlit as st

from src.config.logger import get_logger
from src.ui.utils import safe_error

logger = get_logger(__name__)


def render_actions():
    """渲染操作清单页面"""
    st.title("📋 操作清单")

    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    if not product_id:
        st.warning("请先选择产品")
        return

    # 获取产品信息
    product = db.get_product(product_id)
    product_name = product.get("name", "未知产品") if product else "未知产品"

    st.subheader(f"产品: {product_name}")

    # 标签页切换
    tab1, tab2, tab3 = st.tabs(["🔴 否词操作", "🟢 手动投放", "📊 操作历史"])

    with tab1:
        render_negative_actions(db, product_id)

    with tab2:
        render_manual_actions(db, product_id)

    with tab3:
        render_action_history(db, product_id)


def render_negative_actions(db, product_id: int):
    """渲染否词操作清单"""
    st.write("### 待否定关键词")

    # 获取需要否定的词 - 使用 filters 参数，返回 DataFrame
    df = db.get_analysis_results(filters={"product_id": product_id})
    if df.empty:
        st.info("暂无待否定的关键词")
        return
    results = df.to_dict("records")
    negative_items = [r for r in results if r["action_type"] == "negative"]

    if not negative_items:
        st.info("暂无待否定的关键词")
        return

    # 按否定类型分组
    exact_negatives = []
    phrase_negatives = []

    for item in negative_items:
        if "精确" in item.get("suggested_action", ""):
            exact_negatives.append(item)
        else:
            phrase_negatives.append(item)

    # 精确否定
    if exact_negatives:
        st.write("#### 精确否定")
        df_exact = pd.DataFrame([
            {
                "关键词": item["term"],
                "触发规则": item["triggered_rule"],
                "花费": f"${item.get('data', {}).get('total_spend', item.get('data', {}).get('spend', 0)):.2f}",
                "点击": item.get("data", {}).get("total_clicks", item.get("data", {}).get("clicks", 0)),
                "订单": item.get("data", {}).get("total_orders", item.get("data", {}).get("orders", 0)),
            }
            for item in exact_negatives
        ])
        st.dataframe(df_exact, use_container_width=True, hide_index=True)

        # 复制按钮
        keywords_text = "\n".join([item["term"] for item in exact_negatives])
        st.text_area(
            "精确否定词列表（复制到亚马逊后台）",
            value=keywords_text,
            height=100,
            key="exact_negative_list",
        )

    # 短语否定
    if phrase_negatives:
        st.write("#### 短语否定")
        df_phrase = pd.DataFrame([
            {
                "关键词": item["term"],
                "触发规则": item["triggered_rule"],
                "花费": f"${item.get('data', {}).get('total_spend', item.get('data', {}).get('spend', 0)):.2f}",
                "点击": item.get("data", {}).get("total_clicks", item.get("data", {}).get("clicks", 0)),
                "订单": item.get("data", {}).get("total_orders", item.get("data", {}).get("orders", 0)),
            }
            for item in phrase_negatives
        ])
        st.dataframe(df_phrase, use_container_width=True, hide_index=True)

        keywords_text = "\n".join([item["term"] for item in phrase_negatives])
        st.text_area(
            "短语否定词列表（复制到亚马逊后台）",
            value=keywords_text,
            height=100,
            key="phrase_negative_list",
        )

    st.divider()

    # 导出按钮
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 导出否词Excel", use_container_width=True):
            export_negative_excel(db, product_id)

    with col2:
        if st.button("📥 导出否词CSV（批量上传格式）", use_container_width=True):
            export_negative_csv(db, product_id)


def render_manual_actions(db, product_id: int):
    """渲染手动投放操作清单"""
    st.write("### 推荐手动投放关键词")

    # 获取需要手动投放的词 - 使用 filters 参数，返回 DataFrame
    df = db.get_analysis_results(filters={"product_id": product_id})
    if df.empty:
        st.info("暂无推荐手动投放的关键词")
        return
    results = df.to_dict("records")
    manual_items = [r for r in results if r["action_type"] == "manual"]

    if not manual_items:
        st.info("暂无推荐手动投放的关键词")
        return

    # 按优先级排序
    def get_priority_score(item):
        data = item.get("data", {})
        orders = data.get("total_orders", data.get("orders", 0))
        sales = data.get("total_sales", data.get("sales", 0))
        return orders * 10 + sales  # 简单优先级计算

    manual_items.sort(key=get_priority_score, reverse=True)

    # 显示表格
    df = pd.DataFrame([
        {
            "关键词": item["term"],
            "订单": item.get("data", {}).get("total_orders", item.get("data", {}).get("orders", 0)),
            "销售额": f"${item.get('data', {}).get('total_sales', item.get('data', {}).get('sales', 0)):.2f}",
            "花费": f"${item.get('data', {}).get('total_spend', item.get('data', {}).get('spend', 0)):.2f}",
            "ACOS": calculate_acos(item),
            "触发规则": item["triggered_rule"],
            "建议匹配": suggest_match_type(item),
        }
        for item in manual_items
    ])

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # 分匹配类型复制
    st.write("#### 按匹配类型复制")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**精确匹配**")
        exact_keywords = [item["term"] for item in manual_items[:10]]  # 前10个用精确
        st.text_area(
            "精确匹配词",
            value="\n".join(exact_keywords),
            height=100,
            key="exact_manual_list",
        )

    with col2:
        st.write("**短语匹配**")
        phrase_keywords = [item["term"] for item in manual_items[10:20]]  # 中间用短语
        st.text_area(
            "短语匹配词",
            value="\n".join(phrase_keywords) if phrase_keywords else "暂无",
            height=100,
            key="phrase_manual_list",
        )

    with col3:
        st.write("**广泛匹配**")
        broad_keywords = [item["term"] for item in manual_items[20:]]  # 其余用广泛
        st.text_area(
            "广泛匹配词",
            value="\n".join(broad_keywords) if broad_keywords else "暂无",
            height=100,
            key="broad_manual_list",
        )

    st.divider()

    # 导出按钮
    if st.button("📥 导出手动词Excel", use_container_width=True):
        export_manual_excel(db, product_id)


def render_action_history(db, product_id: int):
    """渲染操作历史"""
    st.write("### 操作历史")

    # 获取操作计划历史
    # action_plans 表没有 product_id，需要通过 analysis_results -> search_terms -> campaigns 关联
    try:
        cursor = db.execute(
            """
            SELECT
                ap.created_at,
                ap.action as action_type,
                st.term,
                ap.status
            FROM action_plans ap
            JOIN analysis_results ar ON ap.analysis_result_id = ar.id
            JOIN search_terms st ON ar.search_term_id = st.id
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ?
            ORDER BY ap.created_at DESC
            LIMIT 50
            """,
            (product_id,),
        )
        history = cursor.fetchall()

        if not history:
            st.info("暂无操作历史记录")
            return

        df = pd.DataFrame([
            {
                "时间": row["created_at"],
                "操作类型": row["action_type"],
                "关键词": row["term"],
                "状态": row["status"],
            }
            for row in history
        ])

        st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        logger.error(f"获取操作历史失败: {e}")
        st.info("暂无操作历史记录")


def calculate_acos(item: dict) -> str:
    """计算ACOS"""
    data = item.get("data", {})
    spend = data.get("total_spend", data.get("spend", 0))
    sales = data.get("total_sales", data.get("sales", 0))

    if sales > 0:
        acos = spend / sales
        return f"{acos:.2%}"
    return "N/A"


def suggest_match_type(item: dict) -> str:
    """建议匹配类型"""
    data = item.get("data", {})
    orders = data.get("total_orders", data.get("orders", 0))
    acos = 0
    spend = data.get("total_spend", data.get("spend", 0))
    sales = data.get("total_sales", data.get("sales", 0))

    if sales > 0:
        acos = spend / sales

    # 高转化低ACOS用精确
    if orders >= 5 and acos < 0.15:
        return "精确匹配"
    elif orders >= 3 and acos < 0.25:
        return "短语匹配"
    else:
        return "广泛匹配"


def export_negative_excel(db, product_id: int):
    """导出否词Excel"""
    try:
        from src.export.exporter import ReportExporter
        from src.rules.engine import AnalysisResult

        df = db.get_analysis_results(filters={"product_id": product_id})

        if df.empty:
            st.warning("没有可导出的数据")
            return

        results_data = df.to_dict("records")

        # 转换为 AnalysisResult 对象
        # need_ai_judgment 根据 confidence 推断（<1.0 表示需要AI确认）
        results = []
        for r in results_data:
            need_ai = r.get("confidence", 1.0) < 1.0
            results.append(AnalysisResult(
                term=r["term"],
                term_type=r["term_type"],
                triggered_rule=r["triggered_rule"],
                suggested_action=r["suggested_action"],
                action_type=r["action_type"],
                confidence=r["confidence"],
                need_ai_judgment=need_ai,
                data=r.get("data", {}),
            ))

        exporter = ReportExporter()
        filepath = exporter.export_negative_keywords(results)

        if filepath:
            st.success(f"✅ 导出成功: {filepath}")
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
        safe_error("导出", e)


def export_negative_csv(db, product_id: int):
    """导出否词CSV（批量上传格式）"""
    try:
        from src.export.exporter import ReportExporter
        from src.rules.engine import AnalysisResult

        df = db.get_analysis_results(filters={"product_id": product_id})

        if df.empty:
            st.warning("没有可导出的数据")
            return

        results_data = df.to_dict("records")

        # need_ai_judgment 根据 confidence 推断
        results = []
        for r in results_data:
            need_ai = r.get("confidence", 1.0) < 1.0
            results.append(AnalysisResult(
                term=r["term"],
                term_type=r["term_type"],
                triggered_rule=r["triggered_rule"],
                suggested_action=r["suggested_action"],
                action_type=r["action_type"],
                confidence=r["confidence"],
                need_ai_judgment=need_ai,
                data=r.get("data", {}),
            ))

        exporter = ReportExporter()
        filepath = exporter.export_to_csv(results, result_type="negative")

        if filepath:
            st.success(f"✅ 导出成功: {filepath}")
            with open(filepath, "rb") as f:
                st.download_button(
                    label="📥 点击下载",
                    data=f.read(),
                    file_name=filepath.name,
                    mime="text/csv",
                )
        else:
            st.warning("没有可导出的数据")

    except Exception as e:
        safe_error("导出", e)


def export_manual_excel(db, product_id: int):
    """导出手动词Excel"""
    try:
        from src.export.exporter import ReportExporter
        from src.rules.engine import AnalysisResult

        df = db.get_analysis_results(filters={"product_id": product_id})

        if df.empty:
            st.warning("没有可导出的数据")
            return

        results_data = df.to_dict("records")

        # need_ai_judgment 根据 confidence 推断
        results = []
        for r in results_data:
            need_ai = r.get("confidence", 1.0) < 1.0
            results.append(AnalysisResult(
                term=r["term"],
                term_type=r["term_type"],
                triggered_rule=r["triggered_rule"],
                suggested_action=r["suggested_action"],
                action_type=r["action_type"],
                confidence=r["confidence"],
                need_ai_judgment=need_ai,
                data=r.get("data", {}),
            ))

        exporter = ReportExporter()
        filepath = exporter.export_manual_keywords(results)

        if filepath:
            st.success(f"✅ 导出成功: {filepath}")
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
        safe_error("导出", e)
