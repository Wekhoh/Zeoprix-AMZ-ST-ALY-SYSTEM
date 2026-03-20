"""
操作清单页面
展示待执行的否词和手动投放操作
"""

import pandas as pd
import streamlit as st

from src.config.logger import get_logger
from src.rules.engine import analyze_search_terms
from src.ui.utils import safe_error

logger = get_logger(__name__)


def render_actions():
    """渲染操作清单页面"""
    st.title("操作清单")

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
    tab1, tab2, tab3 = st.tabs(["否词操作", "手动投放", "操作历史"])

    with tab1:
        render_negative_actions(db, product_id)

    with tab2:
        render_manual_actions(db, product_id)

    with tab3:
        render_action_history(db, product_id)


def render_negative_actions(db, product_id: int):
    """渲染否词操作清单"""
    st.write("### 待否定关键词")

    # 使用实时分析结果（与搜索词分析页面保持一致）
    analysis_results = analyze_search_terms(db, product_id)
    if not analysis_results:
        st.info("暂无待否定的关键词")
        return

    # 转换为dict格式以兼容现有代码
    # 注意: aggregate_by_term 返回的字段是 total_spend, total_clicks 等
    negative_items = []
    for r in analysis_results:
        # action_type 可能是 negative_exact, negative_phrase 等
        if r.action_type and r.action_type.startswith("negative"):
            negative_items.append(
                {
                    "term": r.term,
                    "term_type": r.term_type,
                    "triggered_rule": r.triggered_rule,
                    "suggested_action": r.suggested_action,
                    "action_type": r.action_type,
                    "confidence": r.confidence,
                    "spend": r.data.get("total_spend", r.data.get("spend", 0)),
                    "clicks": r.data.get("total_clicks", r.data.get("clicks", 0)),
                    "orders": r.data.get("total_orders", r.data.get("orders", 0)),
                    "sales": r.data.get("total_sales", r.data.get("sales", 0)),
                }
            )

    if not negative_items:
        st.info("暂无待否定的关键词")
        return

    # 按否定类型分组 - 区分关键词和ASIN
    exact_negatives = []  # 关键词精确否定
    phrase_negatives = []  # 关键词短语否定
    product_negatives = []  # ASIN商品否定

    for item in negative_items:
        # 首先按term_type区分ASIN和关键词
        if item.get("term_type") == "asin":
            product_negatives.append(item)
        elif "精准" in item.get("suggested_action", "") or "精确" in item.get(
            "suggested_action", ""
        ):
            exact_negatives.append(item)
        else:
            phrase_negatives.append(item)

    # 关键词精确否定
    if exact_negatives:
        st.write("#### 关键词精确否定")
        df_exact = pd.DataFrame(
            [
                {
                    "关键词": item["term"],
                    "触发规则": item["triggered_rule"],
                    "花费": f"${item.get('spend', 0):.2f}",
                    "点击": item.get("clicks", 0),
                    "订单": item.get("orders", 0),
                }
                for item in exact_negatives
            ]
        )
        st.dataframe(df_exact, width="stretch", hide_index=True)

        # 复制按钮
        keywords_text = "\n".join([item["term"] for item in exact_negatives])
        st.text_area(
            "精确否定词列表（复制到亚马逊后台）",
            value=keywords_text,
            height=100,
            key="exact_negative_list",
        )

    # 关键词短语否定
    if phrase_negatives:
        st.write("#### 关键词短语否定")
        df_phrase = pd.DataFrame(
            [
                {
                    "关键词": item["term"],
                    "触发规则": item["triggered_rule"],
                    "花费": f"${item.get('spend', 0):.2f}",
                    "点击": item.get("clicks", 0),
                    "订单": item.get("orders", 0),
                }
                for item in phrase_negatives
            ]
        )
        st.dataframe(df_phrase, width="stretch", hide_index=True)

        keywords_text = "\n".join([item["term"] for item in phrase_negatives])
        st.text_area(
            "短语否定词列表（复制到亚马逊后台）",
            value=keywords_text,
            height=100,
            key="phrase_negative_list",
        )

    # ASIN商品否定
    if product_negatives:
        st.write("#### ASIN商品否定")
        df_product = pd.DataFrame(
            [
                {
                    "ASIN": item["term"],
                    "触发规则": item["triggered_rule"],
                    "花费": f"${item.get('spend', 0):.2f}",
                    "点击": item.get("clicks", 0),
                    "订单": item.get("orders", 0),
                }
                for item in product_negatives
            ]
        )
        st.dataframe(df_product, width="stretch", hide_index=True)

        asins_text = "\n".join([item["term"] for item in product_negatives])
        st.text_area(
            "商品否定ASIN列表（复制到亚马逊后台）",
            value=asins_text,
            height=100,
            key="product_negative_list",
        )

    st.divider()

    # 导出按钮
    col1, col2 = st.columns(2)

    with col1:
        if st.button("导出否词Excel", width="stretch"):
            export_negative_excel(db, product_id)

    with col2:
        if st.button("导出否词CSV（批量上传格式）", width="stretch"):
            export_negative_csv(db, product_id)


def render_manual_actions(db, product_id: int):
    """渲染手动投放操作清单"""
    st.write("### 推荐手动投放")

    # 使用实时分析结果（与搜索词分析页面保持一致）
    analysis_results = analyze_search_terms(db, product_id)
    if not analysis_results:
        st.info("暂无推荐手动投放的关键词")
        return

    # 转换为dict格式以兼容现有代码 - 区分关键词和ASIN
    # 注意: aggregate_by_term 返回的字段是 total_spend, total_clicks 等
    manual_keywords = []  # 关键词手动投放
    manual_products = []  # ASIN商品定位

    for r in analysis_results:
        # action_type 可能是 manual_exact, manual_product 等
        if r.action_type and r.action_type.startswith("manual"):
            item = {
                "term": r.term,
                "term_type": r.term_type,
                "triggered_rule": r.triggered_rule,
                "suggested_action": r.suggested_action,
                "action_type": r.action_type,
                "confidence": r.confidence,
                "spend": r.data.get("total_spend", r.data.get("spend", 0)),
                "clicks": r.data.get("total_clicks", r.data.get("clicks", 0)),
                "orders": r.data.get("total_orders", r.data.get("orders", 0)),
                "sales": r.data.get("total_sales", r.data.get("sales", 0)),
            }
            # 按term_type区分
            if r.term_type == "asin":
                manual_products.append(item)
            else:
                manual_keywords.append(item)

    if not manual_keywords and not manual_products:
        st.info("暂无推荐手动投放的关键词")
        return

    # 按优先级排序
    def get_priority_score(item):
        orders = item.get("orders", 0)
        sales = item.get("sales", 0)
        return orders * 10 + sales  # 简单优先级计算

    manual_keywords.sort(key=get_priority_score, reverse=True)
    manual_products.sort(key=get_priority_score, reverse=True)

    # ========== 关键词手动投放 ==========
    if manual_keywords:
        st.write("#### 关键词手动投放")
        df_keywords = pd.DataFrame(
            [
                {
                    "关键词": item["term"],
                    "订单": item.get("orders", 0),
                    "销售额": f"${item.get('sales', 0):.2f}",
                    "花费": f"${item.get('spend', 0):.2f}",
                    "ACOS": calculate_acos(item),
                    "触发规则": item["triggered_rule"],
                    "建议匹配": suggest_match_type(item),
                }
                for item in manual_keywords
            ]
        )
        st.dataframe(df_keywords, width="stretch", hide_index=True)

        st.divider()

        # 分匹配类型复制 - 根据action_type实际分类
        st.write("##### 按匹配类型复制")

        # 根据实际匹配类型分组（不再硬编码按位置切分）
        exact_keywords = [
            item["term"]
            for item in manual_keywords
            if suggest_match_type(item) == "精确匹配"
        ]
        phrase_keywords = [
            item["term"]
            for item in manual_keywords
            if suggest_match_type(item) == "短语匹配"
        ]

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**精确匹配** ({len(exact_keywords)}个)")
            st.text_area(
                "精确匹配词（复制到亚马逊后台）",
                value="\n".join(exact_keywords) if exact_keywords else "暂无",
                height=150,
                key="exact_manual_list",
            )

        with col2:
            st.write(f"**短语匹配** ({len(phrase_keywords)}个)")
            st.text_area(
                "短语匹配词（复制到亚马逊后台）",
                value="\n".join(phrase_keywords) if phrase_keywords else "暂无",
                height=150,
                key="phrase_manual_list",
            )

    # ========== ASIN商品定位 ==========
    if manual_products:
        st.write("#### ASIN商品定位")
        df_products = pd.DataFrame(
            [
                {
                    "ASIN": item["term"],
                    "订单": item.get("orders", 0),
                    "销售额": f"${item.get('sales', 0):.2f}",
                    "花费": f"${item.get('spend', 0):.2f}",
                    "ACOS": calculate_acos(item),
                    "触发规则": item["triggered_rule"],
                }
                for item in manual_products
            ]
        )
        st.dataframe(df_products, width="stretch", hide_index=True)

        # ASIN没有匹配类型，直接复制列表
        asins_text = "\n".join([item["term"] for item in manual_products])
        st.text_area(
            "商品定位ASIN列表（复制到亚马逊后台）",
            value=asins_text,
            height=100,
            key="product_manual_list",
        )

    st.divider()

    # 导出按钮
    if st.button("导出手动词Excel", width="stretch"):
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

        df = pd.DataFrame(
            [
                {
                    "时间": row["created_at"],
                    "操作类型": row["action_type"],
                    "关键词": row["term"],
                    "状态": row["status"],
                }
                for row in history
            ]
        )

        st.dataframe(df, width="stretch", hide_index=True)

    except Exception as e:
        logger.error(f"获取操作历史失败: {e}")
        st.info("暂无操作历史记录")


def calculate_acos(item: dict) -> str:
    """计算ACOS"""
    spend = item.get("spend", 0)
    sales = item.get("sales", 0)

    if sales > 0:
        acos = spend / sales
        return f"{acos:.2%}"
    return "N/A"


def suggest_match_type(item: dict) -> str:
    """
    建议匹配类型 - 基于规则引擎的action_type

    用户手动标注的"手动精准"应该显示"精确匹配"，而不是根据ACOS/订单自动推断
    """
    action_type = item.get("action_type", "")

    # 根据action_type确定匹配类型
    # manual_exact, manual_exact_no_neg, manual_exact_with_neg → 精确匹配
    if "manual_exact" in action_type:
        return "精确匹配"

    # manual_phrase（如果有）→ 短语匹配
    if "manual_phrase" in action_type:
        return "短语匹配"

    # manual_product → 商品定位（ASIN没有匹配类型，但保险起见）
    if "manual_product" in action_type:
        return "商品定位"

    # 默认：精确匹配（用户的Excel标注大多是"手动精准"）
    return "精确匹配"


def export_negative_excel(db, product_id: int):
    """导出否词Excel"""
    try:
        from src.export.exporter import ReportExporter

        # 使用实时分析结果（与搜索词分析页面保持一致）
        results = analyze_search_terms(db, product_id)

        if not results:
            st.warning("没有可导出的数据")
            return

        exporter = ReportExporter()
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
            st.warning("没有可导出的数据")

    except Exception as e:
        safe_error("导出", e)


def export_negative_csv(db, product_id: int):
    """导出否词CSV（批量上传格式）"""
    try:
        from src.export.exporter import ReportExporter

        # 使用实时分析结果（与搜索词分析页面保持一致）
        results = analyze_search_terms(db, product_id)

        if not results:
            st.warning("没有可导出的数据")
            return

        exporter = ReportExporter()
        filepath = exporter.export_to_csv(results, result_type="negative")

        if filepath:
            st.success(f"导出成功: {filepath}")
            with open(filepath, "rb") as f:
                st.download_button(
                    label="点击下载",
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

        # 使用实时分析结果（与搜索词分析页面保持一致）
        results = analyze_search_terms(db, product_id)

        if not results:
            st.warning("没有可导出的数据")
            return

        exporter = ReportExporter()
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
            st.warning("没有可导出的数据")

    except Exception as e:
        safe_error("导出", e)
