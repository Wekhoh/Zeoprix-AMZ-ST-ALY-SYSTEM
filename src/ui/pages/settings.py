"""
系统设置页面
管理规则配置、产品配置和系统参数
"""

from html import escape

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


SETTINGS_PAGE_CSS = """
<style>
.settings-hero {
    padding: 1.6rem 1.8rem;
    border-radius: 26px;
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,255,0.96) 100%);
    border: 1px solid rgba(59, 91, 219, 0.10);
    box-shadow: 0 16px 38px rgba(15, 23, 42, 0.06);
    margin-bottom: 1.2rem;
}
.settings-hero__eyebrow,
.settings-note__eyebrow {
    display: inline-flex;
    align-items: center;
    padding: 0.3rem 0.72rem;
    border-radius: 999px;
    background: rgba(59, 91, 219, 0.08);
    color: #3b5bdb;
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 0.95rem;
}
.settings-hero h1 {
    margin: 0;
    font-size: 2.05rem;
    line-height: 1.1;
    color: #0f172a;
}
.settings-hero p,
.settings-note p {
    margin: 0.85rem 0 0;
    color: #52607a;
    font-size: 1rem;
    line-height: 1.72;
}
.settings-hero__chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.7rem;
    margin-top: 1.1rem;
}
.settings-hero__chip {
    padding: 0.54rem 0.88rem;
    border-radius: 999px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    background: rgba(255,255,255,0.82);
    color: #334155;
    font-size: 0.9rem;
    font-weight: 600;
}
.settings-note {
    padding: 1rem 1.15rem;
    border-radius: 20px;
    background: rgba(255,255,255,0.78);
    border: 1px solid rgba(15, 23, 42, 0.06);
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
    margin-bottom: 1rem;
}
</style>
"""


def _build_settings_shell_meta(product_name: str | None) -> dict[str, str | list[str]]:
    """构建系统设置页的控制台文案。"""
    current_product = product_name or "未选择产品"
    return {
        "eyebrow": "规则控制台",
        "title": "系统设置",
        "description": "把规则、词库、产品信息和数据管理收在同一处，先定策略，再批量应用到当前产品。",
        "chips": [
            f"当前产品：{current_product}",
            "先调规则，再看分析页回放",
            "数据管理与规则设置分区阅读",
        ],
    }


def render_settings():
    """渲染系统设置页面"""
    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    product_name = None
    if product_id:
        product = db.get_product(product_id)
        if product:
            product_name = product.get("name")

    meta = _build_settings_shell_meta(product_name)
    chips_html = "".join(
        f'<div class="settings-hero__chip">{escape(chip)}</div>' for chip in meta["chips"]
    )
    st.markdown(SETTINGS_PAGE_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <section class="settings-hero">
            <div class="settings-hero__eyebrow">{escape(meta["eyebrow"])}</div>
            <h1>{escape(meta["title"])}</h1>
            <p>{escape(meta["description"])}</p>
            <div class="settings-hero__chips">{chips_html}</div>
        </section>
        <section class="settings-note">
            <div class="settings-note__eyebrow">建议顺序</div>
            <p>先改规则配置与关键词库，再看产品配置；API 设置和数据管理放在后面，避免一开始就掉进长表单里打滚。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

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
    st.caption("把产品名、ASIN、核心关键词和竞品列表收在一起，方便你从“规则”跳到“产品上下文”。")

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
    st.caption("API 设置主要用于确认模型和密钥状态，日常不需要频繁改动，把它当成运维区更合适。")

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
