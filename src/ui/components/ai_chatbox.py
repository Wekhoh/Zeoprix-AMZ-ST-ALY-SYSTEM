"""
AI助手浮动对话框组件
实现类似Amazon Seller Assistant的弹出式对话框
"""

import streamlit as st

from src.config.logger import get_logger

logger = get_logger(__name__)

# 浮动按钮和对话框的CSS样式
CHATBOX_CSS = """
<style>
/* 浮动AI按钮 */
.ai-fab-button {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    color: white;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    transition: transform 0.2s, box-shadow 0.2s;
}

.ai-fab-button:hover {
    transform: scale(1.1);
    box-shadow: 0 6px 16px rgba(102, 126, 234, 0.6);
}

/* 浮动对话框容器 */
.ai-chatbox-container {
    position: fixed;
    bottom: 90px;
    right: 24px;
    width: 380px;
    max-height: 520px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
    z-index: 9998;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid #e5e7eb;
}

/* 对话框头部 */
.ai-chatbox-header {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    color: white;
    padding: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.ai-chatbox-title {
    font-weight: 600;
    font-size: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.ai-chatbox-close {
    background: rgba(255, 255, 255, 0.2);
    border: none;
    color: white;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
}

.ai-chatbox-close:hover {
    background: rgba(255, 255, 255, 0.3);
}

/* 消息区域 */
.ai-chatbox-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    max-height: 350px;
}

.ai-message {
    margin-bottom: 12px;
    display: flex;
    gap: 8px;
}

.ai-message-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
}

.ai-message-avatar.assistant {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    color: white;
}

.ai-message-avatar.user {
    background: #f3f4f6;
    color: #374151;
}

.ai-message-content {
    background: #f9fafb;
    padding: 10px 14px;
    border-radius: 12px;
    max-width: 280px;
    font-size: 14px;
    line-height: 1.5;
}

.ai-message.user .ai-message-content {
    background: #2563EB;
    color: white;
    margin-left: auto;
}

/* 输入区域 */
.ai-chatbox-input {
    padding: 12px 16px;
    border-top: 1px solid #e5e7eb;
    display: flex;
    gap: 8px;
}

.ai-chatbox-input input {
    flex: 1;
    padding: 10px 14px;
    border: 1px solid #e5e7eb;
    border-radius: 20px;
    outline: none;
    font-size: 14px;
}

.ai-chatbox-input input:focus {
    border-color: #2563EB;
}

.ai-chatbox-input button {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    color: white;
    border: none;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* 快捷操作按钮 */
.ai-quick-actions {
    padding: 8px 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.ai-quick-btn {
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    padding: 6px 12px;
    border-radius: 16px;
    font-size: 12px;
    color: #374151;
    cursor: pointer;
    transition: all 0.2s;
}

.ai-quick-btn:hover {
    background: #2563EB;
    color: white;
    border-color: #2563EB;
}

/* 隐藏streamlit默认样式 */
.ai-chatbox-streamlit {
    position: fixed;
    bottom: 90px;
    right: 24px;
    width: 380px;
    z-index: 9998;
}
</style>
"""


def init_chatbox_state():
    """初始化对话框状态"""
    if "chatbox_open" not in st.session_state:
        st.session_state.chatbox_open = False
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


def toggle_chatbox():
    """切换对话框显示状态"""
    st.session_state.chatbox_open = not st.session_state.chatbox_open


def render_floating_ai_button():
    """渲染浮动AI按钮和对话框"""
    init_chatbox_state()

    # 注入CSS
    st.markdown(CHATBOX_CSS, unsafe_allow_html=True)

    # 使用Streamlit的popover实现弹出对话框（Streamlit 1.33+）
    # 创建一个固定位置的容器
    with st.container():
        # 右下角固定区域
        cols = st.columns([10, 1])
        with cols[1]:
            with st.popover("AI", width="content"):
                render_chatbox_content()


def render_chatbox_content():
    """渲染对话框内容"""
    st.markdown("### AI助手")
    st.caption("您的亚马逊广告优化专家")

    # 快捷操作
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
            if st.button(label, key=f"quick_{i}", width="stretch"):
                _send_message(question)

    st.divider()

    # 消息历史
    messages_container = st.container(height=250)
    with messages_container:
        for msg in st.session_state.chat_messages[-10:]:
            with st.chat_message(msg["role"]):
                st.write(
                    msg["content"][:500] + "..."
                    if len(msg["content"]) > 500
                    else msg["content"]
                )

    # 输入框
    user_input = st.chat_input("问点什么...", key="chatbox_input")
    if user_input:
        _send_message(user_input)


def _send_message(message: str):
    """发送消息并获取AI响应"""
    # 添加用户消息
    st.session_state.chat_messages.append(
        {
            "role": "user",
            "content": message,
        }
    )

    # 获取AI响应
    try:
        from src.ai.chat import ChatAssistant

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

        assistant = ChatAssistant(
            db=db,
            product_id=product_id,
        )
        response = assistant.process_message(message)

        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": response.message,
            }
        )
    except Exception as e:
        logger.error(f"AI响应错误: {e}")
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": f"抱歉，处理请求时出错: {str(e)}",
            }
        )

    st.rerun()


def render_sidebar_ai_toggle():
    """在侧边栏渲染AI助手开关（简化版）"""
    init_chatbox_state()

    with st.expander("AI助手", expanded=st.session_state.chatbox_open):
        render_chatbox_content()
