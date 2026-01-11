"""
AMZ搜索词分析系统 - Streamlit主应用
"""

import streamlit as st

from src.config.logger import get_logger
from src.config.settings import Settings
from src.data.db import Database

logger = get_logger(__name__)

# 页面配置
st.set_page_config(
    page_title="AMZ搜索词分析系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """初始化Session State"""
    if "db" not in st.session_state:
        settings = Settings()
        st.session_state.db = Database(settings.database_path)
        st.session_state.db.init_schema()
        st.session_state.db.init_default_rules()

    if "current_product_id" not in st.session_state:
        st.session_state.current_product_id = None

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("🔍 AMZ搜索词分析")
        st.divider()

        # 导航菜单
        NAV_OPTIONS = ["首页", "文件上传", "搜索词分析", "操作清单", "系统设置"]

        # 初始化导航状态
        if "nav_page" not in st.session_state:
            st.session_state.nav_page = "首页"

        # 计算当前索引（支持快速操作按钮跳转）
        current_index = (
            NAV_OPTIONS.index(st.session_state.nav_page)
            if st.session_state.nav_page in NAV_OPTIONS
            else 0
        )

        page = st.radio(
            "导航",
            options=NAV_OPTIONS,
            index=current_index,
            key="nav_radio",
            label_visibility="collapsed",
        )

        # 同步radio选择到session_state
        if page != st.session_state.nav_page:
            st.session_state.nav_page = page

        st.divider()

        # 产品选择
        db = st.session_state.db
        products = db.get_all_products()

        if products:
            product_options = {p["name"]: p["id"] for p in products}
            selected_product = st.selectbox(
                "当前产品",
                options=list(product_options.keys()),
                index=0 if products else None,
            )
            if selected_product:
                st.session_state.current_product_id = product_options[selected_product]
        else:
            st.info("请先上传数据或创建产品")

        st.divider()

        # AI助手入口
        with st.expander("🤖 AI助手", expanded=False):
            render_ai_chat()

        return page


def render_ai_chat():
    """渲染AI对话（侧边栏版本）"""
    # 显示历史消息
    for msg in st.session_state.chat_messages[-5:]:  # 只显示最近5条
        with st.chat_message(msg["role"]):
            st.write(msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"])

    # 输入框
    user_input = st.text_input("问点什么...", key="sidebar_chat_input")

    if user_input:
        # 添加用户消息
        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_input,
        })

        # 获取AI响应（简化版本）
        try:
            from src.ai.chat import ChatAssistant

            assistant = ChatAssistant(
                db=st.session_state.db,
                product_id=st.session_state.current_product_id,
            )
            response = assistant.process_message(user_input)

            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": response.message,
            })
        except Exception as e:
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": f"抱歉，处理请求时出错: {str(e)}",
            })

        st.rerun()

    # 清除对话按钮
    if st.button("清除对话", use_container_width=True):
        st.session_state.chat_messages = []
        st.rerun()


def main():
    """主函数"""
    # 初始化
    init_session_state()

    # 渲染侧边栏并获取当前页面
    current_page = render_sidebar()

    # 根据页面显示内容
    if current_page == "首页":
        from src.ui.pages.home import render_home
        render_home()
    elif current_page == "文件上传":
        from src.ui.pages.upload import render_upload
        render_upload()
    elif current_page == "搜索词分析":
        from src.ui.pages.analysis import render_analysis
        render_analysis()
    elif current_page == "操作清单":
        from src.ui.pages.actions import render_actions
        render_actions()
    elif current_page == "系统设置":
        from src.ui.pages.settings import render_settings
        render_settings()


if __name__ == "__main__":
    main()
