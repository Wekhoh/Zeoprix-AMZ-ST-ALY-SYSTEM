"""集成测试：主应用导航与首页概览体验。"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import src.analysis.truth_replay as truth_replay_module
import src.ui.pages.analysis as analysis_page_module
import streamlit as st
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from src.backend.app import create_app
from src.config.product_defaults import build_seeded_product_config
from src.rules.engine import AnalysisResult
from src.analysis.truth_replay import (
    build_analysis_run_snapshot_rows,
    get_latest_analysis_run_diff_preview,
    get_latest_analysis_run_summary_delta,
)
from src.ai.chat import ChatResponse, GuidedOption
from src.ai.copilot import (
    build_actions_ai_brief,
    build_asin_ai_brief,
    build_ai_context_badges,
    build_ai_context_pack,
    build_campaign_ai_brief,
    build_chat_response_envelope,
    build_follow_up_context_hint,
    build_review_ai_brief,
    build_summary_ai_brief,
    build_upload_ai_brief,
)
from src.ui.pages.analysis import (
    _build_analysis_access_meta,
    _build_latest_snapshot_summary_rows,
    _build_snapshot_summary_rows,
    _build_truth_summary_metrics,
    _get_analysis_mode_meta,
    save_review_changes,
)
from src.ui.pages.analysis_asin import (
    _build_asin_analysis_access_meta,
    _build_latest_snapshot_asin_rows,
    _build_snapshot_asin_rows,
)
from src.ui.pages.analysis_campaign import (
    _build_campaign_analysis_access_meta,
    _build_latest_snapshot_campaign_rows,
    _build_snapshot_campaign_rows,
)
from src.ui.pages.asin_analysis import _build_asin_hero_meta, _build_asin_summary_cards
from src.ui.pages.actions import (
    _build_actions_access_meta,
    _build_actions_workbench_meta,
    _build_snapshot_action_buckets,
    _get_export_results,
    _get_latest_snapshot_action_context,
)
from src.ui.pages.home import (
    _build_dashboard_metric_cards,
    _build_overview_chart_rows,
    _build_workbench_status_cards,
    _get_product_runtime_state_impl,
    _build_workspace_summary_meta,
)
from src.ui.pages.review import (
    _build_review_access_meta,
    _build_review_dashboard_state,
    _build_review_empty_state,
    _build_review_upsert_payload,
)
from src.ui.pages.settings import (
    _backend_get_workspace_members,
    _backend_remove_workspace_member,
    _backend_upsert_workspace_member,
    _build_api_settings_summary,
    _build_product_settings_summary,
    _build_settings_access_meta,
    _build_settings_shell_meta,
    _build_workspace_member_management_meta,
    _build_workspace_member_removal_meta,
    _build_workspace_member_summary,
    _normalize_backend_workspace_members_for_settings,
)
from src.ui.pages.settings_data import (
    _build_data_management_summary,
    _build_keyword_library_summary,
    build_full_backup_export_payload,
    clear_product_runtime_data,
    restore_full_backup,
)
from src.ui.pages.settings_rules import (
    _build_rule_section_meta,
    _build_rule_settings_summary,
)
from src.ui.pages.upload import _build_analysis_run_state
from src.ui.pages.upload import _build_truth_import_guidance
from src.ui.pages.upload import _build_upload_access_meta
from src.ui.pages.upload import run_analysis


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


def test_build_ai_chat_view_state_exposes_pending_placeholder_and_retry_prompt():
    """AI 聊天视图状态应暴露等待中的占位消息与可重试提示。"""
    from src.app import _build_ai_chat_view_state

    state = _build_ai_chat_view_state(
        [
            {"role": "user", "content": "先帮我看 ACOS"},
            {
                "role": "assistant",
                "content": "AI 请求超时，请稍后重试。",
                "status": "warning",
                "can_retry": True,
                "retry_prompt": "先帮我看 ACOS",
            },
        ],
        is_generating=True,
    )

    assert state["show_empty_state"] is False
    assert state["input_disabled"] is True
    assert state["show_action_bar"] is True
    assert state["show_retry_button"] is False
    assert state["retry_prompt"] == "先帮我看 ACOS"
    assert state["pending_message"] == {
        "role": "assistant",
        "content": "AI 正在思考...",
        "status": "pending",
        "can_retry": False,
        "retry_prompt": None,
    }


def test_build_ai_chat_view_state_hides_action_bar_for_empty_chat():
    """空白聊天态不应先占掉底部空间，输入区必须优先可见。"""
    from src.app import _build_ai_chat_view_state

    state = _build_ai_chat_view_state([], is_generating=False)

    assert state["show_empty_state"] is True
    assert state["show_action_bar"] is False
    assert state["show_retry_button"] is False
    assert state["retry_prompt"] is None


def test_build_ai_error_message_marks_retryable_timeout_and_nonretryable_missing_key():
    """AI 错误状态应区分可重试超时与不可重试的密钥缺失。"""
    from src.app import _build_ai_error_message

    timeout_error = _build_ai_error_message(TimeoutError("request timeout"))
    missing_key_error = _build_ai_error_message(ValueError("未配置 GEMINI_API_KEY"))

    assert timeout_error == {
        "content": "AI 请求超时，请稍后重试。",
        "status": "warning",
        "can_retry": True,
    }
    assert missing_key_error == {
        "content": "当前未配置 AI Key，暂时无法使用 AI 助手。",
        "status": "error",
        "can_retry": False,
    }


def test_build_ai_context_pack_prefers_latest_snapshot(db, product_id):
    """AI 上下文应优先绑定最近一次有效分析快照。"""
    product = db.get_product(product_id)
    product_name = product.get("name", "") if product else ""
    db.save_analysis_run_snapshot(
        product_id=product_id,
        run_source="manual",
        summary={"negative": 2, "manual": 1, "conflict": 0},
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "clicks": 12,
                "orders": 0,
                "spend": 24.0,
                "sales": 0.0,
            }
        ],
    )

    context_pack = build_ai_context_pack(
        db,
        product_id,
        page_key="summary",
        page_title="汇总分析",
    )

    assert context_pack.context_source == "latest_snapshot"
    assert context_pack.snapshot_id is not None
    assert product_name in context_pack.context_label
    assert "最近一次分析结果" in context_pack.context_label
    assert context_pack.metrics["negative_count"] == 2
    assert context_pack.evidence[0]["term"] == "travel pillow"


def test_build_chat_response_envelope_maps_options_and_summary():
    """聊天响应 envelope 应保留结论、追问和上下文标签。"""
    response = ChatResponse(
        message="当前最大的问题是 ACOS 偏高。\n建议先处理高花费无转化词。",
        options=[
            GuidedOption(id="next-1", label="查看最浪费的词"),
            GuidedOption(id="next-2", label="给我 3 个优先动作"),
        ],
        data={"intent": "recommendations"},
    )

    context_pack = build_ai_context_pack(
        db=None,
        product_id=None,
        page_key="summary",
        page_title="汇总分析",
        page_context={"product_name": "桌面验收产品"},
    )

    envelope = build_chat_response_envelope(response, context_pack)

    assert envelope.headline == "当前最大的问题是 ACOS 偏高。"
    assert envelope.bullets == ["建议先处理高花费无转化词。"]
    assert envelope.follow_up_prompts == ["查看最浪费的词", "给我 3 个优先动作"]
    assert envelope.context_label == context_pack.context_label


def test_build_summary_ai_brief_uses_snapshot_counts(db, product_id):
    """汇总页 AI 简报应基于最近一次有效 snapshot 给出结论与建议。"""
    db.save_analysis_run_snapshot(
        product_id=product_id,
        run_source="manual",
        summary={"negative": 3, "manual": 2, "conflict": 1},
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高花费低转化",
                "clicks": 20,
                "orders": 0,
                "spend": 32.0,
                "sales": 0.0,
            }
        ],
    )

    brief = build_summary_ai_brief(db, product_id)

    assert brief["headline"]
    assert any("3" in item for item in brief["bullets"])
    assert brief["recommended_next_actions"]
    assert brief["context_label"].endswith("最近一次分析结果")
    assert "boss_summary" in brief["draft_payload"]
    assert "priority_plan" in brief["draft_payload"]


def test_build_actions_ai_brief_uses_action_context_counts():
    """操作清单 AI 简报应解释当前执行清单规模与下一步动作。"""
    brief = build_actions_ai_brief(
        {
            "counts": {"negative": 4, "manual": 2, "conflict": 1},
            "product_name": "桌面验收产品",
            "context_label": "当前产品：桌面验收产品 · 上下文：最近一次分析结果",
        }
    )

    assert "桌面验收产品" in brief["headline"]
    assert any("4" in item for item in brief["bullets"])
    assert brief["recommended_next_actions"]
    assert "boss_summary" in brief["draft_payload"]
    assert "执行" in brief["draft_payload"]["execution_note"]
    assert "negative_batch_note" in brief["draft_payload"]
    assert "manual_batch_note" in brief["draft_payload"]
    assert "conflict_resolution_note" in brief["draft_payload"]


def test_build_ai_context_badges_include_page_source_and_snapshot_time(db, product_id):
    """上下文徽标应体现页面、来源与快照时间，供成熟 Copilot 统一显示。"""
    db.save_analysis_run_snapshot(
        product_id=product_id,
        run_source="manual",
        summary={"negative": 1, "manual": 0, "conflict": 0},
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "clicks": 12,
                "orders": 0,
                "spend": 24.0,
                "sales": 0.0,
            }
        ],
    )

    context_pack = build_ai_context_pack(
        db,
        product_id,
        page_key="actions",
        page_title="操作清单",
    )

    badges = build_ai_context_badges(context_pack)

    assert badges[0] == "操作清单"
    assert "最近一次分析结果" in badges[1]
    assert any("快照：" in badge for badge in badges)


def test_build_upload_ai_brief_guides_next_steps_after_successful_import_analysis():
    """上传页 AI 简报应在成功导入并完成分析后给出后续工作流建议。"""
    brief = build_upload_ai_brief(
        product_name="桌面验收产品",
        parsed_files_count=2,
        total_terms=316,
        total_spend=248.5,
        total_clicks=143,
        total_orders=11,
        analysis_state={
            "status": "success",
            "message": "分析完成。",
            "terms_analyzed": 54,
            "results_saved": 18,
            "pending_reviews": 6,
        },
    )

    assert "桌面验收产品" in brief["headline"]
    assert any("54" in item for item in brief["bullets"])
    assert any("审核页" in item or "汇总页" in item for item in brief["follow_up_prompts"])
    assert brief["warning"] is None
    assert "import_readout" in brief["draft_payload"]
    assert "analysis_next_step" in brief["draft_payload"]


def test_build_upload_ai_brief_warns_when_import_has_no_actionable_analysis():
    """上传页 AI 简报应解释导入成功但分析未形成建议的 warning 状态。"""
    brief = build_upload_ai_brief(
        product_name="桌面验收产品",
        parsed_files_count=1,
        total_terms=28,
        total_spend=18.3,
        total_clicks=22,
        total_orders=0,
        analysis_state={
            "status": "warning",
            "message": "规则分析已运行，但当前没有生成可保存的建议。",
            "terms_analyzed": 28,
            "results_saved": 0,
            "pending_reviews": 0,
        },
    )

    assert "桌面验收产品" in brief["headline"]
    assert brief["warning"]
    assert any("没有生成可保存的建议" in item for item in brief["bullets"])
    assert "data_quality_note" in brief["draft_payload"]
    assert "analysis_next_step" in brief["draft_payload"]


def test_build_campaign_ai_brief_highlights_top_campaign_signal():
    """按活动 AI 简报应点出最关键活动与浪费信号。"""
    brief = build_campaign_ai_brief(
        [
            {
                "term": "travel pillow",
                "campaign_name": "Brand Exact",
                "campaign_id": "camp-1",
                "action_type": "negative_exact",
                "triggered_rule": "高点击低转化",
                "suggested_action": "否定精准",
                "clicks": 18,
                "orders": 1,
                "spend": 26.5,
                "sales": 31.0,
            },
            {
                "term": "best neck pillow",
                "campaign_name": "Generic Auto",
                "campaign_id": "camp-2",
                "action_type": "manual_keyword",
                "triggered_rule": "高转化补量",
                "suggested_action": "手动精准",
                "clicks": 9,
                "orders": 3,
                "spend": 11.0,
                "sales": 52.0,
            },
        ],
        product_name="桌面验收产品",
        context_label="当前产品：桌面验收产品 · 上下文：最近一次分析结果（按活动）",
    )

    assert "桌面验收产品" in brief["headline"]
    assert any("Brand Exact" in item for item in brief["bullets"])
    assert brief["evidence"][0]["term"] == "travel pillow"
    assert "按活动" in brief["context_label"]
    assert "campaign_focus_note" in brief["draft_payload"]
    assert "budget_shift_note" in brief["draft_payload"]


def test_build_asin_ai_brief_surfaces_variant_focus():
    """按 ASIN AI 简报应指出当前最需要关注的变体。"""
    brief = build_asin_ai_brief(
        [
            {
                "term": "travel pillow",
                "asin_identifier": "B0TESTASIN1",
                "action_type": "negative_exact",
                "triggered_rule": "高点击低转化",
                "suggested_action": "否定精准",
                "clicks": 16,
                "orders": 1,
                "spend": 22.0,
                "sales": 29.0,
            },
            {
                "term": "best neck pillow",
                "asin_identifier": "B0TESTASIN2",
                "action_type": "manual_keyword",
                "triggered_rule": "高转化补量",
                "suggested_action": "手动精准",
                "clicks": 8,
                "orders": 3,
                "spend": 10.0,
                "sales": 49.0,
            },
        ],
        product_name="桌面验收产品",
        context_label="当前产品：桌面验收产品 · 上下文：最近一次分析结果（按 ASIN）",
    )

    assert "桌面验收产品" in brief["headline"]
    assert any("B0TESTASIN1" in item for item in brief["bullets"])
    assert brief["evidence"][0]["term"] == "travel pillow"
    assert "按 ASIN" in brief["context_label"]
    assert "variant_focus_note" in brief["draft_payload"]
    assert "landing_page_note" in brief["draft_payload"]


def test_build_review_ai_brief_distinguishes_ai_and_manual_state():
    """审核页 AI 简报应同时解释 AI 建议与人工当前状态。"""
    brief = build_review_ai_brief(
        term="travel pillow",
        term_type="keyword",
        item={
            "relevance": "generic",
            "total_clicks": 19,
            "total_orders": 1,
            "total_spend": 23.4,
            "triggered_rule": "高点击低转化",
            "suggested_action": "否定精准",
        },
        ai_suggestion={
            "relevance": "weak",
            "confidence": 0.72,
            "reasoning": "搜索意图偏泛",
            "suggested_action": "先否定词组",
        },
        context_label="当前产品：桌面验收产品 · 上下文：最近一次分析结果（审核）",
    )

    assert "travel pillow" in brief["headline"]
    assert any("AI 当前建议" in item for item in brief["bullets"])
    assert any("人工当前标记" in item for item in brief["bullets"])
    assert brief["evidence"][0]["term"] == "travel pillow"
    assert any("为什么这么判断" in prompt for prompt in brief["follow_up_prompts"])
    assert "review_decision_note" in brief["draft_payload"]
    assert "risk_note" in brief["draft_payload"]


def test_normalize_ai_chat_message_preserves_structured_fields():
    """聊天消息标准化后应保留结构化 AI 响应字段。"""
    from src.app import _normalize_ai_chat_message

    normalized = _normalize_ai_chat_message(
        {
            "role": "assistant",
            "content": "这是正文",
            "headline": "一句结论",
            "bullets": ["第一点"],
            "evidence": [{"label": "高花费词", "value": "travel pillow"}],
            "recommended_next_actions": ["先否定 travel pillow"],
            "follow_up_prompts": ["解释为什么"],
            "context_label": "当前产品：桌面验收产品 · 上下文：最近一次分析结果",
            "context_badges": ["汇总分析", "最近一次分析结果"],
            "draft_payload": {"boss_summary": "先止损再补量"},
        }
    )

    assert normalized["headline"] == "一句结论"
    assert normalized["bullets"] == ["第一点"]
    assert normalized["evidence"][0]["label"] == "高花费词"
    assert normalized["recommended_next_actions"] == ["先否定 travel pillow"]
    assert normalized["follow_up_prompts"] == ["解释为什么"]
    assert "最近一次分析结果" in normalized["context_label"]
    assert normalized["context_badges"] == ["汇总分析", "最近一次分析结果"]
    assert normalized["draft_payload"]["boss_summary"] == "先止损再补量"


def test_queue_ai_message_sets_pending_generation_state():
    """提交 AI 对话时应立即写入用户消息并标记生成中。"""
    from src.app import _queue_ai_message

    st.session_state.clear()
    st.session_state.chat_messages = []
    st.session_state.ai_chat_is_generating = False
    st.session_state.ai_chat_pending_prompt = None
    st.session_state.ai_chat_last_prompt = None

    queued = _queue_ai_message("  请总结当前产品问题  ")

    assert queued is True
    assert st.session_state.ai_chat_is_generating is True
    assert st.session_state.ai_chat_pending_prompt == "请总结当前产品问题"
    assert st.session_state.ai_chat_last_prompt == "请总结当前产品问题"
    assert "ai_chat_last_routed_from" not in st.session_state
    assert st.session_state.chat_messages == [
        {
            "role": "user",
            "content": "请总结当前产品问题",
            "status": "default",
            "can_retry": False,
            "retry_prompt": None,
        }
    ]


def test_queue_ai_message_tracks_source_hint():
    """由页面卡片发起的追问应记录来源提示，供侧边栏展示上下文。"""
    from src.app import _queue_ai_message

    st.session_state.clear()
    st.session_state.chat_messages = []
    st.session_state.ai_chat_is_generating = False
    st.session_state.ai_chat_pending_prompt = None
    st.session_state.ai_chat_last_prompt = None

    queued = _queue_ai_message(
        "请解释为什么 ACOS 偏高",
        source_label="汇总页 AI 简报",
        source_context_hint="当前 ACOS 偏高，重点词：travel pillow、neck support",
    )

    assert queued is True
    assert st.session_state.ai_chat_last_routed_from == "汇总页 AI 简报"
    assert (
        st.session_state.ai_chat_last_routed_context
        == "当前 ACOS 偏高，重点词：travel pillow、neck support"
    )


def test_clear_ai_chat_history_resets_source_hint():
    """清空对话时应一并清理最近一次路由来源提示。"""
    from src.app import _clear_ai_chat_history

    st.session_state.clear()
    st.session_state.chat_messages = [{"role": "user", "content": "hello"}]
    st.session_state.ai_chat_is_generating = False
    st.session_state.ai_chat_pending_prompt = None
    st.session_state.ai_chat_last_prompt = "hello"
    st.session_state.ai_chat_last_routed_from = "汇总页 AI 简报"
    st.session_state.ai_chat_last_routed_context = "当前 ACOS 偏高"

    _clear_ai_chat_history()

    assert st.session_state.chat_messages == []
    assert "ai_chat_last_routed_from" not in st.session_state
    assert "ai_chat_last_routed_context" not in st.session_state


def test_build_follow_up_context_hint_uses_headline_and_terms():
    """页面 AI 卡片追问应携带简短结论与关键词线索。"""
    hint = build_follow_up_context_hint(
        {
            "headline": "当前 ACOS 偏高，建议先止损后补量。",
            "evidence": [
                {"term": "travel pillow"},
                {"term": "neck support"},
                {"term": "memory foam pillow"},
            ],
        }
    )

    assert "当前 ACOS 偏高" in hint
    assert "travel pillow" in hint
    assert "neck support" in hint


def test_get_ai_chat_panel_height_keeps_follow_up_input_visible():
    """有历史消息时应缩短消息面板，为持续对话留出输入区空间。"""
    from src.app import (
        AI_CHAT_EMPTY_PANEL_HEIGHT,
        AI_CHAT_MESSAGES_PANEL_HEIGHT,
        _get_ai_chat_panel_height,
    )

    assert _get_ai_chat_panel_height(True) == AI_CHAT_EMPTY_PANEL_HEIGHT
    assert _get_ai_chat_panel_height(False) == AI_CHAT_MESSAGES_PANEL_HEIGHT
    assert AI_CHAT_MESSAGES_PANEL_HEIGHT < AI_CHAT_EMPTY_PANEL_HEIGHT + 40


def test_build_ai_chat_scroll_script_targets_anchor_and_scrolls():
    """自动滚动脚本应指向锚点并使用 sessionStorage 去重。"""
    from src.app import _build_ai_chat_scroll_script

    script = _build_ai_chat_scroll_script("sidebar-anchor", "count=2")

    assert "sidebar-anchor" in script
    assert "scrollIntoView" in script
    assert "sessionStorage" in script


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



def test_backend_get_default_workspace_members_reads_member_payload(monkeypatch):
    """共享模式应从后端读取当前工作区成员列表，而不是继续依赖本地数据库直连。"""
    import src.app as app_module

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return (
                '[{"id":"user-1","email":"owner@example.com","name":"管理员","role":"admin"},'
                '{"id":"user-2","email":"viewer@example.com","name":"观察同事","role":"viewer"}]'.encode("utf-8")
            )

    def fake_urlopen(req, timeout):
        assert req.full_url == "https://backend.example.com/workspaces/default/members"
        assert req.get_method() == "GET"
        assert req.headers["Authorization"] == "Bearer access-token"
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_module.request, "urlopen", fake_urlopen)

    members = app_module._backend_get_default_workspace_members(
        "https://backend.example.com", "access-token"
    )

    assert members == [
        {"id": "user-1", "email": "owner@example.com", "name": "管理员", "role": "admin"},
        {"id": "user-2", "email": "viewer@example.com", "name": "观察同事", "role": "viewer"},
    ]



def test_render_backend_auth_gate_refreshes_current_user_from_backend(monkeypatch, db):
    """共享模式下如果 session 里已有 token，应先用 auth/me 刷新当前用户和工作区上下文再同步到本地工作区。"""
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

    def fake_refresh_backend_workspace_context(base_url, access_token):
        assert base_url == "https://backend.example.com"
        assert access_token == "access-token"
        st.session_state.backend_workspace = {
            "id": "default-workspace",
            "name": "共享团队工作区",
            "role": "viewer",
            "member_count": 2,
        }
        st.session_state.backend_workspace_members = [
            {
                "id": "user-1",
                "email": "owner@example.com",
                "name": "管理员",
                "role": "admin",
            },
            {
                "id": "user-2",
                "email": "viewer@example.com",
                "name": "观察同事",
                "role": "viewer",
            },
        ]
        return {
            "workspace": st.session_state.backend_workspace,
            "members": st.session_state.backend_workspace_members,
        }

    monkeypatch.setattr(app_module, "_backend_get_current_user", fake_backend_get_current_user)
    monkeypatch.setattr(
        app_module,
        "_refresh_backend_workspace_context",
        fake_refresh_backend_workspace_context,
    )

    app_module._render_backend_auth_gate(db)

    assert st.session_state.backend_auth_user["email"] == "viewer@example.com"
    assert st.session_state.backend_workspace["name"] == "共享团队工作区"
    assert len(st.session_state.backend_workspace_members) == 2
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


def test_build_sidebar_collaboration_state_prefers_backend_workspace_context(db):
    """共享模式下，侧边栏应优先使用后端工作区与成员上下文，并关闭本地身份切换。"""
    import src.app as app_module

    st.session_state.clear()
    product_id = db.create_product(name="本地旅行枕工作区", asin="B0BACKSID1")
    st.session_state.backend_auth_user = {
        "id": "user-2",
        "email": "viewer@example.com",
        "name": "观察同事",
        "role": "viewer",
    }
    st.session_state.backend_workspace = {
        "id": "default-workspace",
        "name": "后端共享工作区",
        "role": "viewer",
        "member_count": 2,
    }
    st.session_state.backend_workspace_members = [
        {"id": "user-1", "email": "owner@example.com", "name": "管理员", "role": "admin"},
        {"id": "user-2", "email": "viewer@example.com", "name": "观察同事", "role": "viewer"},
    ]

    state = app_module._build_sidebar_collaboration_state(
        db,
        product_id,
        "本地旅行枕工作区",
    )

    assert state["workspace_name"] == "后端共享工作区"
    assert state["member_count"] == 2
    assert state["selected_member"] == {
        "user_id": "user-2",
        "email": "viewer@example.com",
        "display_name": "观察同事",
        "role": "viewer",
    }
    assert state["show_identity_switcher"] is False
    assert "团队登录决定" in state["identity_hint"]


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


def test_ensure_local_owner_admin_memberships_backfills_legacy_products(db):
    """历史产品缺失工作区成员时，应自动补齐本地管理员 admin 身份。"""
    product_id = db.create_product(name="旧工作区", asin="B0LEGACY001")
    owner = db.get_or_create_local_owner()
    db.execute(
        "DELETE FROM workspace_memberships WHERE product_id = ? AND user_id = ?",
        (product_id, owner["id"]),
    )
    db.commit()

    repaired = db.ensure_local_owner_admin_memberships()

    assert repaired >= 1
    assert db.get_workspace_role(product_id, owner["id"]) == "admin"


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


def test_runtime_state_marks_empty_workspace_as_ready_for_import(db, product_id):
    """首页状态中心应把空工作区标记为待导入原始数据。"""
    state = _get_product_runtime_state_impl(
        db,
        product_id,
        stats={
            "term_count": 0,
            "total_spend": 0,
            "total_orders": 0,
            "total_sales": 0,
            "acos": 0,
        },
        pending_stats={},
    )

    assert state["stage_key"] == "ready_for_import"
    assert state["stage_title"] == "待导入原始数据"
    assert state["snapshot_count"] == 0
    assert any(action[0] == "去文件上传" for action in state["next_actions"])


def test_runtime_state_prioritizes_review_then_execution(db, product_id, campaign_id):
    """首页状态中心应优先提示待审核，其次才是待执行。"""
    _seed_minimal_search_term(db, campaign_id)
    db.save_analysis_run_snapshot(
        product_id=product_id,
        run_source="manual",
        summary={"negative": 2, "manual": 1, "conflict": 0},
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "clicks": 12,
                "orders": 0,
                "spend": 24.0,
                "sales": 0.0,
            }
        ],
    )

    review_state = _get_product_runtime_state_impl(
        db,
        product_id,
        stats={
            "term_count": 1,
            "total_spend": 24.0,
            "total_orders": 0,
            "total_sales": 0,
            "acos": 0,
        },
        pending_stats={"review_pending_count": 3, "negative_count": 2, "manual_count": 1},
    )
    execution_state = _get_product_runtime_state_impl(
        db,
        product_id,
        stats={
            "term_count": 1,
            "total_spend": 24.0,
            "total_orders": 0,
            "total_sales": 0,
            "acos": 0,
        },
        pending_stats={"review_pending_count": 0, "negative_count": 2, "manual_count": 1},
    )

    assert review_state["stage_key"] == "needs_review"
    assert execution_state["stage_key"] == "ready_for_execution"


def test_build_workbench_status_cards_surfaces_snapshot_and_scale():
    """工作状态卡片应稳定暴露阶段、最新分析、历史沉淀与数据规模。"""
    cards = _build_workbench_status_cards(
        {
            "stage_title": "待执行优化动作",
            "stage_description": "先止损再补量。",
            "latest_snapshot_at": "2026-04-11 12:34:56",
            "snapshot_count": 4,
            "campaign_count": 6,
            "search_term_count": 316,
            "analysis_result_count": 98,
            "manual_review_count": 25,
            "next_actions": [],
        }
    )

    assert cards[0]["label"] == "当前阶段"
    assert "待执行优化动作" in cards[0]["value"]
    assert cards[1]["label"] == "最近一次分析"
    assert "2026-04-11 12:34" in cards[1]["value"]
    assert cards[2]["value"] == "4 个分析快照"
    assert "316 条搜索词 / 6 个活动" in cards[3]["value"]


def test_homepage_renders_workbench_status_center(monkeypatch, db, product_id, campaign_id):
    """首页应真实渲染当前工作状态中心，而不只是 KPI 和快捷按钮。"""
    _seed_minimal_search_term(db, campaign_id)
    db.save_analysis_run_snapshot(
        product_id=product_id,
        run_source="manual",
        summary={"negative": 2, "manual": 1, "conflict": 0},
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "clicks": 12,
                "orders": 0,
                "spend": 24.0,
                "sales": 0.0,
            }
        ],
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["current_product_id"] = product_id
    app.run(timeout=20)

    joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    assert "当前工作状态" in joined
    assert "最近一次分析" in joined
    assert "历史沉淀" in joined


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


def _bootstrap_backend_api(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(
        "AMZ_BACKEND_DATABASE_URL",
        f"sqlite:///{(tmp_path / 'backend-settings.db').as_posix()}",
    )
    monkeypatch.setenv("AMZ_BACKEND_JWT_SECRET", "test-secret-with-at-least-32-bytes")
    monkeypatch.setenv("AMZ_BOOTSTRAP_ADMIN_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMZ_BOOTSTRAP_ADMIN_PASSWORD", "owner-password")
    monkeypatch.setenv("AMZ_BOOTSTRAP_ADMIN_NAME", "Workspace Owner")


def _login_backend_user(client: TestClient, email: str, password: str) -> tuple[str, dict]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    body = response.json()
    return body["access_token"], body["user"]


def test_backend_workspace_member_delete_endpoint_deletes_non_admin(monkeypatch, tmp_path):
    _bootstrap_backend_api(monkeypatch, tmp_path)

    with TestClient(create_app()) as client:
        owner_token, _ = _login_backend_user(client, "owner@example.com", "owner-password")
        create_member = client.post(
            "/workspaces/default/members",
            json={
                "email": "viewer@example.com",
                "name": "Viewer",
                "password": "viewer-password",
                "role": "viewer",
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert create_member.status_code == 200

        member_id = create_member.json()["id"]
        delete_member = client.delete(
            f"/workspaces/default/members/{member_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert delete_member.status_code == 200
        assert delete_member.json()["email"] == "viewer@example.com"

        members_response = client.get(
            "/workspaces/default/members",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert members_response.status_code == 200
        assert [member["email"] for member in members_response.json()] == ["owner@example.com"]


def test_backend_workspace_member_delete_endpoint_rejects_last_admin(monkeypatch, tmp_path):
    _bootstrap_backend_api(monkeypatch, tmp_path)

    with TestClient(create_app()) as client:
        owner_token, owner = _login_backend_user(client, "owner@example.com", "owner-password")
        delete_owner = client.delete(
            f"/workspaces/default/members/{owner['id']}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    assert delete_owner.status_code == 400
    assert "At least one workspace admin must remain assigned." in delete_owner.json()["detail"]


def test_shared_settings_member_helpers_use_backend_api(monkeypatch):
    import src.ui.pages.settings as settings_module

    captured = []

    class DummyResponse:
        def __init__(self, body: str):
            self._body = body.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self._body

    def fake_urlopen(req, timeout):
        captured.append(
            {
                "url": req.full_url,
                "method": req.get_method(),
                "auth": req.headers.get("Authorization"),
                "body": req.data.decode("utf-8") if req.data else None,
                "timeout": timeout,
            }
        )
        if req.get_method() == "GET":
            return DummyResponse(
                '[{"id":"user-1","email":"owner@example.com","name":"Owner","role":"admin"}]'
            )
        if req.get_method() == "POST":
            return DummyResponse(
                '{"id":"user-2","email":"editor@example.com","name":"Editor","role":"editor"}'
            )
        if req.get_method() == "DELETE":
            return DummyResponse(
                '{"id":"user-2","email":"editor@example.com","name":"Editor","role":"editor"}'
            )
        raise AssertionError("unexpected method")

    monkeypatch.setattr(settings_module.request, "urlopen", fake_urlopen)

    members = _backend_get_workspace_members("https://backend.example.com", "access-token")
    created = _backend_upsert_workspace_member(
        "https://backend.example.com",
        "access-token",
        email="editor@example.com",
        password="editor-password",
        role="editor",
        display_name="Editor",
    )
    removed = _backend_remove_workspace_member(
        "https://backend.example.com",
        "access-token",
        user_id="user-2",
    )

    assert members == [
        {"id": "user-1", "email": "owner@example.com", "name": "Owner", "role": "admin"}
    ]
    assert created["email"] == "editor@example.com"
    assert removed["id"] == "user-2"
    assert captured == [
        {
            "url": "https://backend.example.com/workspaces/default/members",
            "method": "GET",
            "auth": "Bearer access-token",
            "body": None,
            "timeout": 5,
        },
        {
            "url": "https://backend.example.com/workspaces/default/members",
            "method": "POST",
            "auth": "Bearer access-token",
            "body": '{"email": "editor@example.com", "password": "editor-password", "role": "editor", "name": "Editor"}',
            "timeout": 5,
        },
        {
            "url": "https://backend.example.com/workspaces/default/members/user-2",
            "method": "DELETE",
            "auth": "Bearer access-token",
            "body": None,
            "timeout": 5,
        },
    ]


def test_shared_settings_member_helpers_normalize_backend_members():
    normalized = _normalize_backend_workspace_members_for_settings(
        [
            {"id": "user-1", "email": "owner@example.com", "name": "Owner", "role": "admin"},
            {"id": "user-2", "email": "viewer@example.com", "name": "", "role": "viewer"},
        ]
    )

    assert normalized == [
        {
            "user_id": "user-1",
            "email": "owner@example.com",
            "display_name": "Owner",
            "role": "admin",
        },
        {
            "user_id": "user-2",
            "email": "viewer@example.com",
            "display_name": "viewer@example.com",
            "role": "viewer",
        },
    ]


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


def test_settings_page_blocks_sensitive_tabs_for_viewer():
    """viewer 角色进入系统设置时，应只看到受限提示，不暴露敏感区块操作。"""
    meta = _build_settings_access_meta("viewer")

    assert meta["editable_tabs"] == []
    assert "规则配置" in meta["restricted_tabs"]
    assert "数据管理" in meta["restricted_tabs"]
    assert "查看者" in meta["description"]


def test_upload_page_blocks_sensitive_actions_for_viewer():
    """viewer 进入上传页时，应只能看导入说明，不能创建工作区或导入文件。"""
    meta = _build_upload_access_meta("viewer")

    assert meta["can_create_workspace"] is False
    assert meta["can_import"] is False
    assert "当前角色不能创建新工作区" in meta["create_blocked_message"]
    assert "当前角色只能查看导入流程" in meta["import_blocked_message"]


def test_upload_page_renders_ai_brief_before_file_selection(
    monkeypatch, db, product_id, campaign_id
):
    """上传页在未选择文件前，也应展示 AI 导入摘要并提示先上传文件。"""
    _seed_minimal_search_term(db, campaign_id)
    local_owner = db.get_or_create_local_owner()
    db.upsert_workspace_member_by_email(
        product_id=product_id,
        email=db.DEFAULT_LOCAL_OWNER_EMAIL,
        role="admin",
        display_name="本地工作区管理员",
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["current_product_id"] = product_id
    app.session_state["current_user_id"] = local_owner["id"]
    app.session_state["current_user_name"] = (
        local_owner.get("display_name") or "本地工作区管理员"
    )
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("文件上传").run(timeout=20)

    joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    assert _get_current_page_heading(app) == "文件上传"

    assert "AI 导入摘要" in joined
    assert "还没有可分析的导入文件" in joined


def test_review_page_blocks_sensitive_actions_for_viewer():
    """viewer 进入审核页时，应只看到概览和只读提示，不暴露审核表单。"""
    meta = _build_review_access_meta("viewer")

    assert meta["can_review"] is False
    assert "当前角色只能查看审核概览" in meta["blocked_message"]


def test_review_page_renders_ai_brief_when_queue_is_empty_for_viewer(
    monkeypatch, db, product_id
):
    """审核页在队列为空且 viewer 只读时，也应显示 AI 审核建议卡。"""
    viewer_member = db.upsert_workspace_member_by_email(
        product_id=product_id,
        email="viewer-review-empty@example.com",
        role="viewer",
        display_name="只读审核成员",
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["current_product_id"] = product_id
    app.session_state["current_user_id"] = viewer_member["user_id"]
    app.session_state["current_user_name"] = viewer_member["display_name"]
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("相关性审核").run(timeout=20)

    joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    text_joined = "\n".join(element.value or "" for element in app.text)
    combined = "\n".join(part for part in [joined, text_joined] if part)

    assert "AI 审核建议" in joined
    assert "当前还没有 AI 审核建议" in joined
    assert "审核闭环已完成" in joined
    assert "所有词都已审核完成" in combined


def test_analysis_page_blocks_sensitive_actions_for_viewer():
    """viewer 进入搜索词分析页时，应只能查看分析结果，不能执行校准、AI 分析与导出。"""
    meta = _build_analysis_access_meta("viewer")

    assert meta["can_calibrate"] is False
    assert meta["can_ai"] is False
    assert meta["can_export"] is False
    assert "当前角色只能查看分析结果" in meta["calibration_blocked_message"]
    assert "导出已审核结果需要管理员或编辑者权限" in meta["export_blocked_message"]


def test_summary_page_renders_ai_brief_for_truth_first_results(
    monkeypatch, db, product_id, campaign_id
):
    """汇总页在 truth-first 分支也应显示 AI 汇总简报。"""
    _seed_minimal_search_term(db, campaign_id)

    monkeypatch.setattr(
        truth_replay_module,
        "get_truth_first_summary_rows",
        lambda _db, _product_id: [
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "asin_identifiers": ["B0TESTASIN"],
                "asin_count": 1,
                "triggered_rule": "人工已审核回放",
                "suggested_action": "否定精准",
                "action_type": "negative_exact",
                "action_detail": "否定精准",
                "confidence": 1.0,
                "reviewed": True,
                "has_conflict": False,
                "clicks": 18,
                "orders": 0,
                "spend": 22.4,
                "sales": 0.0,
                "cvr": 0.0,
                "acos": 0.0,
            }
        ],
    )
    monkeypatch.setattr(
        truth_replay_module, "get_latest_analysis_run_diff_preview", lambda *_: None
    )
    monkeypatch.setattr(
        truth_replay_module, "get_latest_analysis_run_summary_delta", lambda *_: None
    )
    monkeypatch.setattr(
        analysis_page_module,
        "build_summary_ai_brief",
        lambda *_: {
            "headline": "汇总页 AI 已就绪",
            "context_label": "上下文：人工校准结果",
            "bullets": ["travel pillow 当前已被人工确认应优先否定。"],
            "recommended_next_actions": ["先在操作清单确认这批否词。"],
            "follow_up_prompts": [],
        },
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["db"] = db
    app.session_state["current_product_id"] = product_id
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("搜索词分析").run(timeout=20)

    joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    assert "AI 汇总简报" in joined
    assert "汇总页 AI 已就绪" in joined


def test_summary_page_renders_ai_brief_for_snapshot_results(
    monkeypatch, db, product_id, campaign_id
):
    """汇总页在最近一次有效快照分支也应显示 AI 汇总简报。"""
    _seed_minimal_search_term(db, campaign_id)

    monkeypatch.setattr(truth_replay_module, "get_truth_first_summary_rows", lambda *_: None)
    monkeypatch.setattr(
        truth_replay_module, "get_latest_analysis_run_diff_preview", lambda *_: None
    )
    monkeypatch.setattr(
        truth_replay_module, "get_latest_analysis_run_summary_delta", lambda *_: None
    )
    monkeypatch.setattr(
        analysis_page_module,
        "_build_latest_snapshot_summary_rows",
        lambda *_: [
            {
                "term": "neck support",
                "term_type": "keyword",
                "asin_identifiers": [],
                "asin_count": 0,
                "triggered_rule": "最近一次有效分析快照",
                "suggested_action": "手动精准",
                "action_type": "manual_exact",
                "action_detail": "手动精准",
                "confidence": 0.86,
                "reviewed": False,
                "has_conflict": False,
                "clicks": 12,
                "orders": 3,
                "spend": 15.8,
                "sales": 80.0,
                "cvr": 0.25,
                "acos": 0.1975,
            }
        ],
    )
    monkeypatch.setattr(
        analysis_page_module,
        "build_summary_ai_brief",
        lambda *_: {
            "headline": "快照分支也会显示 AI 汇总简报",
            "context_label": "上下文：最近一次有效分析结果",
            "bullets": ["neck support 当前值得优先补量。"],
            "recommended_next_actions": ["先在操作清单确认手动投放动作。"],
            "follow_up_prompts": [],
        },
    )

    app = _make_app_test(monkeypatch, db.db_path)
    app.session_state["db"] = db
    app.session_state["current_product_id"] = product_id
    app.run(timeout=20)

    sidebar_radio = _get_sidebar_nav_radio(app)
    sidebar_radio.set_value("搜索词分析").run(timeout=20)

    joined = "\n".join(markdown.value or "" for markdown in app.markdown)
    assert "AI 汇总简报" in joined
    assert "快照分支也会显示 AI 汇总简报" in joined


def test_campaign_analysis_page_blocks_sensitive_actions_for_viewer():
    """viewer 进入按活动模式时，应只能查看结果，不暴露批量审核与导出操作。"""
    meta = _build_campaign_analysis_access_meta("viewer")

    assert meta["can_review"] is False
    assert meta["can_export"] is False
    assert "当前角色只能查看按活动分析结果" in meta["review_blocked_message"]
    assert "导出按活动分析结果需要管理员或编辑者权限" in meta["export_blocked_message"]


def test_asin_analysis_page_blocks_export_for_viewer():
    """viewer 进入按ASIN模式时，应只能查看结果，不暴露导出入口。"""
    meta = _build_asin_analysis_access_meta("viewer")

    assert meta["can_export"] is False
    assert "当前角色只能查看按ASIN分析结果" in meta["blocked_message"]


def test_actions_page_blocks_export_for_viewer():
    """viewer 进入操作清单页时，应只能查看建议，不暴露导出执行清单入口。"""
    meta = _build_actions_access_meta("viewer")

    assert meta["can_export"] is False
    assert "当前角色只能查看操作建议" in meta["blocked_message"]


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




def test_analysis_run_state_tracks_counts_and_retry_flags():
    """上传后分析状态应显式区分结果规模与是否可重试。"""
    state = _build_analysis_run_state(
        "success",
        "分析完成",
        terms_analyzed=12,
        results_saved=9,
        pending_reviews=3,
    )

    assert state == {
        "status": "success",
        "message": "分析完成",
        "terms_analyzed": 12,
        "results_saved": 9,
        "pending_reviews": 3,
        "can_retry": False,
    }


def test_run_analysis_returns_warning_when_no_aggregated_terms(monkeypatch, db, product_id):
    """上传成功但没有可聚合词时，不能伪装成“分析完成”。"""
    import src.data.aggregator as aggregator_module
    import src.rules.engine as engine_module

    class EmptyAggregator:
        def __init__(self, _db):
            pass

        def aggregate_by_term(self, _product_id):
            return pd.DataFrame()

    class UnexpectedEngine:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("没有聚合结果时不应继续进入规则分析")

    monkeypatch.setattr(aggregator_module, "DataAggregator", EmptyAggregator)
    monkeypatch.setattr(engine_module, "RuleEngine", UnexpectedEngine)

    state = run_analysis(db, product_id)

    assert state["status"] == "warning"
    assert "不足以生成搜索词分析结果" in state["message"]
    assert state["terms_analyzed"] == 0
    assert state["results_saved"] == 0
    assert state["pending_reviews"] == 0
    assert state["can_retry"] is False


def test_run_analysis_returns_warning_when_engine_produces_no_suggestions(monkeypatch, db, product_id):
    """规则分析空跑时应返回 warning，而不是伪装成成功。"""
    import src.data.aggregator as aggregator_module
    import src.rules.engine as engine_module

    class NonEmptyAggregator:
        def __init__(self, _db):
            pass

        def aggregate_by_term(self, _product_id):
            return pd.DataFrame([
                {"term": "travel pillow", "clicks": 12, "spend": 8.5, "orders": 0}
            ])

    class EmptyEngine:
        def __init__(self, *_args, **_kwargs):
            pass

        def analyze(self, _df):
            return []

    monkeypatch.setattr(aggregator_module, "DataAggregator", NonEmptyAggregator)
    monkeypatch.setattr(engine_module, "RuleEngine", EmptyEngine)

    state = run_analysis(db, product_id)

    assert state["status"] == "warning"
    assert "没有生成可保存的建议" in state["message"]
    assert state["terms_analyzed"] == 1
    assert state["results_saved"] == 0
    assert state["pending_reviews"] == 0
    assert state["can_retry"] is False


def test_run_analysis_persists_snapshot_on_success(monkeypatch, db, product_id):
    """成功分析后应保存快照，供汇总页读取最近一次有效分析结果。"""
    import src.data.aggregator as aggregator_module
    import src.rules.engine as engine_module

    class NonEmptyAggregator:
        def __init__(self, _db):
            pass

        def aggregate_by_term(self, _product_id):
            return pd.DataFrame([
                {"term": "travel pillow", "clicks": 12, "spend": 8.5, "orders": 0, "sales": 0}
            ])

    class SnapshotEngine:
        def __init__(self, *_args, **_kwargs):
            pass

        def analyze(self, _df):
            return [
                AnalysisResult(
                    term="travel pillow",
                    term_type="keyword",
                    triggered_rule="高花费无订单",
                    suggested_action="否定精准",
                    action_type="negative_exact",
                    confidence=0.92,
                    needs_review=True,
                    data={"total_clicks": 12, "total_spend": 8.5, "total_orders": 0, "total_sales": 0},
                )
            ]

    monkeypatch.setattr(aggregator_module, "DataAggregator", NonEmptyAggregator)
    monkeypatch.setattr(engine_module, "RuleEngine", SnapshotEngine)

    state = run_analysis(db, product_id)
    snapshots = db.list_analysis_run_snapshots(product_id, limit=1)

    assert state["status"] == "success"
    assert state["results_saved"] == 1
    assert state["pending_reviews"] == 1
    assert len(snapshots) == 1
    assert snapshots[0]["run_source"] == "manual"
    assert snapshots[0]["summary"] == {
        "negative_count": 1,
        "manual_count": 0,
        "observe_count": 0,
        "conflict_count": 0,
    }
    assert snapshots[0]["rows"] == [
        {
            "term": "travel pillow",
            "normalized_term": "travel pillow",
            "term_type": "keyword",
            "action_type": "negative_exact",
            "suggested_action": "否定精准",
            "triggered_rule": "高花费无订单",
            "decision_source": "auto_suggestion",
            "clicks": 12.0,
            "orders": 0.0,
            "spend": 8.5,
            "sales": 0.0,
            "impressions": 0.0,
            "confidence": 0.92,
            "cvr": 0.0,
            "acos": 0.0,
        }
    ]


def test_run_analysis_warning_does_not_persist_snapshot(monkeypatch, db, product_id):
    """无建议 warning 不应污染最近一次有效分析快照。"""
    import src.data.aggregator as aggregator_module
    import src.rules.engine as engine_module

    class NonEmptyAggregator:
        def __init__(self, _db):
            pass

        def aggregate_by_term(self, _product_id):
            return pd.DataFrame([
                {"term": "travel pillow", "clicks": 12, "spend": 8.5, "orders": 0}
            ])

    class EmptyEngine:
        def __init__(self, *_args, **_kwargs):
            pass

        def analyze(self, _df):
            return []

    monkeypatch.setattr(aggregator_module, "DataAggregator", NonEmptyAggregator)
    monkeypatch.setattr(engine_module, "RuleEngine", EmptyEngine)

    state = run_analysis(db, product_id)

    assert state["status"] == "warning"
    assert db.list_analysis_run_snapshots(product_id, limit=5) == []


def test_clear_product_runtime_data_removes_analysis_snapshots(db, product_id, campaign_id):
    """清空运行数据时应一并删除最近一次分析快照，避免旧分析残留。"""
    _seed_minimal_search_term(db, campaign_id)
    db.save_analysis_run_snapshot(
        product_id=product_id,
        run_source="manual",
        summary={"negative": 1, "manual": 0, "conflict": 0},
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "clicks": 12,
                "orders": 0,
                "spend": 24.0,
                "sales": 0.0,
            }
        ],
    )

    clear_product_runtime_data(db, product_id)

    assert db.get_table_count("campaigns") == 0
    assert db.list_analysis_run_snapshots(product_id, limit=5) == []


def test_full_backup_export_includes_real_runtime_rows(db, product_id, campaign_id):
    """完整备份应包含可恢复的真实行数据，而不是只有计数摘要。"""
    _seed_minimal_search_term(db, campaign_id)
    search_term_id = db.execute("SELECT id FROM search_terms LIMIT 1").fetchone()["id"]
    analysis_result_id = db.execute(
        """
        INSERT INTO analysis_results (
            search_term_id, triggered_rule, suggested_action, action_type, confidence, ai_reasoning
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (search_term_id, "高点击无转化", "否定精准", "negative_exact", 0.9, "测试原因"),
    ).lastrowid
    db.execute(
        """
        INSERT INTO action_plans (analysis_result_id, action, status, notes)
        VALUES (?, ?, ?, ?)
        """,
        (analysis_result_id, "negate", "pending", "测试动作"),
    )
    db.execute(
        """
        INSERT INTO manual_reviews (
            product_id, term, term_type, reviewed, final_action, notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (product_id, "travel pillow", "keyword", 1, "negative_exact", "人工备注"),
    )
    db.save_analysis_run_snapshot(
        product_id=product_id,
        run_source="manual",
        summary={"negative": 1, "manual": 0, "conflict": 0},
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "clicks": 12,
                "orders": 0,
                "spend": 24.0,
                "sales": 0.0,
            }
        ],
    )
    db.commit()

    payload = build_full_backup_export_payload(db, product_id)
    backup = json.loads(payload["data"].decode("utf-8"))

    assert backup["export_type"] == "full_backup"
    assert len(backup["campaigns"]) == 1
    assert len(backup["search_terms"]) == 1
    assert len(backup["analysis_results"]) == 1
    assert len(backup["action_plans"]) == 1
    assert len(backup["manual_reviews"]) == 1
    assert len(backup["analysis_run_snapshots"]) == 1


def test_restore_full_backup_can_rebuild_product_runtime_data(db, product_id, campaign_id):
    """完整备份应能恢复搜索词、分析结果、审核记录与分析快照。"""
    _seed_minimal_search_term(db, campaign_id)
    search_term_id = db.execute("SELECT id FROM search_terms LIMIT 1").fetchone()["id"]
    analysis_result_id = db.execute(
        """
        INSERT INTO analysis_results (
            search_term_id, triggered_rule, suggested_action, action_type, confidence, ai_reasoning
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (search_term_id, "高点击无转化", "否定精准", "negative_exact", 0.9, "测试原因"),
    ).lastrowid
    db.execute(
        """
        INSERT INTO action_plans (analysis_result_id, action, status, notes)
        VALUES (?, ?, ?, ?)
        """,
        (analysis_result_id, "negate", "pending", "测试动作"),
    )
    db.execute(
        """
        INSERT INTO manual_reviews (
            product_id, term, term_type, reviewed, final_action, notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (product_id, "travel pillow", "keyword", 1, "negative_exact", "人工备注"),
    )
    db.save_analysis_run_snapshot(
        product_id=product_id,
        run_source="manual",
        summary={"negative": 1, "manual": 0, "conflict": 0},
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "clicks": 12,
                "orders": 0,
                "spend": 24.0,
                "sales": 0.0,
            }
        ],
    )
    db.commit()
    backup = json.loads(build_full_backup_export_payload(db, product_id)["data"].decode("utf-8"))

    clear_product_runtime_data(db, product_id)
    assert db.execute("SELECT COUNT(*) AS count FROM search_terms").fetchone()["count"] == 0

    restore_full_backup(db, backup, current_product_id=product_id, restore_as_new_product=False)

    assert db.execute("SELECT COUNT(*) AS count FROM campaigns").fetchone()["count"] == 1
    assert db.execute("SELECT COUNT(*) AS count FROM search_terms").fetchone()["count"] == 1
    assert db.execute("SELECT COUNT(*) AS count FROM analysis_results").fetchone()["count"] == 1
    assert db.execute("SELECT COUNT(*) AS count FROM action_plans").fetchone()["count"] == 1
    assert db.execute("SELECT COUNT(*) AS count FROM manual_reviews").fetchone()["count"] == 1
    assert len(db.list_analysis_run_snapshots(product_id, limit=5)) == 1


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


def test_build_snapshot_summary_rows_formats_latest_snapshot_for_summary_view():
    """最近一次有效分析快照应转换为汇总页可直接展示的数据结构。"""
    rows = _build_snapshot_summary_rows(
        [
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "decision_source": "auto_suggestion",
                "clicks": 12.0,
                "orders": 2.0,
                "spend": 8.5,
                "sales": 40.0,
            }
        ]
    )

    assert rows == [
        {
            "term": "travel pillow",
            "term_type": "keyword",
            "asin_identifiers": [],
            "asin_count": 0,
            "triggered_rule": "高点击无转化",
            "suggested_action": "否定精准",
            "action_type": "negative_exact",
            "action_detail": "否定精准",
            "confidence": 1.0,
            "reviewed": False,
            "has_conflict": False,
            "clicks": 12,
            "orders": 2,
            "spend": 8.5,
            "sales": 40.0,
            "cvr": 2 / 12,
            "acos": 8.5 / 40.0,
        }
    ]


def test_build_snapshot_summary_rows_collapses_conflicts_into_single_summary_row():
    """同一搜索词在最近一次快照中存在多种动作时，应折叠为单条冲突结论。"""
    rows = _build_snapshot_summary_rows(
        [
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "规则A",
                "decision_source": "auto_suggestion",
                "clicks": 9.0,
                "orders": 0.0,
                "spend": 4.0,
                "sales": 0.0,
            },
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "manual_keyword",
                "suggested_action": "加入手动精准",
                "triggered_rule": "规则B",
                "decision_source": "manual_review",
                "clicks": 5.0,
                "orders": 1.0,
                "spend": 3.0,
                "sales": 18.0,
            },
        ]
    )

    assert len(rows) == 1
    assert rows[0]["term"] == "travel pillow"
    assert rows[0]["action_type"] == "conflict"
    assert rows[0]["suggested_action"] == "跨快照分歧"
    assert rows[0]["triggered_rule"] == "最近一次有效分析（跨快照分歧）"
    assert rows[0]["has_conflict"] is True
    assert rows[0]["reviewed"] is True
    assert rows[0]["clicks"] == 14
    assert rows[0]["orders"] == 1


def test_build_latest_snapshot_summary_rows_reads_latest_saved_snapshot(db, product_id):
    """汇总页应优先读取最近一次已保存的有效分析快照。"""
    db.save_analysis_run_snapshot(
        product_id,
        snapshot_rows=[
            {
                "term": "travel pillow",
                "normalized_term": "travel pillow",
                "term_type": "keyword",
                "action_type": "observe",
                "suggested_action": "继续观察",
                "triggered_rule": "观察规则",
                "decision_source": "manual_review",
                "clicks": 7.0,
                "orders": 1.0,
                "spend": 6.0,
                "sales": 25.0,
            }
        ],
        run_source="manual",
        summary={
            "negative_count": 0,
            "manual_count": 0,
            "observe_count": 1,
            "conflict_count": 0,
        },
    )

    rows = _build_latest_snapshot_summary_rows(db, product_id)

    assert len(rows) == 1
    assert rows[0]["term"] == "travel pillow"
    assert rows[0]["action_type"] == "observe"
    assert rows[0]["action_detail"] == "观察"
    assert rows[0]["reviewed"] is True
    assert rows[0]["clicks"] == 7
    assert rows[0]["orders"] == 1


def test_build_analysis_run_snapshot_rows_preserves_campaign_dimensions():
    """成功分析快照应保留广告组与自动处理维度，供后续页面复用。"""

    class _CampaignResult:
        term = "travel pillow"
        term_type = "keyword"
        action_type = "negative_exact"
        suggested_action = "否定精准"
        triggered_rule = "高点击无转化"
        campaign_id = "cmp-001"
        campaign_name = "Brand Exact"
        auto_action = "negate"
        clicks = 12
        orders = 0
        spend = 18.5
        sales = 0.0
        confidence = 0.9
        cvr = 0.0
        acos = 0.0
        data = {}

    rows = build_analysis_run_snapshot_rows([_CampaignResult()])

    assert rows == [
        {
            "term": "travel pillow",
            "normalized_term": "travel pillow",
            "term_type": "keyword",
            "action_type": "negative_exact",
            "suggested_action": "否定精准",
            "triggered_rule": "高点击无转化",
            "decision_source": "auto_suggestion",
            "clicks": 12.0,
            "orders": 0.0,
            "spend": 18.5,
            "sales": 0.0,
            "impressions": 0.0,
            "confidence": 0.9,
            "cvr": 0.0,
            "acos": 0.0,
            "campaign_id": "cmp-001",
            "campaign_name": "Brand Exact",
            "auto_action": "negate",
        }
    ]


def test_build_snapshot_campaign_rows_formats_latest_snapshot_for_campaign_view():
    """最近一次有效快照应转换为按活动页可直接展示的数据结构。"""
    rows = _build_snapshot_campaign_rows(
        [
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "campaign_id": "cmp-001",
                "campaign_name": "Brand Exact",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "clicks": 12.0,
                "orders": 1.0,
                "spend": 18.5,
                "sales": 42.0,
                "confidence": 0.8,
                "cvr": 1 / 12,
                "acos": 18.5 / 42.0,
            }
        ]
    )

    assert rows == [
        {
            "term": "travel pillow",
            "term_type": "keyword",
            "campaign_id": "cmp-001",
            "campaign_name": "Brand Exact",
            "triggered_rule": "高点击无转化",
            "suggested_action": "否定精准",
            "auto_action": "negate",
            "action_type": "negative_exact",
            "confidence": 0.8,
            "clicks": 12,
            "orders": 1,
            "spend": 18.5,
            "sales": 42.0,
            "cvr": 1 / 12,
            "acos": 18.5 / 42.0,
        }
    ]


def test_build_latest_snapshot_campaign_rows_reads_latest_saved_snapshot(db, product_id):
    """按活动页应优先读取最近一次包含广告组维度的有效快照。"""
    db.save_analysis_run_snapshot(
        product_id,
        snapshot_rows=[{"term": "summary only", "term_type": "keyword"}],
        run_source="manual",
        summary={"negative_count": 0},
    )
    db.save_analysis_run_snapshot(
        product_id,
        snapshot_rows=[
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "campaign_id": "cmp-001",
                "campaign_name": "Brand Exact",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "auto_action": "negate",
                "clicks": 12.0,
                "orders": 1.0,
                "spend": 18.5,
                "sales": 42.0,
                "confidence": 0.8,
                "cvr": 1 / 12,
                "acos": 18.5 / 42.0,
            }
        ],
        run_source="manual",
        summary={"negative_count": 1},
    )

    rows = _build_latest_snapshot_campaign_rows(db, product_id)

    assert rows is not None
    assert rows[0]["campaign_id"] == "cmp-001"
    assert rows[0]["campaign_name"] == "Brand Exact"
    assert rows[0]["auto_action"] == "negate"


def test_build_snapshot_asin_rows_formats_latest_snapshot_for_asin_view():
    """最近一次有效快照应转换为按 ASIN 页可直接展示的数据结构。"""
    rows = _build_snapshot_asin_rows(
        [
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "asin_identifier": "B0TESTASIN",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "clicks": 12.0,
                "orders": 1.0,
                "spend": 18.5,
                "sales": 42.0,
                "confidence": 0.8,
                "cvr": 1 / 12,
                "acos": 18.5 / 42.0,
            }
        ]
    )

    assert rows == [
        {
            "term": "travel pillow",
            "term_type": "keyword",
            "asin_identifier": "B0TESTASIN",
            "triggered_rule": "高点击无转化",
            "suggested_action": "否定精准",
            "auto_action": "negate",
            "action_type": "negative_exact",
            "confidence": 0.8,
            "clicks": 12,
            "orders": 1,
            "spend": 18.5,
            "sales": 42.0,
            "cvr": 1 / 12,
            "acos": 18.5 / 42.0,
        }
    ]


def test_build_latest_snapshot_asin_rows_reads_latest_saved_snapshot(db, product_id):
    """按 ASIN 页应优先读取最近一次包含 ASIN 维度的有效快照。"""
    db.save_analysis_run_snapshot(
        product_id,
        snapshot_rows=[{"term": "summary only", "term_type": "keyword"}],
        run_source="manual",
        summary={"negative_count": 0},
    )
    db.save_analysis_run_snapshot(
        product_id,
        snapshot_rows=[
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "asin_identifier": "B0TESTASIN",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高点击无转化",
                "auto_action": "negate",
                "clicks": 12.0,
                "orders": 1.0,
                "spend": 18.5,
                "sales": 42.0,
                "confidence": 0.8,
                "cvr": 1 / 12,
                "acos": 18.5 / 42.0,
            }
        ],
        run_source="manual",
        summary={"negative_count": 1},
    )

    rows = _build_latest_snapshot_asin_rows(db, product_id)

    assert rows is not None
    assert rows[0]["asin_identifier"] == "B0TESTASIN"
    assert rows[0]["auto_action"] == "negate"


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


def test_actions_workbench_meta_uses_snapshot_fallback_counts_without_truth():
    """操作清单页在没有人工真值时，也应能透出最近一次有效快照的执行数量。"""
    meta = _build_actions_workbench_meta(
        "桌面验收产品",
        {},
        {"conflict_count": 4},
        fallback_counts={"negative": 12, "manual": 5, "conflict": 4},
    )

    assert meta["chips"] == [
        "可直接否定 12 项",
        "可直接投放 5 项",
        "待人工拍板 4 项",
    ]


def test_build_snapshot_action_buckets_classifies_latest_snapshot_rows():
    """最近一次有效快照应被稳定拆成操作清单需要的各个分桶。"""
    buckets = _build_snapshot_action_buckets(
        [
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高花费低转化否定精准",
                "clicks": 12,
                "orders": 0,
                "spend": 18.5,
                "sales": 0,
            },
            {
                "term": "travel pillow memory foam",
                "term_type": "keyword",
                "action_type": "negative_phrase",
                "suggested_action": "否定词组",
                "triggered_rule": "高点击低订单否定词组",
            },
            {
                "term": "B0NEG12345",
                "term_type": "asin",
                "action_type": "negative_exact",
                "suggested_action": "商品否定",
                "triggered_rule": "高花费商品否定",
            },
            {
                "term": "best neck pillow",
                "term_type": "keyword",
                "action_type": "manual_exact",
                "suggested_action": "手动精准",
                "triggered_rule": "高转化词移到精准",
            },
            {
                "term": "B0MANUAL99",
                "term_type": "asin",
                "action_type": "manual_product",
                "suggested_action": "手动商品定位",
                "triggered_rule": "高转化ASIN拉商品定位",
            },
            {
                "term": "conflicted keyword",
                "term_type": "keyword",
                "action_type": "conflict",
                "suggested_action": "跨快照分歧",
                "triggered_rule": "最近一次分析冲突",
            },
        ]
    )

    assert [item["term"] for item in buckets["negative_keyword_exact"]] == [
        "travel pillow"
    ]
    assert [item["term"] for item in buckets["negative_keyword_phrase"]] == [
        "travel pillow memory foam"
    ]
    assert [item["term"] for item in buckets["negative_asin"]] == ["B0NEG12345"]
    assert [item["term"] for item in buckets["manual_keywords"]] == [
        "best neck pillow"
    ]
    assert [item["term"] for item in buckets["manual_products"]] == ["B0MANUAL99"]
    assert [item["term"] for item in buckets["cross_asin_conflicts"]] == [
        "conflicted keyword"
    ]
    assert buckets["manual_keywords"][0]["auto_action"] == "keep"


def test_get_latest_snapshot_action_context_reads_latest_saved_snapshot(
    db, product_id
):
    """操作清单页应优先读取最近一次有效快照，避免继续实时重算。"""
    db.save_analysis_run_snapshot(
        product_id,
        snapshot_rows=[],
        run_source="manual",
        summary={"negative": 0, "manual": 0, "conflict": 0},
    )
    db.save_analysis_run_snapshot(
        product_id,
        snapshot_rows=[
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高花费低转化否定精准",
                "clicks": 7,
                "orders": 0,
                "spend": 12.3,
                "sales": 0,
            },
            {
                "term": "best neck pillow",
                "term_type": "keyword",
                "action_type": "manual_exact",
                "suggested_action": "手动精准",
                "triggered_rule": "高转化词移到精准",
            },
        ],
        run_source="manual",
        summary={"negative": 1, "manual": 1, "conflict": 0},
    )

    context = _get_latest_snapshot_action_context(db, product_id)

    assert context is not None
    assert context["counts"] == {"negative": 1, "manual": 1, "conflict": 0}
    assert context["pending_stats"]["conflict_count"] == 0
    assert [item["term"] for item in context["buckets"]["negative_keyword_exact"]] == [
        "travel pillow"
    ]
    assert [item["term"] for item in context["buckets"]["manual_keywords"]] == [
        "best neck pillow"
    ]


def test_get_export_results_prefers_latest_snapshot_when_truth_missing(
    monkeypatch, db, product_id
):
    """没有人工真值时，导出应优先复用最近一次有效快照，而不是退回实时分析。"""
    db.save_analysis_run_snapshot(
        product_id,
        snapshot_rows=[
            {
                "term": "travel pillow",
                "term_type": "keyword",
                "action_type": "negative_exact",
                "suggested_action": "否定精准",
                "triggered_rule": "高花费低转化否定精准",
                "clicks": 6,
                "orders": 0,
                "spend": 9.8,
                "sales": 0,
            }
        ],
        run_source="manual",
        summary={"negative": 1, "manual": 0, "conflict": 0},
    )

    monkeypatch.setattr(
        "src.ui.pages.actions.analyze_search_terms",
        lambda *_args, **_kwargs: pytest.fail("不应在存在有效快照时回退到实时分析"),
    )

    results = _get_export_results(db, product_id, "negative")

    assert len(results) == 1
    assert results[0].term == "travel pillow"
    assert results[0].action_type == "negative_exact"


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


