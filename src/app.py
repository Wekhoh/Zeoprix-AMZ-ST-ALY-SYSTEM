"""
AMZ搜索词分析系统 - Streamlit主应用
"""

import json
import os
import sys
from html import escape
from urllib import error, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from src.config.logger import get_logger
from src.config.settings import Settings
from src.data.db import Database
from src.ui.styles import inject_ai_assistant_styles, inject_global_styles

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

AI_CHAT_MAX_HISTORY = 50
AI_CHAT_PENDING_TEXT = "AI 正在思考..."
AI_CHAT_QUICK_PROMPTS = [
    ("分析我的销售趋势和ACOS", "帮我分析当前的ACOS情况和销售趋势"),
    ("查看需要否定的关键词", "分析哪些词需要否定"),
    ("推荐手动投放的关键词", "有哪些词值得手动投放"),
    ("优化广告投放建议", "给我一些广告优化建议"),
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
    if "ai_chat_is_generating" not in st.session_state:
        st.session_state.ai_chat_is_generating = False
    if "ai_chat_pending_prompt" not in st.session_state:
        st.session_state.ai_chat_pending_prompt = None
    if "ai_chat_last_prompt" not in st.session_state:
        st.session_state.ai_chat_last_prompt = None

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


def _format_workspace_member_option(member: dict) -> str:
    """格式化工作区成员选择器标签。"""
    display_name = (member.get("display_name") or "").strip()
    email = member["email"]
    role = member["role"]
    if display_name and display_name != email:
        return f"{display_name} · {email}（{role}）"
    return f"{email}（{role}）"


def _build_workspace_user_selector_meta(
    members: list[dict],
    current_user_id: int | None,
) -> dict[str, object]:
    """构建侧边栏当前身份切换器元数据。"""
    if not members:
        return {
            "title": "当前身份",
            "description": "当前工作区还没有可切换的成员身份。",
            "options": [],
            "selected_label": None,
        }

    current_member = next(
        (member for member in members if member["user_id"] == current_user_id),
        None,
    )
    if current_member is None:
        current_member = next(
            (member for member in members if member["role"] == "admin"),
            members[0],
        )

    options = [
        {
            "label": _format_workspace_member_option(member),
            "user_id": member["user_id"],
            "email": member["email"],
            "display_name": member.get("display_name") or member["email"],
            "role": member["role"],
        }
        for member in members
    ]
    selected_label = next(
        option["label"]
        for option in options
        if option["user_id"] == current_member["user_id"]
    )
    return {
        "title": "当前身份",
        "description": "切换当前身份，模拟不同成员在同一个工作区里看到的页面和权限。",
        "options": options,
        "selected_label": selected_label,
    }


def _set_current_user_context(member_option: dict[str, object]) -> None:
    """将选中的成员写入当前 session 用户上下文。"""
    st.session_state.current_user_id = member_option["user_id"]
    st.session_state.current_user_email = member_option["email"]
    st.session_state.current_user_name = member_option["display_name"]
    st.session_state.current_user_role = member_option.get("role") or "viewer"


def _get_backend_base_url() -> str | None:
    """获取共享后端地址。"""
    base_url = os.getenv("AMZ_BACKEND_BASE_URL", "").strip().rstrip("/")
    return base_url or None


def _build_backend_auth_shell_meta(base_url: str) -> dict[str, object]:
    """构建后端登录壳文案。"""
    return {
        "title": "团队登录",
        "description": "当前应用已切到共享后端模式。同事通过同一个公网地址访问时，会先在这里登录，再进入同一个工作区。",
        "base_url": base_url,
        "fields": ["邮箱", "密码"],
    }


def _clear_backend_auth_session() -> None:
    """清除后端登录态。"""
    for key in (
        "backend_access_token",
        "backend_auth_user",
        "backend_auth_base_url",
        "backend_workspace",
        "backend_workspace_members",
        "current_user_id",
        "current_user_email",
        "current_user_name",
        "current_user_role",
    ):
        st.session_state.pop(key, None)


def _backend_login_request(base_url: str, email: str, password: str) -> dict:
    """调用共享后端登录接口。"""
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = request.Request(
        f"{base_url}/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = "登录失败，请检查邮箱或密码。"
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail = payload.get("detail") or detail
        except Exception:
            pass
        raise RuntimeError(detail) from exc
    except error.URLError as exc:
        raise RuntimeError("无法连接共享后端，请检查部署地址或网络。") from exc


def _backend_get_current_user(base_url: str, access_token: str) -> dict:
    """调用共享后端 auth/me，确保当前 token 与角色仍有效。"""
    req = request.Request(
        f"{base_url}/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = "当前登录已失效，请重新登录。"
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            if exc.code >= 500:
                detail = payload.get("detail") or "共享后端暂时不可用，请稍后重试。"
            elif exc.code not in (401, 403):
                detail = payload.get("detail") or detail
        except Exception:
            if exc.code >= 500:
                detail = "共享后端暂时不可用，请稍后重试。"
        raise RuntimeError(detail) from exc
    except error.URLError as exc:
        raise RuntimeError("无法连接共享后端，请检查部署地址或网络。") from exc


def _backend_get_default_workspace(base_url: str, access_token: str) -> dict:
    """读取共享后端默认工作区元信息。"""
    req = request.Request(
        f"{base_url}/workspaces/default",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = "无法读取共享工作区信息，请稍后重试。"
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            if exc.code in (401, 403):
                detail = payload.get("detail") or "当前登录已失效，请重新登录。"
            elif exc.code >= 500:
                detail = payload.get("detail") or "共享后端暂时不可用，请稍后重试。"
            else:
                detail = payload.get("detail") or detail
        except Exception:
            if exc.code in (401, 403):
                detail = "当前登录已失效，请重新登录。"
            elif exc.code >= 500:
                detail = "共享后端暂时不可用，请稍后重试。"
        raise RuntimeError(detail) from exc
    except error.URLError as exc:
        raise RuntimeError("无法连接共享后端，请检查部署地址或网络。") from exc


def _backend_get_default_workspace_members(base_url: str, access_token: str) -> list[dict]:
    """读取共享后端默认工作区成员列表。"""
    req = request.Request(
        f"{base_url}/workspaces/default/members",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = "无法读取共享工作区成员，请稍后重试。"
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            if exc.code in (401, 403):
                detail = payload.get("detail") or "当前登录已失效，请重新登录。"
            elif exc.code >= 500:
                detail = payload.get("detail") or "共享后端暂时不可用，请稍后重试。"
            else:
                detail = payload.get("detail") or detail
        except Exception:
            if exc.code in (401, 403):
                detail = "当前登录已失效，请重新登录。"
            elif exc.code >= 500:
                detail = "共享后端暂时不可用，请稍后重试。"
        raise RuntimeError(detail) from exc
    except error.URLError as exc:
        raise RuntimeError("无法连接共享后端，请检查部署地址或网络。") from exc


def _refresh_backend_workspace_context(base_url: str, access_token: str) -> dict[str, object]:
    """刷新共享模式下的工作区与成员上下文。"""
    workspace = _backend_get_default_workspace(base_url, access_token)
    members = _backend_get_default_workspace_members(base_url, access_token)
    st.session_state.backend_workspace = workspace
    st.session_state.backend_workspace_members = members
    return {"workspace": workspace, "members": members}


def _normalize_backend_workspace_members(members: list[dict]) -> list[dict]:
    """将后端成员结构转换为侧边栏可复用的统一格式。"""
    return [
        {
            "user_id": member["id"],
            "email": member["email"],
            "display_name": member.get("name") or member["email"],
            "role": member.get("role") or "viewer",
        }
        for member in members
    ]


def _build_sidebar_collaboration_state(
    db: Database,
    current_product_id: int,
    current_product_name: str,
) -> dict[str, object]:
    """统一构建侧边栏协作上下文，优先使用共享后端工作区数据。"""
    backend_user = st.session_state.get("backend_auth_user")
    backend_workspace = st.session_state.get("backend_workspace")
    backend_members = st.session_state.get("backend_workspace_members") or []
    if backend_user and backend_workspace:
        normalized_members = _normalize_backend_workspace_members(backend_members)
        selected_member = {
            "user_id": backend_user["id"],
            "email": backend_user["email"],
            "display_name": backend_user.get("name") or backend_user["email"],
            "role": backend_user.get("role") or backend_workspace.get("role") or "viewer",
        }
        return {
            "workspace_name": backend_workspace.get("name") or current_product_name,
            "member_count": int(backend_workspace.get("member_count") or len(normalized_members)),
            "selected_member": selected_member,
            "workspace_members": normalized_members,
            "show_identity_switcher": False,
            "identity_hint": "共享模式下当前身份由团队登录决定；如需切换账号，请先退出当前账号。",
        }

    current_user = _ensure_current_user_context(db)
    workspace_members = db.get_workspace_members(
        current_product_id,
        include_system_members=True,
    )
    workspace_role = (
        db.get_workspace_role(current_product_id, current_user["id"])
        or st.session_state.get("current_user_role")
        or "viewer"
    )
    selected_member = {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "display_name": current_user.get("display_name") or current_user["email"],
        "role": workspace_role,
    }
    st.session_state.current_user_role = workspace_role
    selector_meta = _build_workspace_user_selector_meta(
        workspace_members,
        current_user_id=current_user["id"],
    )
    selector_options = {
        option["label"]: option for option in selector_meta["options"]
    }
    selector_key = f"workspace-user-selector-{current_product_id}"
    if selector_meta["selected_label"] is not None and (
        st.session_state.get(selector_key) not in selector_options
    ):
        st.session_state[selector_key] = selector_meta["selected_label"]

    return {
        "workspace_name": current_product_name,
        "member_count": len(workspace_members),
        "selected_member": selected_member,
        "workspace_members": workspace_members,
        "show_identity_switcher": True,
        "identity_hint": selector_meta["description"],
        "selector_meta": selector_meta,
        "selector_options": selector_options,
        "selector_key": selector_key,
    }


def _sync_backend_user_to_local_context(db: Database) -> dict | None:
    """将后端登录用户同步到本地工作区成员上下文。"""
    backend_user = st.session_state.get("backend_auth_user")
    if not backend_user:
        return None

    normalized_email = str(backend_user["email"]).strip().lower()
    display_name = str(backend_user.get("name") or normalized_email).strip()
    normalized_role = str(backend_user.get("role") or "viewer").strip().lower()

    products = db.get_all_products()
    for product in products:
        db.upsert_workspace_member_by_email(
            product_id=product["id"],
            email=normalized_email,
            role=normalized_role,
            display_name=display_name,
        )

    local_user = db.get_user(email=normalized_email)
    if local_user is None:
        user_id = db.create_user(email=normalized_email, display_name=display_name)
        local_user = db.get_user(user_id=user_id)

    st.session_state.current_user_id = local_user["id"]
    st.session_state.current_user_email = normalized_email
    st.session_state.current_user_name = display_name
    st.session_state.current_user_role = normalized_role
    return local_user


def _render_backend_auth_gate(db: Database) -> None:
    """共享后端模式下，先完成登录再进入工作区。"""
    base_url = _get_backend_base_url()
    if not base_url:
        return

    st.session_state.backend_auth_base_url = base_url
    auth_notice = None
    access_token = st.session_state.get("backend_access_token")
    if access_token:
        try:
            st.session_state.backend_auth_user = _backend_get_current_user(base_url, access_token)
            _refresh_backend_workspace_context(base_url, access_token)
        except RuntimeError as exc:
            _clear_backend_auth_session()
            auth_notice = str(exc)
        else:
            _sync_backend_user_to_local_context(db)
            return

    meta = _build_backend_auth_shell_meta(base_url)
    st.title(meta["title"])
    st.caption(meta["description"])
    st.info(f"共享后端地址：{base_url}")
    if auth_notice:
        st.warning(auth_notice)
    with st.form("backend-login-form"):
        st.text_input("邮箱", key="backend_login_email")
        st.text_input("密码", type="password", key="backend_login_password")
        submitted = st.form_submit_button("登录并进入工作区", width="stretch")

    if submitted:
        try:
            payload = _backend_login_request(
                base_url,
                st.session_state.get("backend_login_email", ""),
                st.session_state.get("backend_login_password", ""),
            )
        except RuntimeError as exc:
            st.error(str(exc))
            st.stop()

        st.session_state.backend_access_token = payload["access_token"]
        st.session_state.backend_auth_user = payload["user"]
        st.session_state.backend_login_password = ""
        try:
            _refresh_backend_workspace_context(base_url, payload["access_token"])
        except RuntimeError as exc:
            _clear_backend_auth_session()
            st.error(str(exc))
            st.stop()
        _sync_backend_user_to_local_context(db)
        st.success("登录成功，正在进入共享工作区…")
        st.rerun()

    st.stop()


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

        if st.session_state.get("backend_auth_user"):
            st.caption("当前运行在共享后端登录模式，可直接给同事同一个访问地址。")

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
            if st.session_state.get("current_product_id") is None:
                st.session_state.current_product_id = products[0]["id"]
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

                collaboration_state = _build_sidebar_collaboration_state(
                    db,
                    st.session_state.current_product_id,
                    current_product_name,
                )
                selected_member = collaboration_state["selected_member"]
                workspace_role = selected_member["role"]
                member_count = collaboration_state["member_count"]
                if collaboration_state["show_identity_switcher"]:
                    selector_meta = collaboration_state["selector_meta"]
                    selector_options = collaboration_state["selector_options"]
                    selector_key = collaboration_state["selector_key"]
                    if selector_meta["options"]:
                        st.caption(collaboration_state["identity_hint"])
                        selected_label = st.selectbox(
                            selector_meta["title"],
                            options=list(selector_options.keys()),
                            key=selector_key,
                        )
                        selected_member = selector_options[selected_label]
                        if selected_member["user_id"] != st.session_state.get(
                            "current_user_id"
                        ):
                            _set_current_user_context(selected_member)
                            st.rerun()
                else:
                    st.caption(collaboration_state["identity_hint"])

                workspace_meta = _build_sidebar_workspace_context_meta(
                    workspace_name=collaboration_state["workspace_name"],
                    current_user_name=selected_member["display_name"],
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

                if st.session_state.get("backend_auth_user"):
                    if st.button("退出当前账号", key="sidebar-backend-logout", width="stretch"):
                        _clear_backend_auth_session()
                        st.rerun()
        else:
            st.info("请先上传数据或创建产品")

        st.divider()

        # AI助手入口 - 放在侧边栏底部，更显眼
        render_sidebar_ai_assistant()

        return st.session_state.nav_page


def _normalize_ai_chat_message(message: dict) -> dict:
    """标准化 AI 对话消息结构，统一状态与重试字段。"""
    return {
        "role": message.get("role", "assistant"),
        "content": (message.get("content") or "").strip(),
        "status": message.get("status", "default"),
        "can_retry": bool(message.get("can_retry", False)),
        "retry_prompt": message.get("retry_prompt"),
    }


def _append_ai_chat_message(
    role: str,
    content: str,
    *,
    status: str = "default",
    can_retry: bool = False,
    retry_prompt: str | None = None,
):
    """向会话消息列表中追加一条标准化消息，并控制历史长度。"""
    normalized = _normalize_ai_chat_message(
        {
            "role": role,
            "content": content,
            "status": status,
            "can_retry": can_retry,
            "retry_prompt": retry_prompt,
        }
    )

    if not normalized["content"]:
        return

    history = [
        _normalize_ai_chat_message(item)
        for item in st.session_state.get("chat_messages", [])
    ]
    history.append(normalized)
    if len(history) > AI_CHAT_MAX_HISTORY:
        history = history[-AI_CHAT_MAX_HISTORY:]
    st.session_state.chat_messages = history


def _build_ai_error_message(exc: Exception) -> dict[str, str | bool]:
    """将 AI 异常映射为统一的用户可见消息。"""
    error_text = str(exc or "").strip()
    lowered = error_text.lower()

    if "gemini_api_key" in lowered or "api key" in lowered or "api_key" in lowered:
        return {
            "content": "当前未配置 AI Key，暂时无法使用 AI 助手。",
            "status": "error",
            "can_retry": False,
        }

    if isinstance(exc, TimeoutError) or "timeout" in lowered or "timed out" in lowered:
        return {
            "content": "AI 请求超时，请稍后重试。",
            "status": "warning",
            "can_retry": True,
        }

    if "rate limit" in lowered or "429" in lowered or "too many requests" in lowered:
        return {
            "content": "AI 当前请求较多，请稍后重试。",
            "status": "warning",
            "can_retry": True,
        }

    return {
        "content": "抱歉，处理请求时出错，请稍后重试。",
        "status": "error",
        "can_retry": True,
    }


def _build_ai_chat_view_state(messages: list[dict], is_generating: bool) -> dict:
    """构建统一聊天视图状态，供侧边栏与浮动助手共享。"""
    normalized_messages = [_normalize_ai_chat_message(message) for message in messages]
    retry_prompt = None
    for message in reversed(normalized_messages):
        if message["can_retry"] and message.get("retry_prompt"):
            retry_prompt = message["retry_prompt"]
            break

    return {
        "messages": normalized_messages,
        "show_empty_state": not normalized_messages,
        "input_disabled": is_generating,
        "retry_prompt": retry_prompt,
        "show_retry_button": bool(retry_prompt) and not is_generating,
        "pending_message": {
            "role": "assistant",
            "content": AI_CHAT_PENDING_TEXT,
            "status": "pending",
            "can_retry": False,
            "retry_prompt": None,
        }
        if is_generating
        else None,
    }


def _queue_ai_message(message: str) -> bool:
    """将用户输入排入待处理队列，并立即显示在聊天记录中。"""
    prompt = (message or "").strip()
    if not prompt:
        return False

    _append_ai_chat_message(
        "user",
        prompt,
        status="default",
        can_retry=False,
        retry_prompt=None,
    )
    st.session_state.ai_chat_pending_prompt = prompt
    st.session_state.ai_chat_last_prompt = prompt
    st.session_state.ai_chat_is_generating = True
    return True


def _clear_ai_chat_history():
    """清理聊天历史与待处理状态。"""
    st.session_state.chat_messages = []
    st.session_state.ai_chat_is_generating = False
    st.session_state.ai_chat_pending_prompt = None
    st.session_state.ai_chat_last_prompt = None

    product_id = st.session_state.get("current_product_id")
    if product_id is not None:
        assistant_key = f"chat_assistant_{product_id}"
        st.session_state.pop(assistant_key, None)


def _drain_pending_ai_message() -> bool:
    """消费一条待处理消息，并把结果写回聊天历史。"""
    prompt = st.session_state.get("ai_chat_pending_prompt")
    if not prompt or not st.session_state.get("ai_chat_is_generating"):
        return False

    from src.ai.chat import ChatAssistant

    try:
        db = st.session_state.get("db")
        product_id = st.session_state.get("current_product_id")
        if not db:
            _append_ai_chat_message(
                "assistant",
                "数据库未初始化，请先上传数据。",
                status="error",
                can_retry=False,
                retry_prompt=None,
            )
            return True

        assistant_key = f"chat_assistant_{product_id}"
        if assistant_key not in st.session_state:
            st.session_state[assistant_key] = ChatAssistant(
                db=db,
                product_id=product_id,
            )
        assistant = st.session_state[assistant_key]
        response = assistant.process_message(prompt)
        _append_ai_chat_message(
            "assistant",
            response.message,
            status="default",
            can_retry=False,
            retry_prompt=None,
        )
    except Exception as exc:
        logger.error(f"AI响应错误: {exc}", exc_info=True)
        error_meta = _build_ai_error_message(exc)
        _append_ai_chat_message(
            "assistant",
            str(error_meta["content"]),
            status=str(error_meta["status"]),
            can_retry=bool(error_meta["can_retry"]),
            retry_prompt=prompt if error_meta["can_retry"] else None,
        )
    finally:
        st.session_state.ai_chat_is_generating = False
        st.session_state.ai_chat_pending_prompt = None

    return True


def _render_ai_chat_message(message: dict):
    """渲染单条聊天消息。"""
    with st.chat_message(message["role"]):
        status = message.get("status", "default")
        content = message.get("content", "")
        if status == "error":
            st.error(content)
        elif status == "warning":
            st.warning(content)
        elif status == "pending":
            st.markdown(
                f'<div class="ai-chat-thinking">{escape(content)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.write(content)

        if message.get("can_retry") and message.get("retry_prompt"):
            st.caption("可重试")


def _render_ai_quick_prompts(*, key_prefix: str, disabled: bool):
    """渲染快捷提问按钮。"""
    st.markdown('<div class="ai-chat-quick-grid">', unsafe_allow_html=True)
    for idx, (label, prompt) in enumerate(AI_CHAT_QUICK_PROMPTS):
        if st.button(
            label,
            key=f"{key_prefix}-quick-{idx}",
            use_container_width=True,
            disabled=disabled,
        ):
            if _queue_ai_message(prompt):
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_ai_chat_shell(
    *,
    surface_key: str,
    title: str,
    subtitle: str,
    input_key: str,
    input_placeholder: str,
):
    """统一渲染成熟聊天窗体验。"""
    view_state = _build_ai_chat_view_state(
        st.session_state.get("chat_messages", []),
        bool(st.session_state.get("ai_chat_is_generating")),
    )

    st.markdown(
        f"""
        <div class="ai-chat-shell">
            <div class="ai-chat-header">
                <div class="ai-chat-header-title">{escape(title)}</div>
                <div class="ai-chat-header-subtitle">{escape(subtitle)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if view_state["show_empty_state"]:
        st.markdown(
            """
            <div class="ai-chat-empty-state">
                <div class="ai-chat-empty-title">你好，我是你的 AI 广告分析助手</div>
                <div class="ai-chat-empty-subtitle">我可以结合当前产品、搜索词与分析结果，帮你总结问题、识别浪费，并给出下一步建议。</div>
                <div class="ai-chat-empty-hint">你可以先点一个快捷问题开始，也可以直接在下方输入。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_ai_quick_prompts(key_prefix=surface_key, disabled=view_state["input_disabled"])
    else:
        with st.container(height=320, border=True):
            for message in view_state["messages"]:
                _render_ai_chat_message(message)
            if view_state["pending_message"]:
                _render_ai_chat_message(view_state["pending_message"])

    st.markdown('<div class="ai-chat-actions">', unsafe_allow_html=True)
    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button(
            "重试上一条",
            key=f"{surface_key}-retry",
            use_container_width=True,
            disabled=not view_state["show_retry_button"],
        ):
            if _queue_ai_message(view_state["retry_prompt"] or ""):
                st.rerun()
    with action_col2:
        if st.button(
            "清空对话",
            key=f"{surface_key}-clear",
            use_container_width=True,
            disabled=view_state["input_disabled"] and not view_state["messages"],
        ):
            _clear_ai_chat_history()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    user_input = st.chat_input(
        input_placeholder,
        key=input_key,
        disabled=view_state["input_disabled"],
    )
    if user_input and _queue_ai_message(user_input):
        st.rerun()

    if st.session_state.get("ai_chat_is_generating"):
        with st.spinner(AI_CHAT_PENDING_TEXT):
            processed = _drain_pending_ai_message()
        if processed:
            st.rerun()

    st.markdown(
        '<p class="ai-chat-disclaimer">AI 助手仍在学习中，请仔细核实建议。</p>',
        unsafe_allow_html=True,
    )


def render_sidebar_ai_assistant():
    """在侧边栏渲染成熟聊天体验的 AI 助手。"""
    inject_ai_assistant_styles()
    with st.popover("AI助手", width="stretch"):
        _render_ai_chat_shell(
            surface_key="sidebar-ai",
            title="AI 助手",
            subtitle="结合当前产品、搜索词与分析结果给出建议。",
            input_key="ai_chat_input",
            input_placeholder="输入问题，或让 AI 帮你总结当前产品…",
        )


def render_floating_ai_assistant():
    """渲染复用同一聊天内核的浮动 AI 助手。"""
    inject_ai_assistant_styles()
    with st.popover("AI", width="content"):
        _render_ai_chat_shell(
            surface_key="floating-ai",
            title="AI助手",
            subtitle="你的亚马逊广告分析助手。",
            input_key="floating_ai_input",
            input_placeholder="输入你的问题…",
        )


def _process_ai_message(message: str):
    """兼容旧入口：排队后触发统一聊天处理流程。"""
    if _queue_ai_message(message):
        st.rerun()


def main():
    """主函数"""
    # 初始化
    init_session_state()
    _render_backend_auth_gate(st.session_state.db)

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

