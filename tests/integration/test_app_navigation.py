"""集成测试：主应用导航与首页概览体验。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.config.product_defaults import build_seeded_product_config
from src.analysis.truth_replay import (
    get_latest_analysis_run_diff_preview,
    get_latest_analysis_run_summary_delta,
)
from src.ui.pages.analysis import (
    _build_analysis_access_meta,
    _build_truth_summary_metrics,
    _get_analysis_mode_meta,
    save_review_changes,
)
from src.ui.pages.analysis_asin import _build_asin_analysis_access_meta
from src.ui.pages.analysis_campaign import _build_campaign_analysis_access_meta
from src.ui.pages.asin_analysis import _build_asin_hero_meta, _build_asin_summary_cards
from src.ui.pages.actions import _build_actions_access_meta, _build_actions_workbench_meta
from src.ui.pages.home import (
    _build_dashboard_metric_cards,
    _build_overview_chart_rows,
    _build_workspace_summary_meta,
)
from src.ui.pages.review import (
    _build_review_access_meta,
    _build_review_dashboard_state,
    _build_review_empty_state,
    _build_review_upsert_payload,
)
from src.ui.pages.settings import (
    _build_api_settings_summary,
    _build_product_settings_summary,
    _build_settings_access_meta,
    _build_settings_shell_meta,
    _build_workspace_member_management_meta,
    _build_workspace_member_removal_meta,
    _build_workspace_member_summary,
)
from src.ui.pages.settings_data import (
    _build_data_management_summary,
    _build_keyword_library_summary,
)
from src.ui.pages.settings_rules import (
    _build_rule_section_meta,
    _build_rule_settings_summary,
)
from src.ui.pages.upload import _build_truth_import_guidance
from src.ui.pages.upload import _build_upload_access_meta


APP_PATH = Path(__file__).resolve().parents[2] / "src" / "app.py"
SIDEBAR_NAV_OPTIONS = [
    "首页",
    "文件上传",
    "搜索词分析",
    "ASIN分析",
    "操作清单",
    "相关性审核",
    "系统设置",
]


def _make_app_test(monkeypatch, db_path: str) -> AppTest:
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    return AppTest.from_file(str(APP_PATH))


def _get_sidebar_nav_radio(app: AppTest):
    return next(
        radio for radio in app.radio if list(radio.options) == SIDEBAR_NAV_OPTIONS
    )


def _get_current_page_heading(app: AppTest) -> str | None:
    """兼容原生标题与自定义 HTML hero 的页面标题提取。"""
    if app.title:
        return app.title[0].value

    for markdown in app.markdown:
        value = markdown.value or ""
        if "<h1>" in value and "</h1>" in value:
            return value.split("<h1>", 1)[1].split("</h1>", 1)[0].strip()
    return None


def test_backend_auth_shell_meta_describes_shared_login():
    """共享后端模式应先展示明确的团队登录壳文案。"""
    from src.app import _build_backend_auth_shell_meta

    meta = _build_backend_auth_shell_meta("https://backend.example.com")

    assert meta == {
        "title": "团队登录",
        "description": "当前应用已切到共享后端模式。同事通过同一个公网地址访问时，会先在这里登录，再进入同一个工作区。",
        "base_url": "https://backend.example.com",
        "fields": ["邮箱", "密码"],
    }


def test_sync_backend_user_to_local_context_assigns_role_across_products(db):
    """后端登录用户应被同步到本地所有工作区，确保旧页面权限继续生效。"""
    from src.app import _clear_backend_auth_session, _sync_backend_user_to_local_context

    st.session_state.clear()
    product_ids = [
        db.create_product(name="旅行枕工作区", asin="B0SYNCROLE1"),
        db.create_product(name="枕套工作区", asin="B0SYNCROLE2"),
    ]
    st.session_state.backend_auth_user = {
        "email": "colleague@example.com",
        "name": "同事",
        "role": "editor",
    }

    local_user = _sync_backend_user_to_local_context(db)

    assert local_user["email"] == "colleague@example.com"
    assert st.session_state.current_user_email == "colleague@example.com"
    assert st.session_state.current_user_name == "同事"
    assert st.session_state.current_user_role == "editor"
    for product_id in product_ids:
        assert db.get_workspace_role(product_id, local_user["id"]) == "editor"

    _clear_backend_auth_session()


def test_app_requires_backend_login_when_shared_mode_enabled(monkeypatch, tmp_path):
    """配置共享后端地址后，应用应先停在团队登录壳而不是直接进入工作台。"""
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "shared-auth.db"))
    monkeypatch.setenv("AMZ_BACKEND_BASE_URL", "https://backend.example.com")

    app = AppTest.from_file(str(APP_PATH))
    app.run(timeout=40)

    assert app.title[0].value == "团队登录"
    assert any("共享后端地址：https://backend.example.com" in info.value for info in app.info)
    assert any(button.label == "登录并进入工作区" for button in app.button)



def test_backend_get_current_user_reads_auth_me_payload(monkeypatch):
    """共享登录态恢复时，应通过 auth/me 获取后端最新用户与角色。"""
    import src.app as app_module

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return (
                '{"id":"user-1","email":"colleague@example.com","name":"同事","role":"viewer"}'.encode("utf-8")
            )

    def fake_urlopen(req, timeout):
        assert req.full_url == "https://backend.example.com/auth/me"
        assert req.get_method() == "GET"
        assert req.headers["Authorization"] == "Bearer access-token"
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_module.request, "urlopen", fake_urlopen)

    payload = app_module._backend_get_current_user("https://backend.example.com", "access-token")

    assert payload == {
        "id": "user-1",
        "email": "colleague@example.com",
        "name": "同事",
        "role": "viewer",
    }



def test_render_backend_auth_gate_refreshes_current_user_from_backend(monkeypatch, db):
    """共享模式下如果 session 里已有 token，应先用 auth/me 刷新当前用户再同步到本地工作区。"""
    import src.app as app_module

    st.session_state.clear()
    product_id = db.create_product(name="共享登录工作区", asin="B0AUTHME01")
    monkeypatch.setenv("AMZ_BACKEND_BASE_URL", "https://backend.example.com")
    st.session_state.backend_access_token = "access-token"

    def fake_backend_get_current_user(base_url, access_token):
        assert base_url == "https://backend.example.com"
        assert access_token == "access-token"
        return {
            "id": "user-2",
            "email": "viewer@example.com",
            "name": "观察同事",
            "role": "viewer",
        }

    monkeypatch.setattr(app_module, "_backend_get_current_user", fake_backend_get_current_user)

    app_module._render_backend_auth_gate(db)

    assert st.session_state.backend_auth_user["email"] == "viewer@example.com"
    assert st.session_state.current_user_email == "viewer@example.com"
    assert st.session_state.current_user_name == "观察同事"
    assert st.session_state.current_user_role == "viewer"

    local_user = db.get_user(email="viewer@example.com")
    assert local_user is not None
    assert db.get_workspace_role(product_id, local_user["id"]) == "viewer"

    app_module._clear_backend_auth_session()


def test_sidebar_product_selector_prefers_current_product_id():
    """侧边栏产品选择器应优先定位到当前产品，而不是固定回到第一个。"""
    from src.app import _get_product_selectbox_index

    products = [
        {"id": 101, "name": "第一个产品"},
        {"id": 202, "name": "第二个产品"},
        {"id": 303, "name": "第三个产品"},
    ]

    assert _get_product_selectbox_index(products, 202) == 1
    assert _get_product_selectbox_index(products, 999) == 0
    assert _get_product_selectbox_index([], 202) is None


def test_sidebar_current_product_name_prefers_selected_product():
    """侧边栏当前产品提示应优先展示 session 中选中的产品。"""
    from src.app import _get_current_product_name

    products = [
        {"id": 101, "name": "第一个产品"},
        {"id": 202, "name": "第二个产品"},
        {"id": 303, "name": "第三个产品"},
    ]

    assert _get_current_product_name(products, 202) == "第二个产品"
    assert _get_current_product_name(products, 999) == "第一个产品"
    assert _get_current_product_name([], 202) is None


def test_sidebar_workspace_context_meta_surfaces_current_user_and_role():
    """侧边栏工作区协作摘要应稳定输出当前用户、角色和成员数。"""
    from src.app import _build_sidebar_workspace_context_meta

    meta = _build_sidebar_workspace_context_meta(
        workspace_name="旅行枕工作区",
        current_user_name="本地工作区管理员",
        member_count=3,
        current_role="admin",
    )

    assert meta == {
        "title": "当前工作区协作",
        "description": "工作区已经绑定成员与角色，后续切到多人协作时会沿着这套上下文继续扩展，不用再从单机工具重搭一次。",
        "chips": [
            "工作区：旅行枕工作区",
            "当前用户：本地工作区管理员",
            "角色：admin",
            "成员 3 人",
        ],
    }


def test_workspace_user_selector_meta_prefers_current_member_and_labels_roles():
    """侧边栏当前身份切换器应优先选中当前成员，并输出可读标签。"""
    from src.app import _build_workspace_user_selector_meta

    members = [
        {
            "user_id": 1,
            "email": "local-owner@workspace.local",
            "display_name": "本地工作区管理员",
            "role": "admin",
        },
        {
            "user_id": 2,
            "email": "viewer@example.com",
            "display_name": "查看者",
            "role": "viewer",
        },
    ]

    meta = _build_workspace_user_selector_meta(members, current_user_id=2)

    assert meta["title"] == "当前身份"
    assert meta["selected_label"] == "查看者 · viewer@example.com（viewer）"
    assert meta["options"] == [
        {
            "label": "本地工作区管理员 · local-owner@workspace.local（admin）",
            "user_id": 1,
            "email": "local-owner@workspace.local",
            "display_name": "本地工作区管理员",
            "role": "admin",
        },
        {
            "label": "查看者 · viewer@example.com（viewer）",
            "user_id": 2,
            "email": "viewer@example.com",
            "display_name": "查看者",
            "role": "viewer",
        },
    ]


def test_resolve_current_user_context_prefers_selected_user_and_falls_back_to_local_owner(db):
    """当前用户上下文应优先使用 session 指定用户，缺失时回退到本地管理员。"""
    from src.app import _resolve_current_user_context

    created_user_id = db.create_user(
        email="viewer@example.com",
        display_name="查看者",
    )

    assert _resolve_current_user_context(db, created_user_id)["email"] == "viewer@example.com"
    assert (
        _resolve_current_user_context(db, 999999)["email"]
        == db.DEFAULT_LOCAL_OWNER_EMAIL
    )


def test_create_product_assigns_default_workspace_admin(db):
    """新建产品工作区时，应自动绑定一个默认本地管理员成员。"""
    product_id = db.create_product(name="新建工作区", asin="B0WORKSPACE1")

    members = db.get_workspace_members(product_id, include_system_members=True)

    assert len(members) == 1
    assert members[0]["role"] == "admin"
    assert members[0]["email"] == "local-owner@workspace.local"


def test_workspace_summary_meta_surfaces_member_count_and_role():
    """首页工作区摘要应稳定输出工作区、成员数和当前角色。"""
    summary = _build_workspace_summary_meta(
        product_name="旅行枕工作区",
        member_count=3,
        current_role="admin",
    )

    assert summary == {
        "title": "当前工作区",
        "description": "把产品分析、规则调整和人工校准都收在同一个工作区里，后续多人协作时可以继续沿用这套成员与角色模型。",
        "chips": [
            "工作区：旅行枕工作区",
            "成员 3 人",
            "当前角色：admin",
        ],
    }


def test_workspace_member_summary_surfaces_roles_and_member_roster():
    """系统设置页应稳定输出工作区成员摘要与成员清单。"""
    summary = _build_workspace_member_summary(
        product_name="旅行枕工作区",
        current_user_name="本地工作区管理员",
        current_role="admin",
        members=[
            {
                "display_name": "本地工作区管理员",
                "email": "local-owner@workspace.local",
                "role": "admin",
            },
            {
                "display_name": "运营同学",
                "email": "operator@example.com",
                "role": "editor",
            },
        ],
    )

    assert summary == {
        "title": "工作区成员",
        "description": "先确认当前是谁在这个工作区里、大家分别能做什么，后面再继续补真正的登录和权限拦截。",
        "chips": [
            "当前工作区：旅行枕工作区",
            "当前用户：本地工作区管理员",
            "当前角色：admin",
            "成员 2 人",
        ],
        "rows": [
            {
                "成员": "本地工作区管理员",
                "邮箱": "local-owner@workspace.local",
                "角色": "admin",
            },
            {
                "成员": "运营同学",
                "邮箱": "operator@example.com",
                "角色": "editor",
            },
        ],
    }


def test_workspace_member_management_meta_gates_admin_actions():
    admin_meta = _build_workspace_member_management_meta("admin")
    viewer_meta = _build_workspace_member_management_meta("viewer")

    assert admin_meta["can_manage"] is True
    assert admin_meta["fields"] == ["成员邮箱", "成员名称（可选）", "角色"]
    assert "至少保留 1 位管理员" in admin_meta["description"]
    assert viewer_meta["can_manage"] is False
    assert "管理员角色" in viewer_meta["blocked_message"]


def test_workspace_member_removal_meta_filters_out_system_owner():
    members = [
        {
            "user_id": 1,
            "email": "local-owner@workspace.local",
            "display_name": "本地工作区管理员",
            "role": "admin",
        },
        {
            "user_id": 2,
            "email": "editor@example.com",
            "display_name": "运营同学",
            "role": "editor",
        },
    ]

    admin_meta = _build_workspace_member_removal_meta("admin", members)
    viewer_meta = _build_workspace_member_removal_meta("viewer", members)

    assert admin_meta["can_manage"] is True
    assert admin_meta["can_remove"] is True
    assert admin_meta["options"] == [
        {
            "label": "运营同学 · editor@example.com（editor）",
            "user_id": 2,
            "email": "editor@example.com",
            "role": "editor",
        }
    ]
    assert "最后一个管理员" in admin_meta["description"]
    assert viewer_meta["can_manage"] is False
    assert viewer_meta["can_remove"] is False


def test_upload_access_meta_distinguishes_admin_editor_and_viewer():
    """上传页权限摘要应稳定区分创建工作区与导入数据的角色边界。"""
    admin_meta = _build_upload_access_meta("admin")
    editor_meta = _build_upload_access_meta("editor")
    viewer_meta = _build_upload_access_meta("viewer")

    assert admin_meta["can_create_workspace"] is True
    assert admin_meta["can_import"] is True
    assert editor_meta["can_create_workspace"] is False
    assert editor_meta["can_import"] is True
    assert viewer_meta["can_create_workspace"] is False
    assert viewer_meta["can_import"] is False
    assert "管理员" in viewer_meta["import_blocked_message"]


def test_review_access_meta_blocks_viewer_but_allows_editor():
    """审核页权限摘要应允许 editor/admin 审核，并阻止 viewer 写入人工校准。"""
    editor_meta = _build_review_access_meta("editor")
    viewer_meta = _build_review_access_meta("viewer")

    assert editor_meta["can_review"] is True
    assert viewer_meta["can_review"] is False
    assert "管理员或编辑者权限" in viewer_meta["blocked_message"]


def test_campaign_and_asin_analysis_access_meta_gate_viewer_sensitive_actions():
    campaign_meta = _build_campaign_analysis_access_meta("viewer")
    asin_meta = _build_asin_analysis_access_meta("viewer")

    assert campaign_meta["can_review"] is False
    assert campaign_meta["can_export"] is False
    assert "批量审核" in campaign_meta["review_blocked_message"]

    assert asin_meta["can_export"] is False
    assert "导出按ASIN分析结果" in asin_meta["blocked_message"]


def test_analysis_and_actions_access_meta_gate_viewer_sensitive_actions():
    analysis_meta = _build_analysis_access_meta("viewer")
    actions_meta = _build_actions_access_meta("viewer")

    assert analysis_meta["can_calibrate"] is False
    assert analysis_meta["can_ai"] is False
    assert analysis_meta["can_export"] is False
    assert "人工校准" in analysis_meta["calibration_blocked_message"]

    assert actions_meta["can_export"] is False
    assert "导出执行清单" in actions_meta["blocked_message"]


def test_settings_access_meta_maps_editor_and_viewer_permissions():
    """系统设置权限摘要应稳定映射 editor/viewer 的可编辑区块和受限区块。"""
    editor_meta = _build_settings_access_meta("editor")
    viewer_meta = _build_settings_access_meta("viewer")

    assert editor_meta["editable_tabs"] == ["规则配置", "规则管理", "关键词库", "产品配置"]
    assert editor_meta["restricted_tabs"] == ["成员管理", "API设置", "数据管理"]
    assert "编辑者" in editor_meta["description"]

    assert viewer_meta["editable_tabs"] == []
    assert viewer_meta["restricted_tabs"] == [
        "规则配置",
        "规则管理",
        "关键词库",
        "产品配置",
        "API设置",
        "数据管理",
        "成员管理",
    ]
    assert "查看者" in viewer_meta["description"]


def test_upsert_workspace_member_by_email_creates_and_updates_workspace_member(db, product_id):
    created_member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="operator@example.com",
        role="editor",
        display_name="运营同学",
    )
    updated_member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="operator@example.com",
        role="viewer",
        display_name="渠道同学",
    )
    members = db.get_workspace_members(product_id, include_system_members=True)
    matching_members = [
        member for member in members if member["email"] == "operator@example.com"
    ]

    assert created_member["role"] == "editor"
    assert updated_member["role"] == "viewer"
    assert updated_member["display_name"] == "渠道同学"
    assert len(matching_members) == 1


def test_upsert_workspace_member_by_email_rejects_demoting_last_admin(db, product_id):
    with pytest.raises(ValueError, match="至少需要保留 1 个管理员"):
        db.upsert_workspace_member_by_email(
            product_id=product_id,
            email=db.DEFAULT_LOCAL_OWNER_EMAIL,
            role="viewer",
            display_name=db.DEFAULT_LOCAL_OWNER_NAME,
        )


def test_remove_workspace_member_deletes_non_admin_member(db, product_id):
    member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="remove-me@example.com",
        role="viewer",
        display_name="待移除成员",
    )

    db.remove_workspace_member(product_id=product_id, user_id=member["user_id"])

    remaining_emails = {
        workspace_member["email"]
        for workspace_member in db.get_workspace_members(
            product_id, include_system_members=True
        )
    }
    assert "remove-me@example.com" not in remaining_emails


def test_remove_workspace_member_rejects_deleting_last_admin(db, product_id):
    local_owner = db.get_or_create_local_owner()

    with pytest.raises(ValueError, match="至少需要保留 1 个管理员"):
        db.remove_workspace_member(product_id=product_id, user_id=local_owner["id"])


def _seed_minimal_search_term(db, campaign_id: int) -> None:
    df = pd.DataFrame(
        [
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "impressions": 100,
                "clicks": 12,
                "ctr": 0.12,
                "spend": 18.0,
                "cpc": 1.5,
                "orders": 2,
                "sales": 40.0,
                "acos": 0.45,
                "roas": 2.22,
                "conversion_rate": 0.16,
                "report_date": "2026-03-21",
            }
        ]
    )
    db.save_search_terms(df, campaign_id)


def test_sidebar_navigation_updates_on_each_selection_change(
    monkeypatch, db, product_id, campaign_id
):
    """侧边栏单击切换页面时，不应滞后一拍。"""
    _seed_minimal_search_term(db, campaign_id)
    app = _make_app_test(monkeypatch, db.db_path)

    app.run(timeout=20)
    assert _get_current_page_heading(app) == "搜索词运营工作台"
    assert len(app.code) == 0

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("文件上传").run(timeout=20)
    assert _get_current_page_heading(app) == "文件上传"

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("搜索词分析").run(timeout=20)
    assert _get_current_page_heading(app) == "搜索词分析"

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("操作清单").run(timeout=20)
    assert _get_current_page_heading(app) == "操作清单"


def test_home_quick_action_button_navigates_after_single_click(
    monkeypatch, db, product_id, campaign_id
):
    """首页快捷按钮单击后应直接跳转目标页面。"""
    _seed_minimal_search_term(db, campaign_id)
    app = _make_app_test(monkeypatch, db.db_path)

    app.run(timeout=20)

    quick_action_button = next(
        button for button in app.button if button.label == "查看操作清单"
    )
    quick_action_button.click().run(timeout=40)

    assert _get_current_page_heading(app) == "操作清单"


def test_homepage_surfaces_workspace_summary(monkeypatch, db, product_id, campaign_id):
    """首页应展示当前工作区、成员数与当前角色摘要。"""
    _seed_minimal_search_term(db, campaign_id)
    app = _make_app_test(monkeypatch, db.db_path)

    app.run(timeout=20)

    markdown_values = [markdown.value or "" for markdown in app.markdown]
    joined = "\n".join(markdown_values)
    assert "workspace-summary-shell" in joined
    assert "当前工作区" in joined


def test_sidebar_surfaces_workspace_collaboration_context(monkeypatch, db, product_id, campaign_id):
    """侧边栏应展示当前工作区协作上下文。"""
    _seed_minimal_search_term(db, campaign_id)
    app = _make_app_test(monkeypatch, db.db_path)

    app.run(timeout=20)

    markdown_values = [markdown.value or "" for markdown in app.markdown]
    joined = "\n".join(markdown_values)
    assert "当前工作区协作" in joined
    assert "当前用户：本地工作区管理员" in joined
    assert "角色：" in joined
    assert "成员 " in joined


def test_sidebar_current_user_switcher_updates_role_context(
    monkeypatch, db, product_id, campaign_id
):
    """切换侧边栏当前身份后，应同步刷新协作上下文与设置页权限。"""
    _seed_minimal_search_term(db, campaign_id)
    db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="viewer@example.com",
        role="viewer",
        display_name="查看者",
    )
    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["db"] = db
    app.session_state["current_product_id"] = product_id

    app.run(timeout=20)

    user_selectbox = next(
        selectbox
        for selectbox in app.selectbox
        if selectbox.label == "当前身份"
    )
    user_selectbox.set_value("查看者 · viewer@example.com（viewer）").run(timeout=20)

    joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    assert "当前用户：查看者" in joined
    assert "角色：viewer" in joined

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("系统设置").run(timeout=20)
    settings_joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    caption_joined = "\n".join(caption.value or "" for caption in app.caption)
    assert "当前角色权限" in settings_joined
    assert "查看者当前只建议阅读成员与产品摘要" in caption_joined


def test_settings_page_blocks_sensitive_tabs_for_viewer(monkeypatch, db, product_id, campaign_id):
    """viewer 角色进入系统设置时，应只看到受限提示，不暴露敏感区块操作。"""
    _seed_minimal_search_term(db, campaign_id)
    viewer_member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="viewer-settings@example.com",
        role="viewer",
        display_name="只读设置成员",
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["current_user_id"] = viewer_member["user_id"]
    app.session_state["current_user_name"] = viewer_member["display_name"]
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("系统设置").run(timeout=20)

    joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    infos = "\n".join(element.value for element in app.info)

    assert "当前角色权限" in joined
    assert "工作区成员" in joined
    assert "当前角色没有规则配置权限" in infos
    assert "API 设置属于管理员区块" in infos
    assert "数据管理包含重算、清空和导入导出等敏感操作" in infos
    assert "当前角色只能查看产品摘要与关键词配置" in infos


def test_upload_page_blocks_sensitive_actions_for_viewer(
    monkeypatch, db, product_id, campaign_id
):
    """viewer 进入上传页时，应只能看导入说明，不能创建工作区或导入文件。"""
    _seed_minimal_search_term(db, campaign_id)
    viewer_member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="viewer-upload@example.com",
        role="viewer",
        display_name="只读上传成员",
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["current_user_id"] = viewer_member["user_id"]
    app.session_state["current_user_name"] = viewer_member["display_name"]
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("文件上传").run(timeout=20)

    product_select = next(
        selectbox for selectbox in app.selectbox if selectbox.label == "选择产品"
    )
    product_select.set_value("创建新产品").run(timeout=20)

    infos = "\n".join(element.value for element in app.info)
    joined = "\n".join(markdown.value or "" for markdown in app.markdown)

    assert "当前上传权限" in joined
    assert "当前角色不能创建新工作区" in infos
    assert "当前角色只能查看导入流程" in infos


def test_review_page_blocks_sensitive_actions_for_viewer(
    monkeypatch, db, product_id, campaign_id
):
    """viewer 进入审核页时，应只看到概览和只读提示，不暴露审核表单。"""
    _seed_minimal_search_term(db, campaign_id)
    db.save_analysis_result_by_term(
        product_id=product_id,
        term="travel pillow",
        triggered_rule="样本不足继续观察",
        suggested_action="观察",
        action_type="observe",
    )
    db.upsert_manual_review(
        product_id=product_id,
        term="travel pillow",
        term_type="keyword",
        campaign_id=campaign_id,
        relevance="pending",
        reviewed=False,
    )
    viewer_member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="viewer-review@example.com",
        role="viewer",
        display_name="只读审核成员",
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["current_user_id"] = viewer_member["user_id"]
    app.session_state["current_user_name"] = viewer_member["display_name"]
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("相关性审核").run(timeout=20)

    infos = "\n".join(element.value for element in app.info)
    joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    text_joined = "\n".join(element.value or "" for element in app.text)

    assert "当前审核权限" in joined
    assert "当前角色只能查看审核概览" in f"{infos}\n{text_joined}"


def test_analysis_page_blocks_sensitive_actions_for_viewer(
    monkeypatch, db, product_id, campaign_id
):
    """viewer 进入搜索词分析页时，应只能查看分析结果，不能执行校准、AI 分析与导出。"""
    _seed_minimal_search_term(db, campaign_id)
    db.save_analysis_result_by_term(
        product_id=product_id,
        term="travel pillow",
        triggered_rule="样本不足继续观察",
        suggested_action="观察",
        action_type="observe",
    )
    viewer_member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="viewer-analysis@example.com",
        role="viewer",
        display_name="只读分析成员",
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["current_user_id"] = viewer_member["user_id"]
    app.session_state["current_user_name"] = viewer_member["display_name"]
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("搜索词分析").run(timeout=20)

    infos = "\n".join(element.value for element in app.info)
    captions = "\n".join((element.value or "") for element in app.caption)
    joined = "\n".join(markdown.value or "" for markdown in app.markdown)

    assert "当前分析权限" in joined
    assert "当前角色只能查看分析结果" in infos
    assert "导出已审核结果需要管理员或编辑者权限" in captions


def test_campaign_analysis_page_blocks_sensitive_actions_for_viewer(
    monkeypatch, db, product_id, campaign_id
):
    """viewer 进入按活动模式时，应只能查看结果，不暴露批量审核与导出操作。"""
    _seed_minimal_search_term(db, campaign_id)
    db.save_analysis_result_by_term(
        product_id=product_id,
        term="travel pillow",
        triggered_rule="样本不足继续观察",
        suggested_action="观察",
        action_type="observe",
    )
    viewer_member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="viewer-campaign@example.com",
        role="viewer",
        display_name="只读活动成员",
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["current_user_id"] = viewer_member["user_id"]
    app.session_state["current_user_name"] = viewer_member["display_name"]
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("搜索词分析").run(timeout=20)

    mode_radio = next(radio for radio in app.radio if radio.label == "分析模式")
    mode_radio.set_value("按活动模式").run(timeout=20)

    joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    infos = "\n".join(element.value for element in app.info)
    captions = "\n".join((element.value or "") for element in app.caption)

    assert "当前活动分析权限" in joined
    assert "当前角色只能查看按活动分析结果" in infos
    assert "导出按活动分析结果需要管理员或编辑者权限" in captions


def test_asin_analysis_page_blocks_export_for_viewer(
    monkeypatch, db, product_id, campaign_id
):
    """viewer 进入按ASIN模式时，应只能查看结果，不暴露导出入口。"""
    _seed_minimal_search_term(db, campaign_id)
    viewer_member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="viewer-asin@example.com",
        role="viewer",
        display_name="只读ASIN成员",
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["current_user_id"] = viewer_member["user_id"]
    app.session_state["current_user_name"] = viewer_member["display_name"]
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("搜索词分析").run(timeout=20)

    mode_radio = next(radio for radio in app.radio if radio.label == "分析模式")
    mode_radio.set_value("按ASIN模式").run(timeout=20)

    joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    infos = "\n".join(element.value for element in app.info)

    assert "当前ASIN分析权限" in joined
    assert "当前角色只能查看按ASIN分析结果" in infos


def test_actions_page_blocks_export_for_viewer(monkeypatch, db, product_id, campaign_id):
    """viewer 进入操作清单页时，应只能查看建议，不暴露导出执行清单入口。"""
    _seed_minimal_search_term(db, campaign_id)
    db.save_analysis_result_by_term(
        product_id=product_id,
        term="travel pillow",
        triggered_rule="高花费低转化否定精准",
        suggested_action="否定精准",
        action_type="negative_exact",
    )
    viewer_member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="viewer-actions@example.com",
        role="viewer",
        display_name="只读操作成员",
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["current_user_id"] = viewer_member["user_id"]
    app.session_state["current_user_name"] = viewer_member["display_name"]
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("操作清单").run(timeout=20)

    infos = "\n".join(element.value for element in app.info)
    joined = "\n".join(markdown.value or "" for markdown in app.markdown)

    assert "当前执行权限" in joined
    assert "当前角色只能查看操作建议" in infos


def test_analysis_ui_reviews_are_saved_as_ui_calibration(db, product_id, campaign_id):
    """搜索词分析页的人工勾选应明确记录为 UI 人工校准来源。"""
    original_df = pd.DataFrame([{"搜索词": "travel pillow", "已审核": False}])
    edited_df = pd.DataFrame([{"搜索词": "travel pillow", "已审核": True}])
    results = [
        {
            "term": "travel pillow",
            "term_type": "keyword",
            "suggested_action": "observe",
        }
    ]

    save_review_changes(
        db=db,
        product_id=product_id,
        original_df=original_df,
        edited_df=edited_df,
        results=results,
        campaign_id=campaign_id,
    )

    row = db.conn.execute(
        """
        SELECT reviewed, review_source
        FROM manual_reviews
        WHERE product_id = ? AND term = ? AND campaign_id = ?
        """,
        (product_id, "travel pillow", campaign_id),
    ).fetchone()

    assert row is not None
    assert row["reviewed"] == 1
    assert row["review_source"] == "ui_calibration"


def test_latest_analysis_run_diff_preview_returns_empty_state_without_two_runs(
    db, product_id
):
    """少于两次分析运行时，应返回明确的空态提示。"""
    db.save_analysis_run_snapshot(
        product_id=product_id,
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "observe",
                "suggested_action": "观察",
                "decision_source": "auto_suggestion",
            }
        ],
        run_source="manual",
        summary={"observe_count": 1},
    )

    preview = get_latest_analysis_run_diff_preview(db, product_id)

    assert preview["rows"] == []
    assert preview["changed_count"] == 0
    assert preview["empty_message"] == "至少完成两次分析运行后，这里才会显示变化清单。"


def test_latest_analysis_run_diff_preview_formats_changed_terms(db, product_id):
    """最近两次分析运行之间的动作变化应被格式化成人话清单。"""
    db.save_analysis_run_snapshot(
        product_id=product_id,
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "observe",
                "suggested_action": "观察",
                "triggered_rule": "样本不足继续观察",
                "decision_source": "auto_suggestion",
            }
        ],
        run_source="manual",
        summary={"observe_count": 1},
    )
    db.save_analysis_run_snapshot(
        product_id=product_id,
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "人工已审核回放",
                "decision_source": "ui_calibration",
            }
        ],
        run_source="manual",
        summary={"negative_count": 1},
    )

    preview = get_latest_analysis_run_diff_preview(db, product_id)

    assert preview["changed_count"] == 1
    assert preview["empty_message"] == ""
    assert preview["rows"] == [
        {
            "搜索词": "travel pillow",
            "类型": "关键词",
            "旧动作": "观察",
            "新动作": "否定精准",
            "旧来源": "自动建议",
            "新来源": "人工校准",
            "旧触发规则": "样本不足继续观察",
            "新触发规则": "人工已审核回放",
            "变化原因": "人工校准覆盖了自动建议。",
        }
    ]


def test_latest_analysis_run_diff_preview_explains_rule_switches(db, product_id):
    """当自动建议触发规则切换时，应输出明确的规则变化解释。"""
    db.save_analysis_run_snapshot(
        product_id=product_id,
        snapshot_rows=[
            {
                "term": "premium neck pillow",
                "normalized_term": "premium neck pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "低转化高点击否定",
                "decision_source": "auto_suggestion",
            }
        ],
        run_source="manual",
        summary={"negative_count": 1},
    )
    db.save_analysis_run_snapshot(
        product_id=product_id,
        snapshot_rows=[
            {
                "term": "premium neck pillow",
                "normalized_term": "premium neck pillow",
                "term_type": "keyword",
                "action_type": "manual_exact_no_neg",
                "suggested_action": "手动精准",
                "triggered_rule": "高转化手动投放",
                "decision_source": "auto_suggestion",
            }
        ],
        run_source="manual",
        summary={"manual_count": 1},
    )

    preview = get_latest_analysis_run_diff_preview(db, product_id)

    assert preview["changed_count"] == 1
    assert preview["rows"][0]["旧触发规则"] == "低转化高点击否定"
    assert preview["rows"][0]["新触发规则"] == "高转化手动投放"
    assert (
        preview["rows"][0]["变化原因"]
        == "规则判断从「低转化高点击否定」切换为「高转化手动投放」。"
    )


def test_latest_analysis_run_summary_delta_returns_empty_state_without_two_runs(
    db, product_id
):
    """少于两次分析运行时，应返回明确的摘要空态提示。"""
    db.save_analysis_run_snapshot(
        product_id=product_id,
        snapshot_rows=[],
        run_source="manual",
        summary={"observe_count": 1},
    )

    summary_delta = get_latest_analysis_run_summary_delta(db, product_id)

    assert summary_delta["cards"] == []
    assert summary_delta["empty_message"] == "至少完成两次分析运行后，这里才会显示变化摘要。"


def test_latest_analysis_run_summary_delta_formats_count_changes(db, product_id):
    """最近两次分析运行应输出稳定的汇总数量变化卡片。"""
    db.save_analysis_run_snapshot(
        product_id=product_id,
        snapshot_rows=[],
        run_source="manual",
        summary={
            "negative_count": 1,
            "manual_count": 0,
            "observe_count": 3,
            "conflict_count": 2,
        },
    )
    db.save_analysis_run_snapshot(
        product_id=product_id,
        snapshot_rows=[],
        run_source="manual",
        summary={
            "negative_count": 4,
            "manual_count": 2,
            "observe_count": 1,
            "conflict_count": 1,
        },
    )

    summary_delta = get_latest_analysis_run_summary_delta(db, product_id)

    assert summary_delta["empty_message"] == ""
    assert summary_delta["cards"] == [
        {"label": "建议否定", "value": 4, "delta": 3},
        {"label": "建议手动投放", "value": 2, "delta": 2},
        {"label": "继续观察", "value": 1, "delta": -2},
        {"label": "跨ASIN分歧", "value": 1, "delta": -1},
    ]


def test_pending_notices_are_rendered_in_truth_first_priority_order():
    """首页待处理项应按 truth-first 优先级输出固定顺序和文案。"""
    from src.ui.pages.home import _build_pending_notices

    notices = _build_pending_notices(
        {
            "negative_count": 37,
            "manual_count": 11,
            "conflict_count": 18,
            "ai_pending_count": 0,
            "review_pending_count": 0,
        }
    )

    assert notices == [
        ("warning", "37 个词需要否定"),
        ("success", "11 个高转化词待投放"),
        ("warning", "18 个词存在跨ASIN分歧，需人工拍板"),
    ]


def test_pending_notices_fall_back_to_empty_state_when_all_counts_are_zero():
    """当没有待处理项时，首页应只显示统一的空状态提示。"""
    from src.ui.pages.home import _build_pending_notices

    notices = _build_pending_notices(
        {
            "negative_count": 0,
            "manual_count": 0,
            "conflict_count": 0,
            "ai_pending_count": 0,
            "review_pending_count": 0,
        }
    )

    assert notices == [("success", "暂无待处理项")]


def test_dashboard_metric_cards_keep_truth_first_order_and_format():
    """首页 KPI 卡片应保持稳定顺序和格式化文案。"""
    cards = _build_dashboard_metric_cards(
        {
            "total_spend": 5803.51,
            "total_orders": 88,
            "acos": 2.4323,
            "term_count": 316,
        }
    )

    assert cards == [
        {"label": "总花费", "value": "$5803.51"},
        {"label": "总订单", "value": "88"},
        {"label": "整体ACOS", "value": "243.23%"},
        {"label": "搜索词数", "value": "316"},
    ]


def test_truth_import_guidance_matches_upload_sequence_rules():
    """上传页应把人工判定表明确表达为可选人工校准入口。"""
    assert _build_truth_import_guidance(None, 0) == (
        "warning",
        "先选择或创建产品工作区，再导入人工校准表。",
    )
    assert _build_truth_import_guidance(1, 0) == (
        "warning",
        "建议先导入原始报表，再导入广告组人工校准表，否则广告活动名称无法匹配。",
    )
    assert _build_truth_import_guidance(1, 6) == (
        "success",
        "当前工作区已具备导入条件：先看预检结果，再一键导入人工校准表。",
    )


def test_seeded_product_config_defaults_to_generic_workspace_template():
    """新建产品工作区默认应使用通用模板，而不是旅行枕验收模板。"""
    config = build_seeded_product_config(product_asin="B0TEST1234")

    assert config["own_asins"] == ["B0TEST1234"]
    assert config["core_keywords"] == []
    assert config["related_keywords"] == []
    assert config["own_variants"] == []
    assert config["competitor_asins"] == []
    assert config["keyword_libraries"] == {
        "irrelevant_keywords": [],
        "weak_category_keywords": [],
        "weak_exact_keywords": [],
        "generic_keywords": [],
        "car_keywords": [],
    }
    assert config["thresholds"] == {
        "min_clicks_for_analysis": 20,
        "min_clicks_for_asin_neg": 6,
        "high_spend_no_order": 20.0,
        "good_cvr": 0.1,
        "bad_cvr": 0.05,
    }


def test_analysis_mode_meta_matches_workbench_copy():
    """搜索词分析页三种模式应有稳定的人话说明。"""
    assert _get_analysis_mode_meta("汇总模式") == {
        "title": "汇总结论视角",
        "description": "把最终动作、跨 ASIN 分歧与执行优先级放在最前面，适合先看结论再处理。",
    }
    assert _get_analysis_mode_meta("按活动模式")["title"] == "广告组级动作视角"
    assert _get_analysis_mode_meta("按ASIN模式")["title"] == "ASIN / 变体差异视角"


def test_truth_summary_metrics_keep_conflicts_out_of_action_counts():
    """truth-first 汇总指标中，跨ASIN分歧不应混入可执行动作计数。"""
    metrics = _build_truth_summary_metrics(
        [
            {"action_type": "negative_exact", "has_conflict": False},
            {"action_type": "negative_phrase", "has_conflict": False},
            {"action_type": "manual_keyword", "has_conflict": False},
            {"action_type": "observe", "has_conflict": False},
            {"action_type": "conflict", "has_conflict": True},
        ]
    )

    assert metrics == {
        "negative_count": 2,
        "manual_count": 1,
        "observe_count": 1,
        "conflict_count": 1,
        "reviewed_label": "5/5",
    }


def test_asin_analysis_hero_meta_matches_workbench_copy():
    """ASIN 分析页 Hero 应稳定输出对比工作台文案。"""
    meta = _build_asin_hero_meta(["BLK", "DBL"])
    assert meta["title"] == "ASIN分析"
    assert meta["chips"] == [
        "已识别 2 个 ASIN",
        "当前重点：BLK / DBL",
        "Top/Bottom 与跨ASIN智能属于洞察页",
    ]


def test_asin_summary_cards_keep_metric_order():
    """ASIN 总览卡片应保持固定指标顺序，避免页面视觉回归。"""
    summary_df = pd.DataFrame(
        [
            {
                "asin_id": "BLK",
                "impressions": 1200,
                "clicks": 45,
                "spend": 67.89,
                "orders": 4,
                "sales": 123.45,
                "ctr": 0.0375,
                "cvr": 0.0889,
                "acos": 0.55,
            }
        ]
    )

    cards = _build_asin_summary_cards(summary_df)
    assert cards == [
        {
            "asin_id": "BLK",
            "metrics": [
                {"label": "展示量", "value": "1,200"},
                {"label": "点击量", "value": "45"},
                {"label": "花费", "value": "$67.89"},
                {"label": "订单", "value": "4"},
                {"label": "销售额", "value": "$123.45"},
                {"label": "CTR", "value": "3.75%"},
                {"label": "CVR", "value": "8.89%"},
                {"label": "ACOS", "value": "55.0%"},
            ],
        }
    ]


def test_actions_workbench_meta_surfaces_execute_vs_review_counts():
    """操作清单页应稳定输出执行面板文案和关键数量。"""
    meta = _build_actions_workbench_meta(
        "桌面验收产品",
        {
            "negative_keyword_exact": [{}] * 24,
            "negative_keyword_phrase": [{}] * 8,
            "negative_asin": [{}] * 5,
            "manual_keywords": [{}] * 9,
            "manual_products": [{}] * 2,
            "cross_asin_conflicts": [{}] * 18,
        },
    )

    assert meta == {
        "eyebrow": "执行面板",
        "title": "操作清单",
        "description": "先处理可直接执行的否词和投放动作，再回头处理需要人工拍板的跨ASIN分歧。",
        "product_label": "桌面验收产品",
        "chips": [
            "可直接否定 37 项",
            "可直接投放 11 项",
            "待人工拍板 18 项",
        ],
    }


def test_review_dashboard_state_and_empty_state_copy():
    """审核页应稳定输出统计概览和完成态文案。"""
    state = _build_review_dashboard_state(
        {"total": 12, "keywords": 9, "asins": 3},
        review_mode="single",
    )
    assert state == {
        "eyebrow": "审核面板",
        "title": "相关性审核",
        "description": "把待审核项按词类型和花费收窄后逐条处理，避免在批量模式里误伤本该细看的词。",
        "chips": [
            "待审核 12 项",
            "关键词 9 项",
            "ASIN 3 项",
            "当前模式：单条模式",
        ],
    }

    assert _build_review_empty_state() == {
        "title": "所有词都已审核完成",
        "description": "这批数据已经完成人工校准，可以直接回到首页看待处理项，或进入操作清单执行。",
        "badge": "审核闭环已完成",
    }


def test_review_upsert_payload_marks_ui_calibration_source():
    """相关性审核页保存时，应把 UI 审核明确标记为人工校准来源。"""
    keyword_payload = _build_review_upsert_payload(
        product_id=1,
        term="travel pillow",
        term_type="keyword",
        scope="local",
        selected_relevance="strong_core",
        selected_competition=None,
        notes="核心词",
    )
    asin_payload = _build_review_upsert_payload(
        product_id=1,
        term="B0TESTASIN",
        term_type="asin",
        scope="global",
        selected_relevance=None,
        selected_competition="can_compete",
        notes="可以竞争",
    )

    assert keyword_payload["review_source"] == "ui_calibration"
    assert keyword_payload["reviewed"] is True
    assert keyword_payload["relevance"] == "strong_core"
    assert keyword_payload["relevance_notes"] == "核心词"
    assert "competition_level" not in keyword_payload

    assert asin_payload["review_source"] == "ui_calibration"
    assert asin_payload["reviewed"] is True
    assert asin_payload["competition_level"] == "can_compete"
    assert asin_payload["competition_notes"] == "可以竞争"
    assert "relevance" not in asin_payload


def test_settings_shell_meta_matches_control_console_copy():
    """系统设置页应稳定输出规则控制台文案。"""
    meta = _build_settings_shell_meta("桌面验收产品")
    assert meta == {
        "eyebrow": "规则控制台",
        "title": "系统设置",
        "description": "把规则、词库、产品信息和数据管理收在同一处，先定策略，再批量应用到当前产品。",
        "chips": [
            "当前产品：桌面验收产品",
            "先调规则，再看分析页回放",
            "数据管理与规则设置分区阅读",
        ],
    }


def test_rule_settings_summary_surfaces_stage_and_thresholds():
    """规则配置页应输出稳定的人话摘要，减少长表单疲劳。"""
    summary = _build_rule_settings_summary(
        {"is_new_product": True},
        {
            "min_clicks_for_analysis": 20,
            "min_clicks_for_asin_neg": 6,
            "high_spend_no_order": 20.0,
            "good_cvr": 0.10,
        },
    )
    assert summary == {
        "title": "规则阈值配置",
        "description": "先确定产品阶段和样本量门槛，再微调 CVR、否词、手动投放和竞品 ASIN 规则，避免把整页输入框当 Excel 填。",
        "chips": [
            "当前阶段：新品期",
            "可靠分析点击门槛 20",
            "ASIN 否定门槛 6 点击 / $20",
            "好转化率 10%",
        ],
    }


def test_rule_section_meta_maps_long_form_into_control_console_sections():
    """规则配置页应把长表单拆成有说明的控制台分区。"""
    sections = _build_rule_section_meta()

    assert [section["title"] for section in sections] == [
        "产品阶段",
        "样本量阈值",
        "转化率阈值 (CVR)",
        "否词规则",
        "手动投放规则",
        "竞品ASIN规则",
    ]
    assert sections[1]["description"].startswith("先把“多少点击才值得认真判断”定住")
    assert sections[-1]["description"].startswith("这里只处理竞品 ASIN 的硬门槛")


def test_keyword_library_summary_surfaces_counts_and_own_variants():
    """关键词库页应先展示词库沉淀规模，而不是直接把用户扔进多段文本框。"""
    summary = _build_keyword_library_summary(
        {
            "keyword_libraries": {
                "irrelevant_keywords": ["massage", "brace"],
                "weak_category_keywords": ["blanket"],
                "generic_keywords": ["pillow", "neck", "home"],
                "car_keywords": ["car"],
            },
            "own_variants": ["B0AAA", "B0BBB"],
        }
    )

    assert summary == {
        "title": "关键词库配置",
        "description": "把搜索词识别里最稳定的人工经验沉淀成词库：先分相关性，再补自家变体，减少每次都从头判断。",
        "chips": [
            "词库总词数 7",
            "不相关词 2",
            "弱相关词 1",
            "自家变体 2",
        ],
    }


def test_data_management_summary_surfaces_scale_before_actions():
    """数据管理页应先告知数据规模，再引导用户做重算、导出或危险操作。"""
    summary = _build_data_management_summary(461, 316, 6)
    assert summary == {
        "title": "数据管理",
        "description": "这里处理的是重跑、清空、导入导出和备份。先看数据规模，再决定是重算、导出还是危险操作。",
        "chips": [
            "搜索词 461",
            "分析结果 316",
            "广告活动 6",
        ],
    }


def test_product_settings_summary_surfaces_identity_and_competition_context():
    """产品配置页应先告诉用户产品身份、核心词和竞品规模，而不是直接掉进输入框。"""
    summary = _build_product_settings_summary(
        {
            "name": "桌面验收产品",
            "asin": "B0TESTASIN",
            "config": {
                "core_keywords": ["travel pillow", "neck pillow"],
                "competitor_asins": ["B0AAA", "B0BBB", "B0CCC"],
            },
        }
    )

    assert summary == {
        "title": "产品配置",
        "description": "把产品基本信息、核心关键词和竞品 ASIN 放在一页里维护，避免系统不知道你卖什么、也不知道你在和谁竞争。",
        "chips": [
            "产品名：桌面验收产品",
            "ASIN 已配置",
            "核心词 2",
            "竞品 ASIN 3",
        ],
    }



def test_api_settings_summary_surfaces_connection_and_model_status():
    """API 设置页应先说明连接状态和当前模型，而不是直接把用户丢进配置说明。"""
    summary = _build_api_settings_summary(True, "Gemini 2.5 Pro")
    assert summary == {
        "title": "API设置",
        "description": "这里只处理模型连接和密钥状态。先确认可用性，再切模型，最后再去分析页验证结果，不要把这里当成日常高频操作页。",
        "chips": [
            "Gemini API 已连接",
            "当前模型：Gemini 2.5 Pro",
            ".env 文件托管密钥",
        ],
    }


def test_overview_chart_rows_are_sorted_for_custom_rendering():
    """��ҳ���ݸ���Ӧ���������������Ⱦ����״ͼ���С"""
    rows = _build_overview_chart_rows(
        {
            "�����۲�-�ؼ���": 154,
            "�񶨾�׼-�ؼ���": 24,
            "�ֶ���׼-�ؼ���": 9,
        }
    )

    assert [row["label"] for row in rows] == [
        "�����۲�-�ؼ���",
        "�񶨾�׼-�ؼ���",
        "�ֶ���׼-�ؼ���",
    ]
    assert [row["value"] for row in rows] == [154, 24, 9]


