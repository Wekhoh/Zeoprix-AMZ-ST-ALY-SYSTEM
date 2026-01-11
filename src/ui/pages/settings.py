"""
系统设置页面
管理规则配置、产品配置和系统参数
"""

import json

import streamlit as st

from src.config.logger import get_logger
from src.ui.utils import safe_error

logger = get_logger(__name__)


def render_settings():
    """渲染系统设置页面"""
    st.title("⚙️ 系统设置")

    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    # 标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📏 规则配置", "📦 产品配置", "🔑 API设置", "📊 数据管理"])

    with tab1:
        render_rule_settings(db, product_id)

    with tab2:
        render_product_settings(db, product_id)

    with tab3:
        render_api_settings()

    with tab4:
        render_data_management(db, product_id)


def render_rule_settings(db, product_id: int):
    """渲染规则配置"""
    st.write("### 规则阈值配置")

    if not product_id:
        st.warning("请先选择产品")
        return

    # 获取产品配置
    product = db.get_product(product_id)
    config = product.get("config", {}) if product else {}

    # 否词规则
    st.write("#### 🔴 否词规则")

    col1, col2 = st.columns(2)

    with col1:
        high_spend_threshold = st.number_input(
            "高花费阈值 ($)",
            min_value=0.0,
            max_value=1000.0,
            value=float(config.get("high_spend_threshold", 10.0)),
            step=1.0,
            help="花费超过此值且零转化则建议否定",
        )

        low_ctr_threshold = st.number_input(
            "低点击率阈值",
            min_value=0.0,
            max_value=1.0,
            value=float(config.get("low_ctr_threshold", 0.001)),
            step=0.001,
            format="%.3f",
            help="点击率低于此值建议否定",
        )

    with col2:
        min_clicks_threshold = st.number_input(
            "最小点击数（统计有效性）",
            min_value=1,
            max_value=100,
            value=int(config.get("min_clicks_threshold", 10)),
            step=1,
            help="点击数需达到此值才进行分析",
        )

        high_acos_threshold = st.number_input(
            "高ACOS阈值",
            min_value=0.0,
            max_value=5.0,
            value=float(config.get("high_acos_threshold", 0.5)),
            step=0.05,
            format="%.2f",
            help="ACOS超过此值建议否定或降低出价",
        )

    st.divider()

    # 手动投放规则
    st.write("#### 🟢 手动投放规则")

    col1, col2 = st.columns(2)

    with col1:
        min_orders_for_manual = st.number_input(
            "最小订单数",
            min_value=1,
            max_value=50,
            value=int(config.get("min_orders_for_manual", 2)),
            step=1,
            help="订单数达到此值才建议手动投放",
        )

        target_acos = st.number_input(
            "目标ACOS",
            min_value=0.0,
            max_value=1.0,
            value=float(config.get("target_acos", 0.25)),
            step=0.05,
            format="%.2f",
            help="低于此ACOS值视为表现良好",
        )

    with col2:
        min_conversion_rate = st.number_input(
            "最小转化率",
            min_value=0.0,
            max_value=1.0,
            value=float(config.get("min_conversion_rate", 0.05)),
            step=0.01,
            format="%.2f",
            help="转化率需达到此值才建议手动投放",
        )

    st.divider()

    # 竞品规则
    st.write("#### 🔵 竞品ASIN规则")

    competitor_high_acos = st.number_input(
        "竞品高ACOS阈值",
        min_value=0.0,
        max_value=5.0,
        value=float(config.get("competitor_high_acos", 0.4)),
        step=0.05,
        format="%.2f",
        help="竞品ASIN的ACOS超过此值建议停止投放",
    )

    st.divider()

    # 保存按钮
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 保存配置", type="primary", use_container_width=True):
            new_config = {
                "high_spend_threshold": high_spend_threshold,
                "low_ctr_threshold": low_ctr_threshold,
                "min_clicks_threshold": min_clicks_threshold,
                "high_acos_threshold": high_acos_threshold,
                "min_orders_for_manual": min_orders_for_manual,
                "target_acos": target_acos,
                "min_conversion_rate": min_conversion_rate,
                "competitor_high_acos": competitor_high_acos,
            }

            try:
                # 保存版本历史
                save_config_version(db, product_id, config, new_config)

                # 更新产品配置
                db.update_product_config(product_id, new_config)
                st.success("✅ 配置已保存！")
                st.rerun()
            except Exception as e:
                safe_error("配置保存", e)

    with col2:
        if st.button("🔄 恢复默认", use_container_width=True):
            try:
                default_config = get_default_config()
                db.update_product_config(product_id, default_config)
                st.success("✅ 已恢复默认配置！")
                st.rerun()
            except Exception as e:
                safe_error("配置恢复", e)

    # 版本历史
    st.divider()
    with st.expander("📜 配置版本历史"):
        render_config_history(db, product_id)


def render_product_settings(db, product_id: int):
    """渲染产品配置"""
    st.write("### 产品信息")

    if not product_id:
        st.warning("请先选择产品")
        return

    product = db.get_product(product_id)

    if not product:
        st.error("产品不存在")
        return

    col1, col2 = st.columns(2)

    with col1:
        product_name = st.text_input(
            "产品名称",
            value=product.get("name", ""),
        )

        product_asin = st.text_input(
            "ASIN",
            value=product.get("asin", ""),
        )

    with col2:
        product_category = st.text_input(
            "品类",
            value=product.get("category", ""),
            placeholder="例如：电子产品",
        )

        product_keywords = st.text_area(
            "核心关键词（每行一个）",
            value="\n".join(product.get("core_keywords", [])) if product.get("core_keywords") else "",
            height=100,
            placeholder="wireless charger\nphone charger",
        )

    st.divider()

    # 竞品ASIN
    st.write("#### 竞品ASIN")

    competitor_asins = st.text_area(
        "竞品ASIN列表（每行一个）",
        value="\n".join(product.get("competitor_asins", [])) if product.get("competitor_asins") else "",
        height=100,
        placeholder="B0XXXXXXXX\nB0YYYYYYYY",
    )

    if st.button("💾 保存产品信息", type="primary", use_container_width=True):
        try:
            # 解析关键词和竞品
            keywords = [k.strip() for k in product_keywords.split("\n") if k.strip()]
            competitors = [a.strip() for a in competitor_asins.split("\n") if a.strip()]

            db.execute(
                """
                UPDATE products
                SET name = ?, asin = ?, category = ?,
                    core_keywords = ?, competitor_asins = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    product_name,
                    product_asin,
                    product_category,
                    json.dumps(keywords),
                    json.dumps(competitors),
                    product_id,
                ),
            )
            db.commit()

            st.success("✅ 产品信息已保存！")
        except Exception as e:
            safe_error("产品信息保存", e)


def render_api_settings():
    """渲染API设置"""
    st.write("### API配置")

    st.info("API密钥存储在 .env 文件中，请手动编辑该文件来修改。")

    # 显示当前状态
    from src.config.settings import Settings

    settings = Settings()

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Gemini API**")
        if settings.is_api_configured:
            st.success(f"✅ 已配置 (****{settings.gemini_api_key[-4:]})")
        else:
            st.error("❌ 未配置 - 请在 .env 文件中设置有效的 GEMINI_API_KEY")

    with col2:
        st.write("**使用模型**")
        from src.config.settings import AVAILABLE_GEMINI_MODELS

        # 初始化session中的模型选择
        if "selected_gemini_model" not in st.session_state:
            st.session_state.selected_gemini_model = settings.gemini_model

        model_ids = [m[0] for m in AVAILABLE_GEMINI_MODELS]
        model_labels = [m[1] for m in AVAILABLE_GEMINI_MODELS]

        # 获取当前索引
        current_model = st.session_state.selected_gemini_model
        try:
            current_index = model_ids.index(current_model)
        except ValueError:
            current_index = 0  # 默认第一个

        selected_index = st.selectbox(
            "选择模型",
            options=range(len(model_labels)),
            index=current_index,
            format_func=lambda i: model_labels[i],
            key="model_selector",
            label_visibility="collapsed",
        )

        selected_model = model_ids[selected_index]

        # 更新session_state
        if selected_model != st.session_state.selected_gemini_model:
            st.session_state.selected_gemini_model = selected_model
            st.success(f"✅ 已切换到 {model_labels[selected_index]}")
            st.rerun()

    st.divider()

    # 配置说明
    st.write("#### 配置说明")
    st.markdown("""
    1. 在项目根目录创建 `.env` 文件
    2. 添加以下内容：
    ```
    GEMINI_API_KEY=your_api_key_here
    ```
    3. 重启应用生效

    **获取API Key**: [Google AI Studio](https://makersuite.google.com/app/apikey)
    """)


def render_data_management(db, product_id: int):
    """渲染数据管理"""
    st.write("### 数据管理")

    if not product_id:
        st.warning("请先选择产品")
        return

    # 数据统计
    st.write("#### 📊 数据统计")

    try:
        # 搜索词数量 - search_terms 没有 product_id，需要通过 campaigns 关联
        cursor = db.execute(
            """
            SELECT COUNT(*) as count FROM search_terms st
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ?
            """,
            (product_id,),
        )
        term_count = cursor.fetchone()["count"]

        # 分析结果数量 - analysis_results 没有 product_id，需要通过 search_terms→campaigns 关联
        cursor = db.execute(
            """
            SELECT COUNT(*) as count FROM analysis_results ar
            JOIN search_terms st ON ar.search_term_id = st.id
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ?
            """,
            (product_id,),
        )
        result_count = cursor.fetchone()["count"]

        # 广告活动数量
        cursor = db.execute(
            "SELECT COUNT(*) as count FROM campaigns WHERE product_id = ?",
            (product_id,),
        )
        campaign_count = cursor.fetchone()["count"]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("搜索词记录", term_count)

        with col2:
            st.metric("分析结果", result_count)

        with col3:
            st.metric("广告活动", campaign_count)

    except Exception as e:
        logger.error(f"获取数据统计失败: {e}")
        st.error("无法获取数据统计")

    st.divider()

    # 数据操作
    st.write("#### 🔧 数据操作")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 重新运行分析", use_container_width=True):
            with st.spinner("正在分析..."):
                try:
                    from src.ui.pages.upload import run_analysis

                    # 清除旧结果 - 通过 search_term_id 关联删除
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

                    run_analysis(db, product_id)
                    st.success("✅ 分析完成！")
                except Exception as e:
                    safe_error("数据分析", e)

    with col2:
        if st.button("🗑️ 清除分析结果", use_container_width=True):
            try:
                # 通过 search_term_id 关联删除
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
                st.success("✅ 分析结果已清除！")
            except Exception as e:
                safe_error("分析结果清除", e)

    st.divider()

    # 危险操作
    st.write("#### ⚠️ 危险操作")

    with st.expander("删除产品数据", expanded=False):
        st.warning("此操作将删除该产品的所有数据，包括搜索词、分析结果等。此操作不可恢复！")

        confirm_text = st.text_input(
            "输入产品名称确认删除",
            placeholder="输入产品名称...",
        )

        product = db.get_product(product_id)
        product_name = product.get("name", "") if product else ""

        if st.button("🗑️ 永久删除", type="secondary"):
            if confirm_text == product_name:
                try:
                    # 删除相关数据 - 注意顺序：先删子表，再删父表
                    # 1. 先删 analysis_results（通过 search_term_id 关联）
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
                    # 2. 删 search_terms（通过 campaign_id 关联）
                    db.execute(
                        """
                        DELETE FROM search_terms
                        WHERE campaign_id IN (
                            SELECT id FROM campaigns WHERE product_id = ?
                        )
                        """,
                        (product_id,),
                    )
                    # 3. 删 action_plans（通过 analysis_results -> search_terms -> campaigns 关联）
                    db.execute(
                        """
                        DELETE FROM action_plans
                        WHERE analysis_result_id IN (
                            SELECT ar.id FROM analysis_results ar
                            JOIN search_terms st ON ar.search_term_id = st.id
                            JOIN campaigns c ON st.campaign_id = c.id
                            WHERE c.product_id = ?
                        )
                        """,
                        (product_id,),
                    )
                    # 4. 删 campaigns（有 product_id）
                    db.execute("DELETE FROM campaigns WHERE product_id = ?", (product_id,))
                    # 5. 最后删 products
                    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
                    db.commit()

                    st.session_state.current_product_id = None
                    st.success("✅ 产品已删除！")
                    st.rerun()
                except Exception as e:
                    safe_error("产品删除", e)
            else:
                st.error("产品名称不匹配，请重新输入")


def get_default_config() -> dict:
    """获取默认配置"""
    return {
        "high_spend_threshold": 10.0,
        "low_ctr_threshold": 0.001,
        "min_clicks_threshold": 10,
        "high_acos_threshold": 0.5,
        "min_orders_for_manual": 2,
        "target_acos": 0.25,
        "min_conversion_rate": 0.05,
        "competitor_high_acos": 0.4,
    }


def save_config_version(db, product_id: int, old_config: dict, new_config: dict):
    """保存配置版本"""
    try:
        db.execute(
            """
            INSERT INTO rule_versions (product_id, old_config, new_config)
            VALUES (?, ?, ?)
            """,
            (product_id, json.dumps(old_config), json.dumps(new_config)),
        )
        db.commit()
    except Exception as e:
        logger.warning(f"保存配置版本失败: {e}")
        # 不阻止主流程


def render_config_history(db, product_id: int):
    """渲染配置历史"""
    try:
        cursor = db.execute(
            """
            SELECT * FROM rule_versions
            WHERE product_id = ?
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (product_id,),
        )
        versions = cursor.fetchall()

        if not versions:
            st.info("暂无版本历史")
            return

        for i, version in enumerate(versions):
            with st.container():
                st.write(f"**版本 {len(versions) - i}** - {version['created_at']}")

                col1, col2 = st.columns(2)

                with col1:
                    st.write("旧配置:")
                    st.json(json.loads(version["old_config"]) if version["old_config"] else {})

                with col2:
                    st.write("新配置:")
                    st.json(json.loads(version["new_config"]) if version["new_config"] else {})

                if st.button(f"回滚到此版本", key=f"rollback_{version['id']}"):
                    try:
                        old_config = json.loads(version["old_config"]) if version["old_config"] else {}
                        db.update_product_config(product_id, old_config)
                        st.success("✅ 已回滚！")
                        st.rerun()
                    except Exception as e:
                        safe_error("配置回滚", e)

                st.divider()

    except Exception as e:
        logger.error(f"获取配置历史失败: {e}")
        st.info("暂无版本历史")
