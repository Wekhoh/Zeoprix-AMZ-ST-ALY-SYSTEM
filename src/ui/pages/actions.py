"""
操作清单页面
展示待执行的否词和手动投放操作
"""

from html import escape

import pandas as pd
import streamlit as st

from src.ai.copilot import build_actions_ai_brief
from src.analysis.truth_replay import (
    action_type_to_auto_action,
    get_truth_first_action_buckets,
    get_truth_first_pending_stats,
)
from src.config.logger import get_logger
from src.rules.engine import AnalysisResult, analyze_search_terms

logger = get_logger(__name__)


ACTIONS_PAGE_CSS = """
<style>
.actions-hero {
    padding: 1.6rem 1.8rem;
    border-radius: 26px;
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,255,0.96) 100%);
    border: 1px solid rgba(59, 91, 219, 0.10);
    box-shadow: 0 16px 38px rgba(15, 23, 42, 0.06);
    margin-bottom: 1.35rem;
}
.actions-hero__eyebrow,
.review-hero__eyebrow {
    display: inline-flex;
    align-items: center;
    padding: 0.3rem 0.72rem;
    border-radius: 999px;
    background: rgba(59, 91, 219, 0.08);
    color: #3b5bdb;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    margin-bottom: 0.95rem;
}
.actions-hero h1,
.review-hero h1 {
    margin: 0;
    font-size: 2.05rem;
    line-height: 1.1;
    color: #0f172a;
}
.actions-hero p,
.review-hero p {
    margin: 0.85rem 0 0;
    color: #52607a;
    font-size: 1rem;
    line-height: 1.72;
}
.actions-hero__chips,
.review-hero__chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.7rem;
    margin-top: 1.1rem;
}
.actions-hero__chip,
.review-hero__chip {
    padding: 0.54rem 0.88rem;
    border-radius: 999px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    background: rgba(255,255,255,0.82);
    color: #334155;
    font-size: 0.9rem;
    font-weight: 600;
}
.actions-section-note,
.review-section-note {
    margin: 0.15rem 0 1rem;
    color: #64748b;
    font-size: 0.95rem;
    line-height: 1.7;
}
.review-completion {
    padding: 1.8rem;
    border-radius: 24px;
    background: linear-gradient(180deg, rgba(240, 253, 244, 0.92) 0%, rgba(236, 253, 245, 0.98) 100%);
    border: 1px solid rgba(34, 197, 94, 0.18);
    box-shadow: 0 14px 34px rgba(34, 197, 94, 0.08);
    margin-top: 1rem;
}
.review-completion__badge {
    display: inline-flex;
    align-items: center;
    padding: 0.32rem 0.72rem;
    border-radius: 999px;
    background: rgba(34, 197, 94, 0.12);
    color: #15803d;
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 0.9rem;
}
.review-completion h3 {
    margin: 0;
    color: #14532d;
    font-size: 1.45rem;
}
.review-completion p {
    margin: 0.7rem 0 0;
    color: #166534;
    font-size: 0.98rem;
    line-height: 1.75;
}
</style>
"""


def _resolve_actions_role_context(db, product_id: int) -> dict[str, str | int]:
    """解析操作清单页当前用户与工作区角色上下文。"""
    current_user_id = st.session_state.get("current_user_id")
    current_user = (
        db.get_user(user_id=current_user_id) if current_user_id is not None else None
    )
    if current_user is None:
        current_user = db.get_or_create_local_owner()

    current_role = db.get_workspace_role(product_id, current_user["id"]) or "viewer"
    return {
        "current_user_name": current_user.get("display_name") or current_user["email"],
        "current_role": current_role,
        "current_user_id": current_user["id"],
    }


def _build_actions_access_meta(current_role: str) -> dict[str, object]:
    """构建操作清单页角色门控摘要。"""
    can_export = current_role in {"admin", "editor"}
    return {
        "title": "当前执行权限",
        "description": "操作清单会沉淀成实际执行素材。管理员和编辑者可以导出否词与手动投放清单，查看者保留只读浏览，避免把未确认动作直接带出工作区。",
        "chips": [
            f"当前角色：{current_role}",
            "可导出执行清单" if can_export else "只读查看执行建议",
        ],
        "can_export": can_export,
        "blocked_message": "当前角色只能查看操作建议，导出执行清单需要管理员或编辑者权限。",
    }


def _build_actions_workbench_meta(
    product_name: str,
    truth_buckets: dict | None,
    pending_stats: dict | None = None,
    fallback_counts: dict[str, int] | None = None,
) -> dict[str, str | list[str]]:
    """构建操作清单页的工作台文案与核心数量。"""
    counts = {
        "negative": 0,
        "manual": 0,
        "conflict": 0,
    }
    if fallback_counts:
        counts.update(
            {
                "negative": int(fallback_counts.get("negative", counts["negative"])),
                "manual": int(fallback_counts.get("manual", counts["manual"])),
                "conflict": int(fallback_counts.get("conflict", counts["conflict"])),
            }
        )
    if truth_buckets:
        counts["negative"] = sum(
            len(truth_buckets.get(key, []))
            for key in ("negative_keyword_exact", "negative_keyword_phrase", "negative_asin")
        )
        counts["manual"] = sum(
            len(truth_buckets.get(key, []))
            for key in ("manual_keywords", "manual_products")
        )
        counts["conflict"] = len(truth_buckets.get("cross_asin_conflicts", []))
    if pending_stats:
        counts["conflict"] = pending_stats.get("conflict_count", counts["conflict"])

    return {
        "eyebrow": "执行面板",
        "title": "操作清单",
        "description": "先处理可直接执行的否词和投放动作，再回头处理需要人工拍板的跨ASIN分歧。",
        "product_label": product_name,
        "chips": [
            f"可直接否定 {counts['negative']} 项",
            f"可直接投放 {counts['manual']} 项",
            f"待人工拍板 {counts['conflict']} 项",
        ],
    }


def _build_snapshot_action_buckets(
    snapshot_rows: list[dict] | None,
) -> dict[str, list[dict[str, object]]]:
    """将最近一次有效分析快照转换为操作清单分桶。"""
    buckets: dict[str, list[dict[str, object]]] = {
        "negative_keyword_exact": [],
        "negative_keyword_phrase": [],
        "negative_asin": [],
        "manual_keywords": [],
        "manual_products": [],
        "cross_asin_conflicts": [],
    }
    if not snapshot_rows:
        return buckets

    for row in snapshot_rows:
        action_type = str(row.get("action_type") or "")
        term = row.get("term")
        term_type = row.get("term_type")
        if not term or not action_type:
            continue

        item = {
            "term": term,
            "term_type": term_type,
            "triggered_rule": row.get("triggered_rule") or "规则分析快照",
            "suggested_action": row.get("suggested_action") or "观察",
            "action_type": action_type,
            "auto_action": row.get("auto_action")
            or action_type_to_auto_action(action_type),
            "confidence": float(row.get("confidence") or 1.0),
            "spend": float(row.get("spend") or 0),
            "clicks": int(row.get("clicks") or 0),
            "orders": int(row.get("orders") or 0),
            "sales": float(row.get("sales") or 0),
        }

        if action_type == "conflict":
            buckets["cross_asin_conflicts"].append(item)
            continue

        if action_type.startswith("negative"):
            if term_type == "asin":
                buckets["negative_asin"].append(item)
            elif action_type == "negative_phrase":
                buckets["negative_keyword_phrase"].append(item)
            else:
                buckets["negative_keyword_exact"].append(item)
            continue

        if action_type.startswith("manual"):
            if term_type == "asin":
                buckets["manual_products"].append(item)
            else:
                buckets["manual_keywords"].append(item)

    return buckets


def _build_snapshot_pending_stats(snapshot_summary: dict | None) -> dict[str, int]:
    """基于最近一次有效快照的 summary 生成待处理统计。"""
    snapshot_summary = snapshot_summary or {}
    return {
        "negative_count": int(snapshot_summary.get("negative", 0) or 0),
        "manual_count": int(snapshot_summary.get("manual", 0) or 0),
        "conflict_count": int(snapshot_summary.get("conflict", 0) or 0),
        "ai_pending_count": 0,
        "review_pending_count": 0,
    }


def _get_latest_snapshot_action_context(
    db,
    product_id: int,
) -> dict[str, object] | None:
    """读取最近一次有效分析快照，为操作清单提供统一结果源。"""
    for snapshot in db.list_analysis_run_snapshots(product_id, limit=20):
        snapshot_rows = snapshot.get("rows") or []
        if not snapshot_rows:
            continue

        buckets = _build_snapshot_action_buckets(snapshot_rows)
        summary = snapshot.get("summary") or {}
        counts = {
            "negative": int(summary.get("negative", 0) or 0),
            "manual": int(summary.get("manual", 0) or 0),
            "conflict": int(summary.get("conflict", 0) or 0),
        }
        if not any(counts.values()):
            counts["negative"] = sum(
                len(buckets[key])
                for key in (
                    "negative_keyword_exact",
                    "negative_keyword_phrase",
                    "negative_asin",
                )
            )
            counts["manual"] = len(buckets["manual_keywords"]) + len(
                buckets["manual_products"]
            )
            counts["conflict"] = len(buckets["cross_asin_conflicts"])

        return {
            "buckets": buckets,
            "counts": counts,
            "pending_stats": _build_snapshot_pending_stats(summary or counts),
            "snapshot": snapshot,
        }

    return None


def _render_actions_ai_brief_card(
    *,
    product_name: str,
    action_buckets: dict[str, list[dict[str, object]]],
    counts: dict[str, int],
    context_label: str,
) -> None:
    """渲染操作清单页的 AI 执行摘要卡。"""
    brief = build_actions_ai_brief(
        {
            "product_name": product_name,
            "counts": counts,
            "context_label": context_label,
            "buckets": action_buckets,
        }
    )
    st.markdown(
        f"""
        <section class="ai-brief-card">
            <div class="ai-brief-card__eyebrow">AI 执行说明</div>
            <h3 class="ai-brief-card__headline">{escape(str(brief.get('headline') or 'AI 已生成执行摘要。'))}</h3>
            <div class="ai-brief-card__context">{escape(str(brief.get('context_label') or context_label))}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    bullets = [
        str(item).strip()
        for item in brief.get("bullets") or []
        if str(item).strip()
    ]
    if bullets:
        st.markdown("**执行摘要**")
        for item in bullets:
            st.markdown(f"- {item}")

    evidence_items = [item for item in (brief.get("evidence") or []) if item]
    if evidence_items:
        st.markdown("**当前证据**")
        for item in evidence_items:
            term = str(item.get("term") or "未命名词").strip()
            rule = str(item.get("triggered_rule") or "规则分析").strip()
            action = str(
                item.get("suggested_action") or item.get("action_type") or "观察"
            ).strip()
            spend = float(item.get("spend") or 0)
            st.markdown(
                f"- **{term}** · 规则：{rule} · 建议：{action} · 花费：${spend:.2f}"
            )

    next_actions = [
        str(item).strip()
        for item in brief.get("recommended_next_actions") or []
        if str(item).strip()
    ]
    if next_actions:
        st.markdown("**下一步建议**")
        for item in next_actions:
            st.markdown(f"- {item}")

    draft_payload = {
        str(key).strip(): str(value).strip()
        for key, value in (brief.get("draft_payload") or {}).items()
        if str(key).strip() and str(value).strip()
    }
    if draft_payload:
        st.markdown("**执行草稿**")
        draft_labels = {
            "boss_summary": "老板汇报摘要",
            "execution_note": "执行备注",
            "handoff_note": "交接提醒",
            "priority_plan": "优先动作草稿",
            "campaign_focus_note": "活动复盘备注",
            "budget_shift_note": "预算调整备注",
            "variant_focus_note": "变体归因备注",
            "landing_page_note": "页面承接备注",
            "review_decision_note": "审核决策备注",
            "risk_note": "风险提示",
            "data_quality_note": "数据质量备注",
            "analysis_next_step": "下一步建议草稿",
            "import_readout": "导入摘要草稿",
            "negative_batch_note": "批量否词说明",
            "manual_batch_note": "批量手动投放说明",
            "conflict_resolution_note": "分歧词处理提示",
        }
        for draft_key, draft_value in draft_payload.items():
            st.text_area(
                draft_labels.get(draft_key, draft_key.replace("_", " ").title()),
                value=draft_value,
                height=96,
                key=f"actions_ai_brief_draft_{draft_key}",
            )

    prompts = [
        str(item).strip()
        for item in brief.get("follow_up_prompts") or []
        if str(item).strip()
    ]
    if prompts:
        st.markdown("**继续追问**")
        columns = st.columns(min(2, len(prompts)))
        for idx, prompt in enumerate(prompts):
            with columns[idx % len(columns)]:
                if st.button(
                    prompt,
                    key=f"actions_ai_brief_prompt_{idx}",
                    width="stretch",
                ):
                    from src.app import _queue_ai_message

                    if _queue_ai_message(prompt, source_label="操作清单 AI 执行说明"):
                        st.rerun()


def _build_export_results_from_bucket_items(
    bucket_items: list[dict[str, object]],
) -> list[AnalysisResult]:
    """将页面桶内条目转换为导出器需要的 AnalysisResult。"""
    export_results: list[AnalysisResult] = []
    for item in bucket_items:
        export_results.append(
            AnalysisResult(
                term=str(item["term"]),
                term_type=str(item["term_type"]),
                triggered_rule=str(item.get("triggered_rule") or "规则分析快照"),
                suggested_action=str(item.get("suggested_action") or "观察"),
                action_type=str(item.get("action_type") or "observe"),
                confidence=float(item.get("confidence") or 1.0),
                need_ai_judgment=False,
                data={
                    "total_spend": float(item.get("spend") or 0),
                    "total_clicks": int(item.get("clicks") or 0),
                    "total_orders": int(item.get("orders") or 0),
                    "total_sales": float(item.get("sales") or 0),
                },
            )
        )
    return export_results


def _get_export_results(db, product_id: int, export_kind: str) -> list[AnalysisResult]:
    """返回与页面 truth bucket 一致的导出结果。"""
    truth_buckets = get_truth_first_action_buckets(db, product_id)
    if truth_buckets is None:
        snapshot_context = _get_latest_snapshot_action_context(db, product_id)
        if snapshot_context is not None:
            truth_buckets = snapshot_context["buckets"]
        else:
            results = analyze_search_terms(db, product_id)
            if export_kind == "negative":
                return [
                    r
                    for r in results
                    if r.action_type and r.action_type.startswith("negative")
                ]
            if export_kind == "manual":
                return [
                    r
                    for r in results
                    if r.action_type and r.action_type.startswith("manual")
                ]
            return results

    bucket_groups = {
        "negative": (
            "negative_keyword_exact",
            "negative_keyword_phrase",
            "negative_asin",
        ),
        "manual": ("manual_keywords", "manual_products"),
    }
    selected_keys = bucket_groups.get(export_kind, ())
    bucket_items = [
        item
        for bucket_key in selected_keys
        for item in truth_buckets.get(bucket_key, [])
    ]
    return _build_export_results_from_bucket_items(bucket_items)


def _get_export_payload(db, product_id: int, export_kind: str, export_format: str):
    """返回页面可直接下载的导出载荷。"""
    from src.export.exporter import ReportExporter

    results = _get_export_results(db, product_id, export_kind=export_kind)
    if not results:
        return None

    exporter = ReportExporter()
    if export_kind == "negative" and export_format == "xlsx":
        payload = exporter.export_negative_keywords_bytes(results)
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif export_kind == "negative" and export_format == "csv":
        payload = exporter.export_to_csv_bytes(results, result_type="negative")
        mime = "text/csv"
    elif export_kind == "manual" and export_format == "xlsx":
        payload = exporter.export_manual_keywords_bytes(results)
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise ValueError(f"不支持的导出类型: {export_kind}/{export_format}")

    if payload is None:
        return None

    file_bytes, file_name = payload
    return {"data": file_bytes, "file_name": file_name, "mime": mime}


def render_actions():
    """渲染操作清单页面"""
    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    if not product_id:
        st.warning("请先选择产品")
        return

    # 获取产品信息
    product = db.get_product(product_id)
    product_name = product.get("name", "未知产品") if product else "未知产品"
    truth_buckets = get_truth_first_action_buckets(db, product_id)
    pending_stats = get_truth_first_pending_stats(db, product_id)
    snapshot_context = None
    fallback_counts = None
    action_buckets = truth_buckets or {}
    if truth_buckets is None:
        snapshot_context = _get_latest_snapshot_action_context(db, product_id)
        if snapshot_context is not None:
            action_buckets = snapshot_context["buckets"]
            pending_stats = snapshot_context["pending_stats"]
            fallback_counts = snapshot_context["counts"]

    meta = _build_actions_workbench_meta(
        product_name,
        action_buckets,
        pending_stats,
        fallback_counts=fallback_counts,
    )
    access_context = _resolve_actions_role_context(db, product_id)
    access_meta = _build_actions_access_meta(access_context["current_role"])

    st.markdown(ACTIONS_PAGE_CSS, unsafe_allow_html=True)
    chips_html = "".join(
        f'<div class="actions-hero__chip">{escape(chip)}</div>' for chip in meta["chips"]
    )
    st.markdown(
        f"""
        <section class="actions-hero">
            <div class="actions-hero__eyebrow">{escape(meta["eyebrow"])}</div>
            <h1>{escape(meta["title"])}</h1>
            <p>{escape(meta["product_label"])} · {escape(meta["description"])}</p>
            <div class="actions-hero__chips">{chips_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    access_chips_html = "".join(
        f'<div class="actions-hero__chip">{escape(str(chip))}</div>'
        for chip in access_meta["chips"]
    )
    st.markdown(
        f"""
        <section class="actions-hero" style="padding: 1rem 1.1rem; margin-top: -0.3rem;">
            <div class="actions-hero__eyebrow">{escape(str(access_meta["title"]))}</div>
            <p>{escape(str(access_meta["description"]))}</p>
            <div class="actions-hero__chips">{access_chips_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if not access_meta["can_export"]:
        st.info(str(access_meta["blocked_message"]))

    effective_counts = fallback_counts or {
        "negative": sum(
            len(action_buckets.get(key, []))
            for key in (
                "negative_keyword_exact",
                "negative_keyword_phrase",
                "negative_asin",
            )
        ),
        "manual": sum(
            len(action_buckets.get(key, []))
            for key in ("manual_keywords", "manual_products")
        ),
        "conflict": int((pending_stats or {}).get("conflict_count", 0) or 0),
    }
    context_label = (
        f"当前产品：{product_name} · 上下文：人工校准结果"
        if truth_buckets is not None
        else f"当前产品：{product_name} · 上下文：最近一次分析结果"
    )
    _render_actions_ai_brief_card(
        product_name=product_name,
        action_buckets=action_buckets,
        counts=effective_counts,
        context_label=context_label,
    )

    # 标签页切换
    tab1, tab2, tab3 = st.tabs(["否词操作", "手动投放", "操作历史"])

    with tab1:
        render_negative_actions(
            db,
            product_id,
            can_export=bool(access_meta["can_export"]),
            action_buckets=action_buckets
            if (truth_buckets is not None or snapshot_context)
            else None,
        )

    with tab2:
        render_manual_actions(
            db,
            product_id,
            can_export=bool(access_meta["can_export"]),
            action_buckets=action_buckets
            if (truth_buckets is not None or snapshot_context)
            else None,
        )

    with tab3:
        render_action_history(db, product_id)


def render_negative_actions(
    db,
    product_id: int,
    *,
    can_export: bool = True,
    action_buckets: dict[str, list[dict[str, object]]] | None = None,
):
    """渲染否词操作清单"""
    st.write("### 待否定关键词")
    st.markdown(
        '<p class="actions-section-note">只保留已经可以直接执行的否词项；跨ASIN分歧不会混进这里，避免复制到后台后再返工。</p>',
        unsafe_allow_html=True,
    )

    if action_buckets is not None:
        exact_negatives = action_buckets["negative_keyword_exact"]
        phrase_negatives = action_buckets["negative_keyword_phrase"]
        product_negatives = action_buckets["negative_asin"]
    else:
        # 使用实时分析结果（与搜索词分析页面保持一致）
        analysis_results = analyze_search_terms(db, product_id)
        if not analysis_results:
            st.info("暂无待否定的关键词")
            return

        # 转换为dict格式以兼容现有代码
        negative_items = []
        for r in analysis_results:
            if r.action_type and r.action_type.startswith("negative"):
                negative_items.append(
                    {
                        "term": r.term,
                        "term_type": r.term_type,
                        "triggered_rule": r.triggered_rule,
                        "suggested_action": r.suggested_action,
                        "action_type": r.action_type,
                        "confidence": r.confidence,
                        "spend": r.data.get("total_spend", r.data.get("spend", 0)),
                        "clicks": r.data.get("total_clicks", r.data.get("clicks", 0)),
                        "orders": r.data.get("total_orders", r.data.get("orders", 0)),
                        "sales": r.data.get("total_sales", r.data.get("sales", 0)),
                    }
                )

        if not negative_items:
            st.info("暂无待否定的关键词")
            return

        exact_negatives = []
        phrase_negatives = []
        product_negatives = []
        for item in negative_items:
            if item.get("term_type") == "asin":
                product_negatives.append(item)
            elif "精准" in item.get("suggested_action", "") or "精确" in item.get(
                "suggested_action", ""
            ):
                exact_negatives.append(item)
            else:
                phrase_negatives.append(item)

    if not exact_negatives and not phrase_negatives and not product_negatives:
        st.info("暂无待否定的关键词")
        return

    # 关键词精确否定
    if exact_negatives:
        st.write("#### 关键词精确否定")
        df_exact = pd.DataFrame(
            [
                {
                    "关键词": item["term"],
                    "触发规则": item["triggered_rule"],
                    "花费": f"${item.get('spend', 0):.2f}",
                    "点击": item.get("clicks", 0),
                    "订单": item.get("orders", 0),
                }
                for item in exact_negatives
            ]
        )
        st.dataframe(df_exact, width="stretch", hide_index=True)

        # 复制按钮
        keywords_text = "\n".join([item["term"] for item in exact_negatives])
        st.text_area(
            "精确否定词列表（复制到亚马逊后台）",
            value=keywords_text,
            height=100,
            key="exact_negative_list",
        )

    # 关键词短语否定
    if phrase_negatives:
        st.write("#### 关键词短语否定")
        df_phrase = pd.DataFrame(
            [
                {
                    "关键词": item["term"],
                    "触发规则": item["triggered_rule"],
                    "花费": f"${item.get('spend', 0):.2f}",
                    "点击": item.get("clicks", 0),
                    "订单": item.get("orders", 0),
                }
                for item in phrase_negatives
            ]
        )
        st.dataframe(df_phrase, width="stretch", hide_index=True)

        keywords_text = "\n".join([item["term"] for item in phrase_negatives])
        st.text_area(
            "短语否定词列表（复制到亚马逊后台）",
            value=keywords_text,
            height=100,
            key="phrase_negative_list",
        )

    # ASIN商品否定
    if product_negatives:
        st.write("#### ASIN商品否定")
        df_product = pd.DataFrame(
            [
                {
                    "ASIN": item["term"],
                    "触发规则": item["triggered_rule"],
                    "花费": f"${item.get('spend', 0):.2f}",
                    "点击": item.get("clicks", 0),
                    "订单": item.get("orders", 0),
                }
                for item in product_negatives
            ]
        )
        st.dataframe(df_product, width="stretch", hide_index=True)

        asins_text = "\n".join([item["term"] for item in product_negatives])
        st.text_area(
            "商品否定ASIN列表（复制到亚马逊后台）",
            value=asins_text,
            height=100,
            key="product_negative_list",
        )

    st.divider()

    # 导出按钮
    col1, col2 = st.columns(2)
    negative_excel_payload = _get_export_payload(db, product_id, "negative", "xlsx")
    negative_csv_payload = _get_export_payload(db, product_id, "negative", "csv")

    with col1:
        if negative_excel_payload and can_export:
            st.download_button(
                label="导出否词Excel",
                data=negative_excel_payload["data"],
                file_name=negative_excel_payload["file_name"],
                mime=negative_excel_payload["mime"],
                key="download_negative_excel",
            )
        else:
            st.button("导出否词Excel", disabled=True, width="stretch")

    with col2:
        if negative_csv_payload and can_export:
            st.download_button(
                label="导出否词CSV（批量上传格式）",
                data=negative_csv_payload["data"],
                file_name=negative_csv_payload["file_name"],
                mime=negative_csv_payload["mime"],
                key="download_negative_csv",
            )
        else:
            st.button("导出否词CSV（批量上传格式）", disabled=True, width="stretch")


def render_manual_actions(
    db,
    product_id: int,
    *,
    can_export: bool = True,
    action_buckets: dict[str, list[dict[str, object]]] | None = None,
):
    """渲染手动投放操作清单"""
    st.write("### 推荐手动投放")
    st.markdown(
        '<p class="actions-section-note">这里展示的是已收敛成可执行动作的手动词与商品定位；如果还存在分歧，请先回首页或搜索词分析页确认。</p>',
        unsafe_allow_html=True,
    )

    if action_buckets is not None:
        manual_keywords = action_buckets["manual_keywords"]
        manual_products = action_buckets["manual_products"]
    else:
        analysis_results = analyze_search_terms(db, product_id)
        if not analysis_results:
            st.info("暂无推荐手动投放的关键词")
            return

        manual_keywords = []
        manual_products = []

        for r in analysis_results:
            if r.action_type and r.action_type.startswith("manual"):
                item = {
                    "term": r.term,
                    "term_type": r.term_type,
                    "triggered_rule": r.triggered_rule,
                    "suggested_action": r.suggested_action,
                    "action_type": r.action_type,
                    "confidence": r.confidence,
                    "spend": r.data.get("total_spend", r.data.get("spend", 0)),
                    "clicks": r.data.get("total_clicks", r.data.get("clicks", 0)),
                    "orders": r.data.get("total_orders", r.data.get("orders", 0)),
                    "sales": r.data.get("total_sales", r.data.get("sales", 0)),
                }
                if r.term_type == "asin":
                    manual_products.append(item)
                else:
                    manual_keywords.append(item)

    if not manual_keywords and not manual_products:
        st.info("暂无推荐手动投放的关键词")
        return

    # 按优先级排序
    def get_priority_score(item):
        orders = item.get("orders", 0)
        sales = item.get("sales", 0)
        return orders * 10 + sales  # 简单优先级计算

    manual_keywords.sort(key=get_priority_score, reverse=True)
    manual_products.sort(key=get_priority_score, reverse=True)

    # ========== 关键词手动投放 ==========
    if manual_keywords:
        st.write("#### 关键词手动投放")
        df_keywords = pd.DataFrame(
            [
                {
                    "关键词": item["term"],
                    "订单": item.get("orders", 0),
                    "销售额": f"${item.get('sales', 0):.2f}",
                    "花费": f"${item.get('spend', 0):.2f}",
                    "ACOS": calculate_acos(item),
                    "触发规则": item["triggered_rule"],
                    "建议匹配": suggest_match_type(item),
                }
                for item in manual_keywords
            ]
        )
        st.dataframe(df_keywords, width="stretch", hide_index=True)

        st.divider()

        # 分匹配类型复制 - 根据action_type实际分类
        st.write("##### 按匹配类型复制")

        # 根据实际匹配类型分组（不再硬编码按位置切分）
        exact_keywords = [
            item["term"]
            for item in manual_keywords
            if suggest_match_type(item) == "精确匹配"
        ]
        phrase_keywords = [
            item["term"]
            for item in manual_keywords
            if suggest_match_type(item) == "短语匹配"
        ]

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**精确匹配** ({len(exact_keywords)}个)")
            st.text_area(
                "精确匹配词（复制到亚马逊后台）",
                value="\n".join(exact_keywords) if exact_keywords else "暂无",
                height=150,
                key="exact_manual_list",
            )

        with col2:
            st.write(f"**短语匹配** ({len(phrase_keywords)}个)")
            st.text_area(
                "短语匹配词（复制到亚马逊后台）",
                value="\n".join(phrase_keywords) if phrase_keywords else "暂无",
                height=150,
                key="phrase_manual_list",
            )

    # ========== ASIN商品定位 ==========
    if manual_products:
        st.write("#### ASIN商品定位")
        df_products = pd.DataFrame(
            [
                {
                    "ASIN": item["term"],
                    "订单": item.get("orders", 0),
                    "销售额": f"${item.get('sales', 0):.2f}",
                    "花费": f"${item.get('spend', 0):.2f}",
                    "ACOS": calculate_acos(item),
                    "触发规则": item["triggered_rule"],
                }
                for item in manual_products
            ]
        )
        st.dataframe(df_products, width="stretch", hide_index=True)

        # ASIN没有匹配类型，直接复制列表
        asins_text = "\n".join([item["term"] for item in manual_products])
        st.text_area(
            "商品定位ASIN列表（复制到亚马逊后台）",
            value=asins_text,
            height=100,
            key="product_manual_list",
        )

    st.divider()

    # 导出按钮
    manual_excel_payload = _get_export_payload(db, product_id, "manual", "xlsx")
    if manual_excel_payload and can_export:
        st.download_button(
            label="导出手动词Excel",
            data=manual_excel_payload["data"],
            file_name=manual_excel_payload["file_name"],
            mime=manual_excel_payload["mime"],
            key="download_manual_excel",
        )
    else:
        st.button("导出手动词Excel", disabled=True, width="stretch")


def render_action_history(db, product_id: int):
    """渲染操作历史"""
    st.write("### 操作历史")
    st.markdown(
        '<p class="actions-section-note">操作历史用于复盘最近执行记录，确认哪些动作已经落地，避免同一批词重复处理。</p>',
        unsafe_allow_html=True,
    )

    # 获取操作计划历史
    # action_plans 表没有 product_id，需要通过 analysis_results -> search_terms -> campaigns 关联
    try:
        cursor = db.execute(
            """
            SELECT
                ap.created_at,
                ap.action as action_type,
                st.term,
                ap.status
            FROM action_plans ap
            JOIN analysis_results ar ON ap.analysis_result_id = ar.id
            JOIN search_terms st ON ar.search_term_id = st.id
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ?
            ORDER BY ap.created_at DESC
            LIMIT 50
            """,
            (product_id,),
        )
        history = cursor.fetchall()

        if not history:
            st.info("暂无操作历史记录")
            return

        df = pd.DataFrame(
            [
                {
                    "时间": row["created_at"],
                    "操作类型": row["action_type"],
                    "关键词": row["term"],
                    "状态": row["status"],
                }
                for row in history
            ]
        )

        st.dataframe(df, width="stretch", hide_index=True)

    except Exception as e:
        logger.error(f"获取操作历史失败: {e}")
        st.info("暂无操作历史记录")


def calculate_acos(item: dict) -> str:
    """计算ACOS"""
    spend = item.get("spend", 0)
    sales = item.get("sales", 0)

    if sales > 0:
        acos = spend / sales
        return f"{acos:.2%}"
    return "N/A"


def suggest_match_type(item: dict) -> str:
    """
    建议匹配类型 - 基于规则引擎的action_type

    用户手动标注的"手动精准"应该显示"精确匹配"，而不是根据ACOS/订单自动推断
    """
    action_type = item.get("action_type", "")

    # 根据action_type确定匹配类型
    # manual_exact, manual_exact_no_neg, manual_exact_with_neg → 精确匹配
    if "manual_exact" in action_type:
        return "精确匹配"

    # manual_phrase（如果有）→ 短语匹配
    if "manual_phrase" in action_type:
        return "短语匹配"

    # manual_product → 商品定位（ASIN没有匹配类型，但保险起见）
    if "manual_product" in action_type:
        return "商品定位"

    # 默认：精确匹配（用户的Excel标注大多是"手动精准"）
    return "精确匹配"
