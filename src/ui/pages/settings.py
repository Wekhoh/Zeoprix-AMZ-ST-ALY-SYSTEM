"""
系统设置页面
管理规则配置、产品配置和系统参数
"""


import streamlit as st

from src.config.logger import get_logger
from src.ui.pages.settings_rules import (
    render_rule_settings,
    render_rule_management,
)
from src.ui.pages.settings_data import (
    render_keyword_library_settings,
    render_data_management,
)
from src.ui.utils import safe_error

logger = get_logger(__name__)


def render_settings():
    """渲染系统设置页面"""
    st.title("系统设置")

    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    # 标签页
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["规则配置", "规则管理", "关键词库", "产品配置", "API设置", "数据管理"]
    )

    with tab1:
        render_rule_settings(db, product_id)

    with tab2:
        render_rule_management(db, product_id)

    with tab3:
        render_keyword_library_settings(db, product_id)

    with tab4:
        render_product_settings(db, product_id)

    with tab5:
        render_api_settings()

    with tab6:
        render_data_management(db, product_id)


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

        # 从config中读取核心关键词
        config = product.get("config", {}) or {}
        core_keywords = config.get("core_keywords", [])
        product_keywords = st.text_area(
            "核心关键词（每行一个）",
            value="\n".join(core_keywords) if core_keywords else "",
            height=100,
            placeholder="travel pillow\nneck pillow",
        )

    st.divider()

    # 竞品ASIN - 从config中读取
    st.write("#### 竞品ASIN")

    comp_asins = config.get("competitor_asins", [])
    competitor_asins = st.text_area(
        "竞品ASIN列表（每行一个）",
        value="\n".join(comp_asins) if comp_asins else "",
        height=100,
        placeholder="B0XXXXXXXX\nB0YYYYYYYY",
    )

    if st.button("保存产品信息", type="primary", width="stretch"):
        try:
            # 解析关键词和竞品
            keywords = [k.strip() for k in product_keywords.split("\n") if k.strip()]
            competitors = [a.strip() for a in competitor_asins.split("\n") if a.strip()]

            # 获取现有config并更新
            existing_config = product.get("config", {}) or {}
            existing_config["core_keywords"] = keywords
            existing_config["competitor_asins"] = competitors

            # 使用 update_product 方法（自动处理JSON序列化和事务）
            db.update_product(
                product_id,
                name=product_name,
                asin=product_asin,
                category=product_category,
                config=existing_config,
            )

            st.success("产品信息已保存")
            st.rerun()
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
            st.success(f"已配置 (****{settings.gemini_api_key[-4:]})")
        else:
            st.error("未配置 - 请在 .env 文件中设置有效的 GEMINI_API_KEY")

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
            st.success(f"已切换到 {model_labels[selected_index]}")
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
