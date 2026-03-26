"""集成测试：主应用导航与首页概览体验。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.ui.pages.home import _build_overview_chart_rows


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
    assert app.title[0].value == "搜索词分析仪表盘"

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("文件上传").run(timeout=20)
    assert app.title[0].value == "文件上传"

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("搜索词分析").run(timeout=20)
    assert app.title[0].value == "搜索词分析"

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("操作清单").run(timeout=20)
    assert app.title[0].value == "操作清单"


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
    quick_action_button.click().run(timeout=20)

    assert app.title[0].value == "操作清单"


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
