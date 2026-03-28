"""
AMZ搜索词分析系统 - Streamlit主应用
"""

import sys
import os
from html import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from src.config.logger import get_logger
from src.config.settings import Settings
from src.data.db import Database
from src.ui.styles import inject_global_styles

logger = get_logger(__name__)

NAV_OPTIONS = [
    "首页",
    "文件上传",
    "搜索词分析",
    "ASIN分析",
    "操作清单",
    "相关性审核",
    "系统设置",
]

# 页面配置
st.set_page_config(
    page_title="AMZ搜索词分析系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 注入全局样式
inject_global_styles()


def init_session_state():
    """初始化Session State"""
    if "db" not in st.session_state:
        try:
            settings = Settings()
            st.session_state.db = Database(settings.database_path)
            st.session_state.db.init_schema()
            st.session_state.db.init_default_rules()
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}", exc_info=True)
            st.error("数据库初始化失败，请检查权限或磁盘空间。")
            st.stop()

    if "current_product_id" not in st.session_state:
        st.session_state.current_product_id = None

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    _ensure_current_user_context(st.session_state.db)


def _resolve_current_user_context(db: Database, current_user_id: int | None) -> dict:
    """根据 session 中的用户 ID 解析当前用户，缺失时回退到本地管理员。"""
    if current_user_id is not None:
        current_user = db.get_user(user_id=current_user_id)
        if current_user is not None:
            return current_user

    return db.get_or_create_local_owner()


def _ensure_current_user_context(db: Database) -> dict:
    """确保 session 中始终有明确的当前用户上下文。"""
    current_user = _resolve_current_user_context(
        db, st.session_state.get("current_user_id")
    )
    st.session_state.current_user_id = current_user["id"]
    st.session_state.current_user_email = current_user["email"]
    st.session_state.current_user_name = (
        current_user.get("display_name") or current_user["email"]
    )
    return current_user


def _get_product_selectbox_index(
    products: list[dict], current_product_id: int | None
) -> int | None:
    """根据当前产品ID返回侧边栏产品选择器应使用的索引。"""
    if not products:
        return None

    if current_product_id is not None:
        for index, product in enumerate(products):
            if product.get("id") == current_product_id:
                return index

    return 0


def _get_current_product_name(
    products: list[dict], current_product_id: int | None
) -> str | None:
    """根据当前产品ID返回当前产品名称，用于侧边栏上下文提示。"""
    if not products:
        return None

    if current_product_id is not None:
        for product in products:
            if product.get("id") == current_product_id:
                return product.get("name")

    return products[0].get("name")


def _build_sidebar_workspace_context_meta(
    workspace_name: str,
    current_user_name: str,
    member_count: int,
    current_role: str,
) -> dict[str, str | list[str]]:
    """构建侧边栏工作区协作文案。"""
    return {
        "title": "当前工作区协作",
        "description": "工作区已经绑定成员与角色，后续切到多人协作时会沿着这套上下文继续扩展，不用再从单机工具重搭一次。",
        "chips": [
            f"工作区：{workspace_name}",
            f"当前用户：{current_user_name}",
            f"角色：{current_role}",
            f"成员 {member_count} 人",
        ],
    }


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand-shell">
                <span class="sidebar-eyebrow">运营工作台</span>
                <h1>AMZ搜索词分析</h1>
                <p>聚焦结论、动作与复盘，让每天的广告优化更稳一点。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        # 初始化导航状态
        if st.session_state.get("nav_page") not in NAV_OPTIONS:
            st.session_state.nav_page = "首页"

        st.markdown(
            '<div class="sidebar-section-label">导航</div>',
            unsafe_allow_html=True,
        )

        st.radio(
            "导航",
            options=NAV_OPTIONS,
            key="nav_page",
            label_visibility="collapsed",
        )

        st.divider()

        # 产品选择
        db = st.session_state.db
        products = db.get_all_products()

        if products:
            current_product_name = _get_current_product_name(
                products, st.session_state.get("current_product_id")
            )
            product_options = {p["name"]: p["id"] for p in products}
            selected_product = st.selectbox(
                "当前产品",
                options=list(product_options.keys()),
                index=_get_product_selectbox_index(
                    products, st.session_state.get("current_product_id")
                ),
            )
            if selected_product:
                st.session_state.current_product_id = product_options[selected_product]

            if current_product_name:
                st.markdown(
                    f"""
                    <div class="sidebar-current-product">
                        <span>当前分析产品</span>
                        <strong>{current_product_name}</strong>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                current_user = _ensure_current_user_context(db)
                workspace_role = (
                    db.get_workspace_role(
                        st.session_state.current_product_id, current_user["id"]
                    )
                    or "viewer"
                )
                member_count = len(
                    db.get_workspace_members(
                        st.session_state.current_product_id,
                        include_system_members=True,
                    )
                )
                workspace_meta = _build_sidebar_workspace_context_meta(
                    workspace_name=current_product_name,
                    current_user_name=st.session_state.current_user_name,
                    member_count=member_count,
                    current_role=workspace_role,
                )
                chips_html = "".join(
                    f'<span style="display:inline-flex; padding:0.36rem 0.72rem; border-radius:999px; '
                    f'background:rgba(59,91,219,0.08); border:1px solid rgba(59,91,219,0.12); '
                    f'font-size:0.78rem; color:#334155; font-weight:600;">{escape(chip)}</span>'
                    for chip in workspace_meta["chips"]
                )
                st.markdown(
                    f"""
                    <div class="sidebar-current-product" style="margin-top:0.8rem;">
                        <span>{escape(workspace_meta["title"])}</span>
                        <strong>{escape(current_product_name)}</strong>
                        <p style="margin:0.7rem 0 0; color:#52607a; font-size:0.84rem; line-height:1.55;">
                            {escape(workspace_meta["description"])}
                        </p>
                        <div style="display:flex; flex-wrap:wrap; gap:0.45rem; margin-top:0.85rem;">
                            {chips_html}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("请先上传数据或创建产品")

        st.divider()

        # AI助手入口 - 放在侧边栏底部，更显眼
        render_sidebar_ai_assistant()

        return st.session_state.nav_page


def render_sidebar_ai_assistant():
    """在侧边栏渲染AI助手（参考Amazon Seller Assistant风格）"""
    # AI助手样式 - 参考Amazon Seller Assistant设计
    st.markdown(
        """
    <style>
    /* ===== AI助手Popover - Amazon风格 - 宽敞布局 ===== */
    div[data-testid="stPopoverBody"] {
        width: 420px !important;
        min-height: auto !important;
        max-height: 85vh !important;
        height: auto !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
        border: 1px solid #d5d9d9 !important;
        padding: 20px 24px !important;
        background: #ffffff !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }

    /* ===== 关键修复：覆盖Streamlit的.st-f3类的max-height限制 ===== */
    .st-f3,
    div.st-f3,
    [data-testid="stPopoverBody"].st-f3,
    div[data-testid="stPopoverBody"].st-f3 {
        max-height: 85vh !important;
        height: auto !important;
        overflow-y: auto !important;
    }

    /* 强制覆盖所有内部容器的高度限制 */
    div[data-testid="stPopoverBody"] > div,
    div[data-testid="stPopoverBody"] > div > div,
    div[data-testid="stPopoverBody"] > div > div > div,
    div[data-testid="stPopoverBody"] > div > div > div > div {
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }

    /* Streamlit内部元素覆盖 - 增加垂直间距 */
    div[data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {
        gap: 8px !important;
    }

    /* ===== Chat Input 样式 - Amazon风格 - 更宽敞 ===== */
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] {
        margin-top: 20px !important;
        padding: 0 !important;
        border-top: 1px solid #e7e7e7 !important;
        padding-top: 16px !important;
    }
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] textarea {
        font-size: 15px !important;
        min-height: 50px !important;
        border-radius: 25px !important;
        border: 1px solid #d5d9d9 !important;
        padding: 12px 18px !important;
        outline: none !important;
        box-shadow: none !important;
    }
    /* 去掉输入框聚焦时的蓝色边框 - 全面覆盖 */
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] textarea:focus,
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] textarea:focus-visible,
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] textarea:active {
        border: 1px solid #d5d9d9 !important;
        outline: none !important;
        outline-width: 0 !important;
        box-shadow: none !important;
    }
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] > div,
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] > div > div {
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] > div:focus-within,
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] > div > div:focus-within {
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    /* 去掉Streamlit默认的蓝色左侧指示线和所有伪元素 */
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"]::before,
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"]::after,
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] > div::before,
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] > div::after,
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] *::before,
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] *::after {
        display: none !important;
        background: transparent !important;
        border: none !important;
    }
    div[data-testid="stPopoverBody"] [data-testid="stChatInputTextArea"] {
        border-left: none !important;
        outline: none !important;
    }
    /* 覆盖Streamlit的.st-emotion-cache类focus样式 */
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] [class*="st-emotion-cache"]:focus,
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] [class*="st-emotion-cache"]:focus-within {
        border-color: #d5d9d9 !important;
        box-shadow: none !important;
        outline: none !important;
    }
    /* 发送按钮 - 蓝色背景+白色箭头 */
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] button {
        background: #2563EB !important;
        border-radius: 50% !important;
        width: 44px !important;
        height: 44px !important;
        border: none !important;
    }
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] button svg {
        fill: #ffffff !important;
        color: #ffffff !important;
    }
    div[data-testid="stPopoverBody"] [data-testid="stChatInput"] button path {
        fill: #ffffff !important;
    }

    /* ===== 标题区域 - Amazon风格 ===== */
    .ai-header {
        margin-bottom: 16px !important;
        padding-bottom: 12px !important;
        border-bottom: 1px solid #e7e7e7 !important;
    }
    .ai-header-title {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #0f1111 !important;
        margin: 0 0 2px 0 !important;
    }
    .ai-header-subtitle {
        font-size: 11px !important;
        color: #565959 !important;
        margin: 0 !important;
    }

    /* ===== 内容区域 ===== */
    .ai-content {
        padding: 0 !important;
    }

    /* ===== 欢迎消息 - Amazon风格 - 宽敞间距 ===== */
    .ai-welcome {
        font-size: 15px !important;
        color: #0f1111 !important;
        line-height: 1.7 !important;
        margin: 0 0 28px 0 !important;
    }

    /* ===== 快捷问题标签 ===== */
    .ai-prompt-text {
        font-size: 15px !important;
        font-weight: 700 !important;
        color: #0f1111 !important;
        margin: 0 0 20px 0 !important;
    }

    /* ===== 快捷按钮容器 ===== */
    .quick-link-btn {
        margin: 0 0 14px 0 !important;
        padding: 0 !important;
    }
    .quick-link-btn > div {
        margin: 0 !important;
        padding: 0 !important;
    }

    /* ===== 快捷按钮样式 - Amazon橙色边框风格 ===== */
    .quick-link-btn button,
    div[data-testid="stPopoverBody"] .stButton button {
        background: #ffffff !important;
        color: #007185 !important;
        border: 1px solid #ff9900 !important;
        border-radius: 8px !important;
        font-size: 14px !important;
        font-weight: 400 !important;
        padding: 10px 14px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        margin: 0 !important;
        width: 100% !important;
        min-height: 42px !important;
        height: auto !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
    }
    .quick-link-btn button:hover,
    div[data-testid="stPopoverBody"] .stButton button:hover {
        background: #232f3e !important;
        color: #ffffff !important;
        border-color: #ff9900 !important;
    }
    /* Hover时按钮内部文字强制白色 - 高对比度 */
    .quick-link-btn button:hover p,
    .quick-link-btn button:hover span,
    .quick-link-btn button:hover div,
    div[data-testid="stPopoverBody"] .stButton button:hover p,
    div[data-testid="stPopoverBody"] .stButton button:hover span,
    div[data-testid="stPopoverBody"] .stButton button:hover div {
        color: #ffffff !important;
    }
    .quick-link-btn button p {
        margin: 0 !important;
        text-align: left !important;
        color: #007185 !important;
    }

    /* ===== 消息容器 ===== */
    div[data-testid="stPopoverBody"] [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 8px !important;
        border: 1px solid #e7e7e7 !important;
        background: #f7f8f8 !important;
        margin: 8px 0 !important;
    }
    div[data-testid="stPopoverBody"] [data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 8px !important;
    }

    /* ===== 聊天消息 ===== */
    div[data-testid="stPopoverBody"] [data-testid="stChatMessage"] {
        padding: 6px 0 !important;
        margin: 0 !important;
        font-size: 14px !important;
        background: transparent !important;
    }

    /* ===== 底部提示 - Amazon风格 ===== */
    .ai-disclaimer {
        font-size: 11px !important;
        color: #565959 !important;
        text-align: center !important;
        padding: 8px 0 0 0 !important;
        margin: 0 !important;
    }

    /* ===== Info消息 ===== */
    div[data-testid="stPopoverBody"] [data-testid="stAlert"] {
        background: #f7f8f8 !important;
        border: 1px solid #e7e7e7 !important;
        border-radius: 8px !important;
        padding: 10px 12px !important;
        color: #0f1111 !important;
        font-size: 14px !important;
        margin: 0 !important;
    }

    /* 分割线 */
    div[data-testid="stPopoverBody"] hr {
        margin: 10px 0 !important;
        border: none !important;
        height: 1px !important;
        background: #e7e7e7 !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # 使用popover弹出对话框
    with st.popover("AI助手", width="stretch"):
        # 标题区域
        st.markdown(
            """
        <div class="ai-header">
            <div>
                <div class="ai-header-title">AI助手</div>
                <div class="ai-header-subtitle">Powered by AI</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 内容区域
        st.markdown('<div class="ai-content">', unsafe_allow_html=True)

        # 欢迎消息或对话历史
        if not st.session_state.chat_messages:
            st.markdown(
                """
            <p class="ai-welcome">你好，我是你的广告分析助手 - 帮助你通过数据洞察和专业建议优化广告投放。</p>
            <p class="ai-prompt-text">向我提问或选择以下主题开始：</p>
            """,
                unsafe_allow_html=True,
            )

            # 快捷问题 - 4个完整问题，Amazon风格
            quick_questions = [
                ("分析我的销售趋势和ACOS", "帮我分析当前的ACOS情况和销售趋势"),
                ("查看需要否定的关键词", "分析哪些词需要否定"),
                ("推荐手动投放的关键词", "有哪些词值得手动投放"),
                ("优化广告投放建议", "给我一些广告优化建议"),
            ]

            for i, (label, question) in enumerate(quick_questions):
                st.markdown('<div class="quick-link-btn">', unsafe_allow_html=True)
                if st.button(label, key=f"ai_quick_{i}", width="stretch"):
                    _process_ai_message(question)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            # 消息历史 - 可滚动区域
            messages_container = st.container(height=250)
            with messages_container:
                for msg in st.session_state.chat_messages[-8:]:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])

        st.markdown("</div>", unsafe_allow_html=True)

        # 使用chat_input - 自带发送按钮
        user_input = st.chat_input("Message AI助手...", key="ai_chat_input")
        if user_input:
            _process_ai_message(user_input)

        # 底部提示
        st.markdown(
            '<p class="ai-disclaimer">AI助手仍在学习中，请仔细核实建议。</p>',
            unsafe_allow_html=True,
        )


def render_floating_ai_assistant():
    """渲染浮动AI助手按钮和弹出对话框"""
    # 浮动按钮样式 - 现代SaaS风格深蓝配色
    st.markdown(
        """
    <style>
    /* 浮动按钮容器 */
    div[data-testid="stPopover"] {
        position: fixed !important;
        bottom: 24px !important;
        right: 24px !important;
        z-index: 9999 !important;
    }
    /* 浮动按钮本体 */
    div[data-testid="stPopover"] > button {
        position: relative !important;
        width: 56px !important;
        height: 56px !important;
        border-radius: 12px !important;
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        font-size: 20px !important;
        padding: 0 !important;
        min-height: unset !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stPopover"] > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4) !important;
    }
    /* 弹出框样式 */
    div[data-testid="stPopoverBody"] {
        width: 400px !important;
        max-height: 520px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12) !important;
        border: 1px solid #E2E8F0 !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # 使用popover作为弹出对话框
    with st.popover("AI", width="content"):
        st.markdown("### AI助手")
        st.caption("您的亚马逊广告优化专家")

        # 快捷问题按钮
        st.markdown("**快捷问题:**")
        col1, col2 = st.columns(2)

        quick_questions = [
            ("分析ACOS", "帮我分析当前的ACOS情况"),
            ("优化建议", "给我一些广告优化建议"),
            ("否词分析", "分析哪些词需要否定"),
            ("投放建议", "有哪些词值得手动投放"),
        ]

        for i, (label, question) in enumerate(quick_questions):
            col = col1 if i % 2 == 0 else col2
            with col:
                if st.button(label, key=f"ai_quick_{i}", width="stretch"):
                    _process_ai_message(question)

        st.divider()

        # 消息历史
        messages_container = st.container(height=280)
        with messages_container:
            if not st.session_state.chat_messages:
                st.info(
                    "你好！我是AI助手，可以帮你分析广告数据。试试上面的快捷问题，或直接输入你的问题。"
                )
            else:
                for msg in st.session_state.chat_messages[-8:]:
                    with st.chat_message(msg["role"]):
                        content = msg["content"]
                        if len(content) > 400:
                            content = content[:400] + "..."
                        st.write(content)

        # 输入框
        user_input = st.chat_input("输入你的问题...", key="floating_ai_input")
        if user_input:
            _process_ai_message(user_input)

        # 清除对话按钮
        if st.session_state.chat_messages:
            if st.button("清除对话", width="stretch", type="secondary"):
                st.session_state.chat_messages = []
                st.rerun()


def _process_ai_message(message: str):
    """处理AI消息"""
    from src.ai.chat import ChatAssistant

    # 限制聊天历史记录大小，防止内存无限增长
    MAX_CHAT_HISTORY = 50
    if len(st.session_state.chat_messages) > MAX_CHAT_HISTORY:
        st.session_state.chat_messages = st.session_state.chat_messages[
            -MAX_CHAT_HISTORY:
        ]

    # 添加用户消息
    st.session_state.chat_messages.append(
        {
            "role": "user",
            "content": message,
        }
    )

    # 获取AI响应
    try:
        db = st.session_state.get("db")
        product_id = st.session_state.get("current_product_id")

        if not db:
            st.session_state.chat_messages.append(
                {
                    "role": "assistant",
                    "content": "数据库未初始化，请先上传数据。",
                }
            )
            st.rerun()
            return

        # 持久化ChatAssistant实例，保持多轮对话上下文
        assistant_key = f"chat_assistant_{product_id}"
        if assistant_key not in st.session_state:
            st.session_state[assistant_key] = ChatAssistant(
                db=db,
                product_id=product_id,
            )
        assistant = st.session_state[assistant_key]
        response = assistant.process_message(message)

        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": response.message,
            }
        )
    except Exception as e:
        logger.error(f"AI响应错误: {e}", exc_info=True)
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": "抱歉，处理请求时出错，请稍后重试。",
            }
        )

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
    elif current_page == "ASIN分析":
        from src.ui.pages.asin_analysis import render_asin_analysis

        render_asin_analysis()
    elif current_page == "操作清单":
        from src.ui.pages.actions import render_actions

        render_actions()
    elif current_page == "相关性审核":
        from src.ui.pages.review import render_review

        render_review()
    elif current_page == "系统设置":
        from src.ui.pages.settings import render_settings

        render_settings()

    # AI助手现在已集成到侧边栏中


if __name__ == "__main__":
    main()
