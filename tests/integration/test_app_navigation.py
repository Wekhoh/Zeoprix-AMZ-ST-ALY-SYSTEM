"""集成测试：主应用导航与首页概览体验。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.config.product_defaults import build_seeded_product_config
from src.ui.pages.analysis import _build_truth_summary_metrics, _get_analysis_mode_meta
from src.ui.pages.asin_analysis import _build_asin_hero_meta, _build_asin_summary_cards
from src.ui.pages.actions import _build_actions_workbench_meta
from src.ui.pages.home import _build_dashboard_metric_cards, _build_overview_chart_rows
from src.ui.pages.review import _build_review_dashboard_state, _build_review_empty_state
from src.ui.pages.settings import (
    _build_api_settings_summary,
    _build_product_settings_summary,
    _build_settings_shell_meta,
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
        "description": "这批数据已经完成人工判定，可以直接回到首页看待处理项，或进入操作清单执行。",
        "badge": "审核闭环已完成",
    }


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
