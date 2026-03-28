"""
系统设置页面
管理规则配置、产品配置和系统参数
"""

from html import escape

import pandas as pd
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


def _build_product_settings_summary(product: dict | None) -> dict[str, str | list[str]]:
    """构建产品配置页的摘要信息。"""
    product = product or {}
    config = product.get("config", {}) or {}
    core_keywords = config.get("core_keywords", [])
    competitor_asins = config.get("competitor_asins", [])
    asin = (product.get("asin") or "").strip()

    return {
        "title": "产品配置",
        "description": "把产品基本信息、核心关键词和竞品 ASIN 放在一页里维护，避免系统不知道你卖什么、也不知道你在和谁竞争。",
        "chips": [
            f"产品名：{product.get('name') or '未命名产品'}",
            f"ASIN {'已配置' if asin else '待补充'}",
            f"核心词 {len(core_keywords)}",
            f"竞品 ASIN {len(competitor_asins)}",
        ],
    }



def _build_api_settings_summary(
    is_configured: bool,
    selected_model_label: str,
) -> dict[str, str | list[str]]:
    """构建 API 设置页的摘要信息。"""
    return {
        "title": "API设置",
        "description": "这里只处理模型连接和密钥状态。先确认可用性，再切模型，最后再去分析页验证结果，不要把这里当成日常高频操作页。",
        "chips": [
            f"Gemini API {'已连接' if is_configured else '未连接'}",
            f"当前模型：{selected_model_label}",
            ".env 文件托管密钥",
        ],
    }


def _build_workspace_member_summary(
    product_name: str,
    current_user_name: str,
    current_role: str,
    members: list[dict],
) -> dict[str, str | list[str] | list[dict[str, str]]]:
    """构建工作区成员摘要。"""
    rows = [
        {
            "成员": member.get("display_name") or member["email"],
            "邮箱": member["email"],
            "角色": member["role"],
        }
        for member in members
    ]
    return {
        "title": "工作区成员",
        "description": "先确认当前是谁在这个工作区里、大家分别能做什么，后面再继续补真正的登录和权限拦截。",
        "chips": [
            f"当前工作区：{product_name}",
            f"当前用户：{current_user_name}",
            f"当前角色：{current_role}",
            f"成员 {len(members)} 人",
        ],
        "rows": rows,
    }


def _build_workspace_member_management_meta(
    current_role: str,
) -> dict[str, str | bool | list[str]]:
    """构建工作区成员管理区块文案。"""
    can_manage = current_role == "admin"
    return {
        "title": "成员管理",
        "description": "先把协作者加进当前工作区，再决定谁能改规则、谁只负责看结果；至少保留 1 位管理员，避免工作区失去治理入口。",
        "can_manage": can_manage,
        "fields": ["成员邮箱", "成员名称（可选）", "角色"],
        "blocked_message": "当前账号还不是管理员，所以这里只展示成员列表；真正的增删改成员需要管理员角色。",
    }


def _build_settings_access_meta(current_role: str) -> dict[str, str | list[str]]:
    """构建当前角色在系统设置页的权限摘要。"""
    role = current_role or "viewer"
    editable_tabs_map = {
        "admin": ["规则配置", "规则管理", "关键词库", "产品配置", "API设置", "数据管理"],
        "editor": ["规则配置", "规则管理", "关键词库", "产品配置"],
        "viewer": [],
    }
    restricted_tabs_map = {
        "admin": [],
        "editor": ["成员管理", "API设置", "数据管理"],
        "viewer": ["规则配置", "规则管理", "关键词库", "产品配置", "API设置", "数据管理", "成员管理"],
    }
    description_map = {
        "admin": "管理员可以处理规则、产品、API、数据和成员管理，是当前工作区的全功能入口。",
        "editor": "编辑者先聚焦规则、词库和产品本身，涉及成员管理、模型切换和数据级危险操作时交给管理员。",
        "viewer": "查看者当前只建议阅读成员与产品摘要，避免直接触发配置变更或危险操作。",
    }

    editable_tabs = editable_tabs_map.get(role, [])
    restricted_tabs = restricted_tabs_map.get(role, [])

    return {
        "title": "当前角色权限",
        "description": description_map.get(role, description_map["viewer"]),
        "chips": [
            f"当前角色：{role}",
            f"可编辑 {len(editable_tabs)} 个区块",
            (
                f"受限：{'、'.join(restricted_tabs[:3])}"
                if restricted_tabs
                else "全部关键区块可编辑"
            ),
        ],
        "editable_tabs": editable_tabs,
        "restricted_tabs": restricted_tabs,
    }


def render_settings():
    """渲染系统设置页面"""
    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")
    current_role = "viewer"

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

    if product_id and product_name:
        workspace_notice = st.session_state.pop("workspace_member_notice", None)
        if workspace_notice:
            st.success(workspace_notice)

        current_user_id = st.session_state.get("current_user_id")
        current_user = (
            db.get_user(user_id=current_user_id)
            if current_user_id is not None
            else None
        ) or db.get_or_create_local_owner()
        current_user_name = st.session_state.get("current_user_name") or (
            current_user.get("display_name") or current_user["email"]
        )
        current_role = db.get_workspace_role(product_id, current_user["id"]) or "viewer"
        members = db.get_workspace_members(product_id, include_system_members=True)
        member_summary = _build_workspace_member_summary(
            product_name=product_name,
            current_user_name=current_user_name,
            current_role=current_role,
            members=members,
        )
        st.write(f"### {member_summary['title']}")
        st.caption(member_summary["description"])
        member_chip_cols = st.columns(len(member_summary["chips"]))
        for col, chip in zip(member_chip_cols, member_summary["chips"], strict=False):
            with col:
                st.info(chip)
        if member_summary["rows"]:
            st.dataframe(
                pd.DataFrame(member_summary["rows"]),
                width="stretch",
                hide_index=True,
            )
        access_meta = _build_settings_access_meta(current_role)
        st.write(f"### {access_meta['title']}")
        st.caption(access_meta["description"])
        access_chip_cols = st.columns(len(access_meta["chips"]))
        for col, chip in zip(access_chip_cols, access_meta["chips"], strict=False):
            with col:
                st.info(chip)
        management_meta = _build_workspace_member_management_meta(
            current_role
        )
        st.write(f"### {management_meta['title']}")
        st.caption(management_meta["description"])
        if management_meta["can_manage"]:
            st.info("管理员调整角色时，系统会自动保护最后一个管理员，避免把工作区锁死。")
            with st.form("workspace-member-management-form"):
                email_col, name_col, role_col = st.columns([1.25, 1.0, 0.75])
                with email_col:
                    member_email = st.text_input(
                        "成员邮箱",
                        placeholder="teammate@example.com",
                    )
                with name_col:
                    display_name = st.text_input(
                        "成员名称（可选）",
                        placeholder="运营同学",
                    )
                with role_col:
                    role = st.selectbox(
                        "角色",
                        options=["admin", "editor", "viewer"],
                    )
                submitted = st.form_submit_button("添加或更新成员", width="stretch")

            if submitted:
                try:
                    member = db.upsert_workspace_member_by_email(
                        product_id=product_id,
                        email=member_email,
                        role=role,
                        display_name=display_name or None,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    logger.error("保存工作区成员失败: %s", exc)
                    st.error(safe_error(exc))
                else:
                    member_name = member.get("display_name") or member["email"]
                    st.session_state["workspace_member_notice"] = (
                        f"已将 {member_name} 设置为 {member['role']}。"
                    )
                    st.rerun()
        else:
            st.info(str(management_meta["blocked_message"]))
        st.divider()

    # 标签页
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["规则配置", "规则管理", "关键词库", "产品配置", "API设置", "数据管理"]
    )

    with tab1:
        if current_role in {"admin", "editor"}:
            render_rule_settings(db, product_id)
        else:
            st.info("当前角色没有规则配置权限；如需调整阈值和阶段，请联系工作区管理员或编辑者。")

    with tab2:
        if current_role in {"admin", "editor"}:
            render_rule_management(db, product_id)
        else:
            st.info("当前角色没有规则管理权限；如需新增、重排或回滚规则，请联系工作区管理员或编辑者。")

    with tab3:
        if current_role in {"admin", "editor"}:
            render_keyword_library_settings(db, product_id)
        else:
            st.info("当前角色没有关键词库编辑权限；这里先保持只读，由管理员或编辑者统一维护。")

    with tab4:
        render_product_settings(db, product_id, can_edit=current_role in {"admin", "editor"})

    with tab5:
        if current_role == "admin":
            render_api_settings()
        else:
            st.info("API 设置属于管理员区块；模型切换和密钥配置暂时只开放给管理员处理。")

    with tab6:
        if current_role == "admin":
            render_data_management(db, product_id)
        else:
            st.info("数据管理包含重算、清空和导入导出等敏感操作，当前角色暂不开放。")


def render_product_settings(db, product_id: int, can_edit: bool = True):
    """渲染产品设置。"""
    if not product_id:
        st.warning("请先选择产品")
        return

    product = db.get_product(product_id)

    if not product:
        st.error("产品不存在")
        return

    config = product.get("config", {}) or {}
    summary = _build_product_settings_summary(product)

    st.write(f"### {summary['title']}")
    st.caption(summary["description"])
    chip_cols = st.columns(len(summary["chips"]))
    for col, chip in zip(chip_cols, summary["chips"], strict=False):
        with col:
            st.info(chip)

    with st.container(border=True):
        st.write("#### 基本信息")
        st.caption("先把产品名、ASIN 和类目填稳，后面的词和竞品才有上下文。")
        col1, col2 = st.columns(2)

        with col1:
            product_name = st.text_input(
                "产品名称",
                value=product.get("name", ""),
                disabled=not can_edit,
            )
            product_asin = st.text_input(
                "ASIN",
                value=product.get("asin", ""),
                disabled=not can_edit,
            )

        with col2:
            product_category = st.text_input(
                "品类",
                value=product.get("category", ""),
                placeholder="例如：旅行枕",
                disabled=not can_edit,
            )

    with st.container(border=True):
        st.write("#### 核心关键词")
        st.caption("这里放的是你最想守住的核心词，帮助系统理解哪些词和你的产品最直接相关。")
        core_keywords = config.get("core_keywords", [])
        product_keywords = st.text_area(
            "核心关键词（每行一个）",
            value="\n".join(core_keywords) if core_keywords else "",
            height=120,
            placeholder="travel pillow\nneck pillow",
            disabled=not can_edit,
        )

    with st.container(border=True):
        st.write("#### 竞品ASIN")
        st.caption("把真正需要盯防的对手沉淀在这里，方便系统在竞品流量里做更准确的判断。")
        comp_asins = config.get("competitor_asins", [])
        competitor_asins = st.text_area(
            "竞品ASIN列表（每行一个）",
            value="\n".join(comp_asins) if comp_asins else "",
            height=120,
            placeholder="B0XXXXXXXX\nB0YYYYYYYY",
            disabled=not can_edit,
        )

    if not can_edit:
        st.info("当前角色只能查看产品摘要与关键词配置，产品信息保存需要管理员或编辑者权限。")
        return

    if st.button("保存产品信息", type="primary", width="stretch"):
        try:
            keywords = [k.strip() for k in product_keywords.split("\n") if k.strip()]
            competitors = [a.strip() for a in competitor_asins.split("\n") if a.strip()]

            existing_config = product.get("config", {}) or {}
            existing_config["core_keywords"] = keywords
            existing_config["competitor_asins"] = competitors

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
    """渲染API设置。"""
    from src.config.settings import AVAILABLE_GEMINI_MODELS, Settings

    settings = Settings()
    if "selected_gemini_model" not in st.session_state:
        st.session_state.selected_gemini_model = settings.gemini_model

    model_ids = [m[0] for m in AVAILABLE_GEMINI_MODELS]
    model_labels = [m[1] for m in AVAILABLE_GEMINI_MODELS]

    current_model = st.session_state.selected_gemini_model
    try:
        current_index = model_ids.index(current_model)
    except ValueError:
        current_index = 0

    current_model_label = model_labels[current_index]
    summary = _build_api_settings_summary(
        settings.is_api_configured,
        current_model_label,
    )

    st.write(f"### {summary['title']}")
    st.caption(summary["description"])
    chip_cols = st.columns(len(summary["chips"]))
    for col, chip in zip(chip_cols, summary["chips"], strict=False):
        with col:
            st.info(chip)

    with st.container(border=True):
        st.write("#### 连接状态与模型")
        st.caption("先确认 Gemini API 是否可用，再切换模型；日常排查时先看这里，不用去翻 .env。")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Gemini API**")
            if settings.is_api_configured:
                st.success(f"已配置 (****{settings.gemini_api_key[-4:]})")
            else:
                st.error("未配置 - 请在 .env 文件中填写有效的 GEMINI_API_KEY")

        with col2:
            st.write("**使用模型**")
            selected_index = st.selectbox(
                "选择模型",
                options=range(len(model_labels)),
                index=current_index,
                format_func=lambda i: model_labels[i],
                key="model_selector",
                label_visibility="collapsed",
            )
            selected_model = model_ids[selected_index]
            selected_model_label = model_labels[selected_index]
            if selected_model != st.session_state.selected_gemini_model:
                st.session_state.selected_gemini_model = selected_model
                st.success(f"已切换到 {selected_model_label}")
                st.rerun()
            else:
                st.info(f"当前已选择：{selected_model_label}")

    with st.container(border=True):
        st.write("#### 配置说明")
        st.caption("如果你是第一次配置，按下面三步走就行；这个区块更像运维说明，不需要每天来回看。")
        st.markdown(
            """
1. 在项目根目录创建 `.env` 文件
2. 写入以下内容：
```
GEMINI_API_KEY=your_api_key_here
```
3. 重启应用使其生效

**获取API Key**: [Google AI Studio](https://makersuite.google.com/app/apikey)
            """
        )
