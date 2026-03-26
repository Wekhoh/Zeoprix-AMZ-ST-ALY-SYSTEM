"""集成测试：主应用导航与首页概览体验。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.ui.pages.analysis import _build_truth_summary_metrics, _get_analysis_mode_meta
from src.ui.pages.asin_analysis import _build_asin_hero_meta, _build_asin_summary_cards
from src.ui.pages.home import _build_dashboard_metric_cards, _build_overview_chart_rows
from src.ui.pages.upload import _build_truth_import_guidance


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
    assert _get_current_page_heading(app) == "搜索词分析仪表盘"
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
    quick_action_button.click().run(timeout=20)

    assert _get_current_page_heading(app) == "操作清单"


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
    """上传页导入顺序提示应覆盖未选产品、未导原始报表和可直接导入三种状态。"""
    assert _build_truth_import_guidance(None, 0) == (
        "warning",
        "先选择或创建产品，再导入人工判定表。",
    )
    assert _build_truth_import_guidance(1, 0) == (
        "warning",
        "建议先导入原始报表，再导入广告组人工判定表，否则广告组名称无法匹配。",
    )
    assert _build_truth_import_guidance(1, 6) == (
        "success",
        "当前产品已具备导入条件：先看预检结果，再一键导入人工判定表。",
    )


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
