from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from src.analysis.truth_replay import (
    get_execution_batch_effect_preview,
    get_truth_first_pending_stats,
    summarize_execution_batch_effect,
)
from src.data.db import Database
from src.data.parser import FileParser
from src.rules.engine import analyze_search_terms_cached
from src.services.settings_service import (
    build_full_backup_export_payload,
    clear_product_runtime_data,
    restore_full_backup,
    save_config_version,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APP_DB_PATH = PROJECT_ROOT / "data" / "db" / "app.db"


def _get_app_database_path() -> Path:
    configured = os.getenv("DATABASE_PATH", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        return path
    return DEFAULT_APP_DB_PATH


def _format_timestamp(value: str | None, *, fallback: str = "尚未分析") -> str:
    if not value:
        return fallback
    return str(value).replace("T", " ")[:16]


def _resolve_product(db: Database, product_id: int | None) -> dict | None:
    if product_id:
        product = db.get_product(product_id)
        if product:
            return product
    products = db.get_all_products()
    return products[0] if products else None


def _campaign_count(db: Database, product_id: int) -> int:
    return int(
        db.execute(
            "SELECT COUNT(*) AS count FROM campaigns WHERE product_id = ?",
            (product_id,),
        ).fetchone()["count"]
    )


def _manual_review_count(db: Database, product_id: int) -> int:
    return int(
        db.execute(
            "SELECT COUNT(*) AS count FROM manual_reviews WHERE product_id = ?",
            (product_id,),
        ).fetchone()["count"]
    )


def _analysis_result_count(db: Database, product_id: int) -> int:
    return int(
        db.execute(
            """
            SELECT COUNT(*) AS count FROM analysis_results ar
            JOIN search_terms st ON ar.search_term_id = st.id
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ?
            """,
            (product_id,),
        ).fetchone()["count"]
    )


def _get_dashboard_stats(db: Database, product_id: int) -> dict[str, Any]:
    query = """
        SELECT
            COUNT(DISTINCT st.term) as term_count,
            COALESCE(SUM(st.spend), 0) as total_spend,
            COALESCE(SUM(st.orders), 0) as total_orders,
            COALESCE(SUM(st.sales), 0) as total_sales,
            MAX(COALESCE(st.report_date, date(st.created_at))) AS latest_report_date
        FROM search_terms st
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ?
    """
    row = db.execute(query, (product_id,)).fetchone()
    if not row:
        return {
            "term_count": 0,
            "total_spend": 0.0,
            "total_orders": 0,
            "total_sales": 0.0,
            "acos": 0.0,
            "latest_report_date": None,
        }
    spend = float(row["total_spend"] or 0.0)
    sales = float(row["total_sales"] or 0.0)
    return {
        "term_count": int(row["term_count"] or 0),
        "total_spend": spend,
        "total_orders": int(row["total_orders"] or 0),
        "total_sales": sales,
        "latest_report_date": row["latest_report_date"],
        "acos": round((spend / sales), 4) if sales > 0 else 0.0,
    }


def _get_pending_stats(db: Database, product_id: int) -> dict[str, int]:
    truth_stats = get_truth_first_pending_stats(db, product_id)
    if truth_stats is not None:
        return truth_stats

    results = analyze_search_terms_cached(db, product_id)
    stats = {
        "negative_count": 0,
        "manual_count": 0,
        "ai_pending_count": 0,
        "review_pending_count": 0,
        "conflict_count": 0,
    }
    for result in results:
        action = result.action_type or ""
        if action.startswith("negative"):
            stats["negative_count"] += 1
        elif action.startswith("manual"):
            stats["manual_count"] += 1
        elif action == "conflict":
            stats["conflict_count"] += 1
        if result.confidence < 1.0:
            stats["ai_pending_count"] += 1
        if getattr(result, "needs_review", False):
            stats["review_pending_count"] += 1
    return stats


def _latest_snapshot(db: Database, product_id: int) -> dict | None:
    snapshots = db.list_analysis_run_snapshots(product_id, limit=1)
    return snapshots[0] if snapshots else None


def _latest_snapshot_rows(db: Database, product_id: int) -> list[dict]:
    snapshot = _latest_snapshot(db, product_id)
    return snapshot.get("rows") or [] if snapshot else []


def _build_top_actions(
    pending_stats: dict[str, int], snapshot_rows: list[dict]
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    review_pending = int(pending_stats.get("review_pending_count") or 0)
    negative_pending = int(pending_stats.get("negative_count") or 0)
    manual_pending = int(pending_stats.get("manual_count") or 0)
    conflict_pending = int(pending_stats.get("conflict_count") or 0)

    negative_rows = sorted(
        [
            r
            for r in snapshot_rows
            if str(r.get("action_type", "")).startswith("negative")
        ],
        key=lambda r: float(r.get("spend") or 0.0),
        reverse=True,
    )
    manual_rows = sorted(
        [
            r
            for r in snapshot_rows
            if str(r.get("action_type", "")).startswith("manual")
        ],
        key=lambda r: float(r.get("sales") or 0.0),
        reverse=True,
    )
    conflict_rows = sorted(
        [r for r in snapshot_rows if str(r.get("action_type", "")) == "conflict"],
        key=lambda r: float(r.get("spend") or 0.0),
        reverse=True,
    )

    if review_pending > 0:
        actions.append(
            {
                "tag": "先审核",
                "title": f"先处理 {review_pending} 个待审核词",
                "description": "先把低置信度和分歧词拍板，后面的执行才会稳定。",
            }
        )
    if negative_pending > 0:
        top = negative_rows[0] if negative_rows else None
        if top:
            actions.append(
                {
                    "tag": "止损优先",
                    "title": f"优先止损：{top.get('term', '高花费词')}",
                    "description": f"花费 ${float(top.get('spend') or 0):.2f}，来源规则：{top.get('triggered_rule') or '最近分析'}。",
                }
            )
        else:
            actions.append(
                {
                    "tag": "止损优先",
                    "title": f"优先止损 {negative_pending} 个高花费词",
                    "description": "先处理高花费无转化词。",
                }
            )
    if manual_pending > 0:
        top = manual_rows[0] if manual_rows else None
        if top:
            actions.append(
                {
                    "tag": "补量机会",
                    "title": f"补量词：{top.get('term', '高转化词')}",
                    "description": f"销售额 ${float(top.get('sales') or 0):.2f}，建议动作：{top.get('suggested_action') or '手动补量'}。",
                }
            )
        else:
            actions.append(
                {
                    "tag": "补量机会",
                    "title": f"补量 {manual_pending} 个高转化词",
                    "description": "止损后优先处理高转化手动机会。",
                }
            )
    if conflict_pending > 0:
        top = conflict_rows[0] if conflict_rows else None
        actions.append(
            {
                "tag": "风险处理",
                "title": f"拍板 {conflict_pending} 个分歧词",
                "description": f"{top.get('term')} 存在跨结论分歧。"
                if top
                else "执行前先稳定分歧词。",
            }
        )

    return actions[:3] or [
        {
            "tag": "继续推进",
            "title": "先导入或运行分析",
            "description": "当前还没有足够结果，先建立本轮数据。",
        }
    ]


def _build_trend(
    points: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, int | str]]]:
    def _window(day_count: int) -> dict[str, str]:
        subset = points[-day_count:]
        spend = sum(float(p["spend"]) for p in subset)
        orders = sum(int(p["orders"]) for p in subset)
        sales = sum(float(p["sales"]) for p in subset)
        acos = (spend / sales) if sales > 0 else 0.0
        return {
            "label": f"最近 {day_count} 天",
            "value": f"${spend:.2f}",
            "detail": f"订单 {orders} ｜ 销售额 ${sales:.2f} ｜ ACOS {acos:.2%}",
        }

    cards = [_window(days) for days in (7, 14, 30)]
    bars = [
        {"label": p["label"], "value": int(round(float(p["spend"]))) or 1}
        for p in points[-5:]
    ]
    return cards, bars


def _get_trend_payload(
    db: Database, product_id: int
) -> tuple[list[dict[str, str]], list[dict[str, int | str]]]:
    cursor = db.execute(
        """
        SELECT COALESCE(st.report_date, date(st.created_at)) AS bucket_date,
               COALESCE(SUM(st.spend), 0) AS spend,
               COALESCE(SUM(st.orders), 0) AS orders,
               COALESCE(SUM(st.sales), 0) AS sales
        FROM search_terms st
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ?
        GROUP BY bucket_date
        ORDER BY bucket_date DESC
        LIMIT 30
        """,
        (product_id,),
    )
    raw = [dict(r) for r in cursor.fetchall()]
    if not raw:
        return [], []
    points = []
    for row in reversed(raw):
        date_value = str(row["bucket_date"])
        try:
            label = dt.date.fromisoformat(date_value).strftime("%m-%d")
        except ValueError:
            label = date_value
        points.append(
            {
                "label": label,
                "spend": float(row["spend"] or 0.0),
                "orders": int(row["orders"] or 0),
                "sales": float(row["sales"] or 0.0),
            }
        )
    return _build_trend(points)


def _classify_bucket(term: str, term_type: str, product_config: dict) -> str:
    normalized_term = str(term or "").strip().lower()
    if not normalized_term:
        return "其它长尾"
    own_variants = {
        str(item).strip().upper()
        for item in (product_config.get("own_variants") or [])
        + (product_config.get("own_asins") or [])
        if str(item).strip()
    }
    competitor_asins = {
        str(item).strip().upper()
        for item in product_config.get("competitor_asins", [])
        if str(item).strip()
    }
    if term_type == "asin":
        normalized_asin = normalized_term.upper()
        if normalized_asin in own_variants:
            return "自家变体 ASIN"
        if normalized_asin in competitor_asins:
            return "竞品 ASIN"
        return "其它 ASIN"

    libraries = product_config.get("keyword_libraries") or {}
    generic_keywords = {
        str(item).strip().lower()
        for item in libraries.get("generic_keywords", [])
        if str(item).strip()
    }
    core_keywords = [
        str(item).strip().lower()
        for item in product_config.get("core_keywords", [])
        if str(item).strip()
    ]
    related_keywords = [
        str(item).strip().lower()
        for item in product_config.get("related_keywords", [])
        if str(item).strip()
    ]
    if normalized_term in generic_keywords:
        return "泛词"
    if any(keyword and keyword in normalized_term for keyword in core_keywords):
        return "核心词"
    if any(keyword and keyword in normalized_term for keyword in related_keywords):
        return "相关词"
    return "其它长尾"


def _get_structure_payload(
    db: Database, product_id: int, product_config: dict
) -> list[dict[str, Any]]:
    rows = _latest_snapshot_rows(db, product_id)
    source_rows = (
        rows
        if rows
        else [
            dict(r)
            for r in db.execute(
                """
        SELECT DISTINCT st.term, st.term_type
        FROM search_terms st
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ?
        """,
                (product_id,),
            ).fetchall()
        ]
    )
    counts: dict[str, int] = {}
    for row in source_rows:
        bucket = _classify_bucket(
            row.get("term", ""), row.get("term_type", "keyword"), product_config
        )
        counts[bucket] = counts.get(bucket, 0) + 1
    total = sum(counts.values()) or 1
    return [
        {"label": label, "count": count, "ratio": f"{round((count / total) * 100)}%"}
        for label, count in sorted(counts.items(), key=lambda i: i[1], reverse=True)
    ]


def _get_execution_effect_payload(db: Database, product_id: int) -> dict[str, Any]:
    batches = db.list_execution_batches(product_id, limit=1)
    if not batches:
        return {
            "status": "暂无批次",
            "summary": "当前还没有执行批次，先在操作清单里生成一批动作。",
            "chips": [],
            "improving": [],
            "risky": [],
            "batchCode": None,
            "batchStatus": None,
        }
    batch = batches[0]
    preview = get_execution_batch_effect_preview(db, batch)
    summary = summarize_execution_batch_effect(preview)
    return {
        "status": summary.get("status", "待观察"),
        "summary": summary.get("summary", "当前还没有足够的信息来判断最近执行效果。"),
        "chips": summary.get("chips", []),
        "improving": summary.get("top_improving_terms", []),
        "risky": summary.get("top_risky_terms", []),
        "batchCode": batch.get("batch_code"),
        "batchStatus": batch.get("status"),
    }


def _get_analysis_rows_payload(db: Database, product_id: int) -> list[dict[str, Any]]:
    rows = _latest_snapshot_rows(db, product_id)
    if rows:
        return [
            {
                "term": row.get("term"),
                "type": row.get("term_type", "keyword"),
                "rule": row.get("triggered_rule") or "最近一次分析",
                "action": row.get("suggested_action")
                or row.get("action_type")
                or "观察",
                "spend": f"${float(row.get('spend') or 0.0):.2f}",
                "orders": int(row.get("orders") or 0),
                "confidence": f"{float(row.get('confidence') or 0):.0%}"
                if isinstance(row.get("confidence"), (int, float))
                else str(row.get("confidence") or "-"),
            }
            for row in rows[:8]
        ]

    results = analyze_search_terms_cached(db, product_id)
    payload = []
    for result in results[:8]:
        payload.append(
            {
                "term": result.term,
                "type": result.term_type,
                "rule": result.triggered_rule,
                "action": result.suggested_action,
                "spend": f"${float(result.data.get('spend') or result.data.get('total_spend') or 0.0):.2f}",
                "orders": int(
                    result.data.get("orders") or result.data.get("total_orders") or 0
                ),
                "confidence": f"{float(result.confidence):.0%}",
            }
        )
    return payload


def _get_execution_batches_payload(
    db: Database, product_id: int
) -> list[dict[str, Any]]:
    batches = db.list_execution_batches(product_id, limit=5)
    payload = []
    for batch in batches:
        preview = get_execution_batch_effect_preview(db, batch)
        summary = summarize_execution_batch_effect(preview)
        items = (batch.get("summary") or {}).get("items") or []
        payload.append(
            {
                "id": batch.get("id"),
                "code": batch.get("batch_code"),
                "type": batch.get("batch_type"),
                "status": batch.get("status"),
                "itemCount": batch.get("item_count") or len(items),
                "spend": f"${float(((batch.get('summary') or {}).get('spend_total') or 0.0)):.2f}",
                "sales": f"${float(((batch.get('summary') or {}).get('sales_total') or 0.0)):.2f}",
                "verdict": summary.get("status", "待观察"),
                "summary": summary.get(
                    "summary", batch.get("draft_note") or "暂无复盘结论。"
                ),
                "improving": summary.get("top_improving_terms", []),
                "risky": summary.get("top_risky_terms", []),
                "itemsPreview": [
                    {
                        "term": str(item.get("term") or "未命名词"),
                        "action": str(
                            item.get("suggested_action")
                            or item.get("action_type")
                            or "待执行"
                        ),
                        "spend": f"${float(item.get('spend') or 0.0):.2f}",
                    }
                    for item in items[:5]
                ],
                "itemsDetail": [
                    {
                        "term": str(item.get("term") or "未命名词"),
                        "action": str(
                            item.get("suggested_action")
                            or item.get("action_type")
                            or "待执行"
                        ),
                        "actionType": str(item.get("action_type") or "pending"),
                        "spend": f"${float(item.get('spend') or 0.0):.2f}",
                        "sales": f"${float(item.get('sales') or 0.0):.2f}",
                    }
                    for item in items
                ],
            }
        )
    return payload


def _build_execution_batch_summary(
    db: Database, product_id: int, batch_type: str
) -> dict[str, Any]:
    snapshot = _latest_snapshot(db, product_id)
    snapshot_rows = snapshot.get("rows") or [] if snapshot else []
    normalized_batch_type = str(batch_type).strip().lower() or "general"
    if normalized_batch_type == "negative":
        filtered = [
            row
            for row in snapshot_rows
            if str(row.get("action_type", "")).startswith("negative")
        ]
    elif normalized_batch_type == "manual":
        filtered = [
            row
            for row in snapshot_rows
            if str(row.get("action_type", "")).startswith("manual")
        ]
    elif normalized_batch_type == "conflict":
        filtered = [
            row
            for row in snapshot_rows
            if str(row.get("action_type", "")) == "conflict"
        ]
    else:
        filtered = snapshot_rows

    items = [
        {
            "term": row.get("term"),
            "action_type": row.get("action_type"),
            "suggested_action": row.get("suggested_action"),
            "spend": float(row.get("spend") or 0.0),
            "sales": float(row.get("sales") or 0.0),
        }
        for row in filtered[:50]
        if row.get("term")
    ]
    return {
        "item_count": len(items),
        "items": items,
        "baseline_snapshot_id": snapshot.get("id") if snapshot else None,
        "spend_total": round(sum(item["spend"] for item in items), 2),
        "sales_total": round(sum(item["sales"] for item in items), 2),
    }


def create_execution_batch_for_frontend(
    *,
    product_id: int,
    batch_type: str,
    draft_note: str | None = None,
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        summary = _build_execution_batch_summary(db, product_id, batch_type)
        if not summary["item_count"]:
            raise ValueError("当前没有可生成该批次的动作。")
        batch = db.create_execution_batch(
            product_id=product_id,
            batch_type=batch_type,
            summary=summary,
            draft_note=draft_note,
        )
        preview = get_execution_batch_effect_preview(db, batch)
        verdict = summarize_execution_batch_effect(preview)
        batch["verdict"] = verdict.get("status", batch.get("status"))
        batch["effect_summary"] = verdict
        return batch


def update_execution_batch_for_frontend(
    *,
    batch_id: int,
    status: str,
    execution_note: str | None = None,
    review_note: str | None = None,
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        db.update_execution_batch(
            batch_id,
            status=status,
            execution_note=execution_note,
            review_note=review_note,
        )
        batch = db.get_execution_batch(batch_id)
        if batch is None:
            raise ValueError("执行批次不存在")
        preview = get_execution_batch_effect_preview(db, batch)
        verdict = summarize_execution_batch_effect(preview)
        batch["verdict"] = verdict.get("status", batch.get("status"))
        batch["effect_summary"] = verdict
        return batch


def _check_decision_conflicts(
    db: "Database",
    product_id: int,
    term: str,
    new_relevance: str,
    *,
    days: int = 14,
) -> list[dict[str, Any]]:
    """Sprint A.4 — 检测当前决策是否与 14 天内的历史决策方向冲突。

    场景：
      - 此前 14 天内被标 strong_core，现在改 irrelevant → 警告（可能误操作）
      - 此前 14 天内被标 irrelevant，现在改 strong_core → 警告（可能复活）

    返回 [] 表示无冲突；非空 list 表示至少一条冲突记录。
    """
    import datetime as _dt

    POSITIVE = {"strong_core", "strong_longtail"}
    NEGATIVE = {"irrelevant", "generic", "weak", "car"}

    new_dir = (
        "positive"
        if new_relevance in POSITIVE
        else ("negative" if new_relevance in NEGATIVE else "neutral")
    )
    if new_dir == "neutral":
        return []

    rows = db.get_manual_reviews_by_term(product_id, term) or []
    cutoff = _dt.datetime.now() - _dt.timedelta(days=days)
    conflicts: list[dict[str, Any]] = []
    for row in rows:
        prev = row.get("relevance")
        if not prev or prev == "pending":
            continue
        prev_dir = (
            "positive"
            if prev in POSITIVE
            else ("negative" if prev in NEGATIVE else "neutral")
        )
        if prev_dir == "neutral" or prev_dir == new_dir:
            continue
        # 时间过滤
        ts_str = row.get("updated_at") or row.get("created_at") or ""
        try:
            ts = _dt.datetime.fromisoformat(str(ts_str).replace("T", " ").split(".")[0])
        except (ValueError, TypeError):
            continue
        if ts < cutoff:
            continue
        conflicts.append(
            {
                "previousDecision": prev,
                "previousDirection": prev_dir,
                "decidedAt": _format_timestamp(ts_str),
                "scope": row.get("scope") or "local",
                "campaignId": row.get("campaign_id"),
                "notes": (row.get("relevance_notes") or row.get("notes") or "")[:140],
            }
        )
    return conflicts


def submit_review_decision_for_frontend(
    *,
    product_id: int,
    term: str,
    term_type: str,
    campaign_id: int | None,
    relevance: str,
    notes: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        # Sprint A.4: 写入前查 14 天内反向决策，未 force 则返回冲突让前端二次确认
        if not force:
            conflicts = _check_decision_conflicts(db, product_id, term, relevance)
            if conflicts:
                return {
                    "requiresConfirmation": True,
                    "conflicts": conflicts,
                    "message": (
                        f"检测到 {len(conflicts)} 条与"
                        f"当前决策方向相反的近期记录，请确认是否仍要提交"
                    ),
                }
        review_id = db.upsert_manual_review(
            product_id=product_id,
            term=term,
            term_type=term_type,
            campaign_id=campaign_id,
            relevance=relevance,
            relevance_notes=notes,
            reviewed=True,
        )
        stats = db.get_review_stats(product_id)
        return {"reviewId": review_id, "stats": stats}


def run_analysis_for_frontend(*, product_id: int) -> dict[str, Any]:
    from src.analysis.truth_replay import (
        apply_reviewed_truth,
        build_analysis_run_snapshot_rows,
        build_analysis_run_snapshot_summary,
    )
    from src.data.aggregator import DataAggregator
    from src.rules.engine import RuleEngine

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        aggregator = DataAggregator(db)
        df = aggregator.aggregate_by_term(product_id)

        if df.empty:
            return {
                "status": "warning",
                "message": "当前导入数据暂时不足以生成搜索词分析结果。",
                "termsAnalyzed": 0,
                "resultsSaved": 0,
            }

        engine = RuleEngine(db, product_id)
        results = engine.analyze(df)
        if not results:
            return {
                "status": "warning",
                "message": "规则分析已运行，但当前没有生成可保存的建议。",
                "termsAnalyzed": len(df),
                "resultsSaved": 0,
            }

        effective_results = apply_reviewed_truth(db, product_id, results)
        snapshot_rows = build_analysis_run_snapshot_rows(effective_results)
        if snapshot_rows:
            db.save_analysis_run_snapshot(
                product_id,
                snapshot_rows,
                run_source="manual",
                summary=build_analysis_run_snapshot_summary(snapshot_rows),
            )

        results_saved = 0
        pending_reviews = 0
        for result in effective_results:
            db.save_analysis_result_by_term(
                product_id=product_id,
                term=result.term,
                triggered_rule=result.triggered_rule,
                suggested_action=result.suggested_action,
                action_type=result.action_type,
                confidence=result.confidence,
                ai_reasoning=result.ai_reasoning,
            )
            results_saved += 1

        for result in effective_results:
            needs_review = getattr(result, "needs_review", False)
            relevance = getattr(result, "relevance", None)
            if needs_review or relevance in (None, "pending"):
                db.upsert_manual_review(
                    product_id=product_id,
                    term=result.term,
                    term_type=result.term_type,
                    system_action=result.suggested_action,
                    relevance="pending",
                    reviewed=False,
                )
                pending_reviews += 1

        return {
            "status": "success",
            "message": "分析完成。",
            "termsAnalyzed": len(df),
            "resultsSaved": results_saved,
            "pendingReviews": pending_reviews,
        }


def upload_files_for_frontend(
    *,
    product_id: int,
    files: list[UploadFile],
    auto_analyze: bool = True,
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    parser = FileParser()
    imported_files: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    total_rows = 0

    with Database(str(db_path)) as db:
        for upload in files:
            upload_name = upload.filename or "uploaded.csv"
            try:
                upload.file.seek(0)
                df = parser.parse(upload.file, upload_name)
            except Exception as exc:
                failures.append({"fileName": upload_name, "reason": f"解析失败：{exc}"})
                continue

            if df is None or df.empty:
                failures.append(
                    {"fileName": upload_name, "reason": "文件中没有可导入的数据。"}
                )
                continue

            campaign_name = Path(upload_name).stem
            campaign_id = db.create_campaign(
                product_id=product_id,
                name=campaign_name,
            )
            saved_count = db.save_search_terms(df, campaign_id)
            imported_files.append(
                {
                    "fileName": upload_name,
                    "campaignName": campaign_name,
                    "rows": int(saved_count),
                }
            )
            total_rows += int(saved_count)

        analysis_state: dict[str, Any] | None = None
        if auto_analyze and total_rows > 0:
            analysis_state = run_analysis_for_frontend(product_id=product_id)

        status = "success" if imported_files else "warning"
        message = "上传完成。" if imported_files else "没有任何文件成功导入。"
        return {
            "status": status,
            "message": message,
            "importedFiles": imported_files,
            "failedFiles": failures,
            "importedRows": total_rows,
            "campaignsCreated": len(imported_files),
            "analysisState": analysis_state,
        }


def clear_runtime_for_frontend(*, product_id: int) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        clear_product_runtime_data(db, product_id)
        return {"status": "success", "message": "运行数据已清空。"}


def export_full_backup_for_frontend(*, product_id: int) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        payload = build_full_backup_export_payload(db, product_id)
        if not payload:
            raise ValueError("产品不存在")
        return {
            "fileName": payload["file_name"],
            "mime": payload["mime"],
            "content": payload["data"].decode("utf-8"),
            "summary": payload["summary"],
        }


def restore_full_backup_for_frontend(
    *,
    product_id: int | None,
    restore_as_new_product: bool,
    backup_data: dict,
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        restored_product_id = restore_full_backup(
            db,
            backup_data,
            current_product_id=product_id,
            restore_as_new_product=restore_as_new_product,
        )
        product = db.get_product(restored_product_id)
        return {
            "status": "success",
            "restoredProductId": restored_product_id,
            "productName": product.get("name") if product else "恢复产品",
        }


def _build_recent_activity(
    db: Database,
    product_id: int,
    latest_snapshot: dict | None,
    execution_batches: list[dict[str, Any]],
    pending_stats: dict[str, int],
) -> list[dict[str, str]]:
    activity: list[dict[str, str]] = []

    if latest_snapshot:
        item_count = int(
            (latest_snapshot.get("summary") or {}).get("item_count")
            or len(latest_snapshot.get("rows") or [])
        )
        activity.append(
            {
                "label": "最近分析",
                "title": f"最新快照已形成 {item_count} 条建议动作",
                "detail": f"生成于 {_format_timestamp(latest_snapshot.get('created_at'))}。",
                "href": "/analysis",
            }
        )

    if execution_batches:
        batch = execution_batches[0]
        activity.append(
            {
                "label": "最近执行",
                "title": f"{batch.get('code') or '最近批次'} 当前状态：{batch.get('status') or 'draft'}",
                "detail": batch.get("summary") or "执行批次已经同步回工作台。",
                "href": "/actions",
            }
        )

    pending_reviews = int(pending_stats.get("review_pending_count") or 0)
    if pending_reviews:
        activity.append(
            {
                "label": "最近审核",
                "title": f"当前仍有 {pending_reviews} 个词待人工拍板",
                "detail": "先处理低置信度与分歧词，后续动作会更稳定。",
                "href": "/review",
            }
        )

    latest_campaign = db.execute(
        "SELECT name, created_at FROM campaigns WHERE product_id = ? ORDER BY created_at DESC LIMIT 1",
        (product_id,),
    ).fetchone()
    if latest_campaign:
        activity.append(
            {
                "label": "最近导入",
                "title": f"{latest_campaign['name']} 已进入当前产品",
                "detail": f"创建于 {_format_timestamp(latest_campaign['created_at'])}。",
                "href": "/upload",
            }
        )

    return activity[:4]


def _derive_stage_title(
    pending_stats: dict[str, int], latest_snapshot: dict | None
) -> tuple[str, str]:
    if (
        pending_stats.get("negative_count")
        or pending_stats.get("manual_count")
        or pending_stats.get("conflict_count")
    ):
        return "待执行优化动作", "先止损，再补量。"
    if pending_stats.get("review_pending_count"):
        return "待人工审核", "先拍板低置信度和分歧词。"
    if latest_snapshot:
        return "可开始新一轮", "本轮已完成，适合复盘或重新导入。"
    return "待运行分析", "先导入或运行分析。"


def build_workbench_payload(product_id: int | None = None) -> dict[str, Any]:
    db_path = _get_app_database_path()
    if not db_path.exists():
        return {"source": "empty", "productContext": None}

    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        if not product:
            return {"source": "empty", "productContext": None}

        product_id = int(product["id"])
        product_name = product.get("name") or "当前产品"
        product_config = product.get("config") or {}
        stats = _get_dashboard_stats(db, product_id)
        pending_stats = _get_pending_stats(db, product_id)
        latest_snapshot = _latest_snapshot(db, product_id)
        workspace_summary = db.get_workspace_summary(product_id)
        stage_title, stage_detail = _derive_stage_title(pending_stats, latest_snapshot)
        top_actions = _build_top_actions(
            pending_stats, _latest_snapshot_rows(db, product_id)
        )
        trend_cards, trend_bars = _get_trend_payload(db, product_id)
        structure_buckets = _get_structure_payload(db, product_id, product_config)
        execution_effect = _get_execution_effect_payload(db, product_id)
        execution_batches = _get_execution_batches_payload(db, product_id)
        recent_activity = _build_recent_activity(
            db, product_id, latest_snapshot, execution_batches, pending_stats
        )
        ops_templates = {
            "boss_summary": f"{product_name} 当前处于「{stage_title}」。最近执行效果判断为「{execution_effect['status']}」，建议今天优先处理："
            + "；".join(item["title"] for item in top_actions[:3]),
            "handoff_note": "【执行交接】先处理："
            + "；".join(item["title"] for item in top_actions[:3]),
            "weekly_review": f"【周度复盘】最近执行效果：{execution_effect['status']}；改善线索：{'、'.join(execution_effect.get('improving') or ['暂无'])}；仍需关注：{'、'.join(execution_effect.get('risky') or ['暂无'])}",
        }

        return {
            "source": "live",
            "productId": product_id,
            "productContext": {
                "name": product_name,
                "role": (
                    workspace_summary.get("current_role") or "viewer"
                ).capitalize(),
                "workspace": f"{product_name}工作区",
                "lastAnalysisAt": _format_timestamp(
                    latest_snapshot.get("created_at") if latest_snapshot else None
                ),
                "lastBackupAt": "暂无完整备份",
            },
            "workbenchStats": [
                {"label": "当前阶段", "value": stage_title, "detail": stage_detail},
                {
                    "label": "最近一次分析",
                    "value": _format_timestamp(
                        latest_snapshot.get("created_at") if latest_snapshot else None
                    ).replace(" ", " · ", 1),
                    "detail": "latest snapshot 已形成。"
                    if latest_snapshot
                    else "还没有分析快照。",
                },
                {
                    "label": "历史沉淀",
                    "value": f"{len(db.list_analysis_run_snapshots(product_id, limit=200))} 个分析快照",
                    "detail": f"{_manual_review_count(db, product_id)} 条人工审核、{len(db.list_execution_batches(product_id, limit=200))} 个执行批次。",
                },
                {
                    "label": "数据规模",
                    "value": f"{stats['term_count']} 条词 · {_campaign_count(db, product_id)} 个活动",
                    "detail": f"当前已形成 {_analysis_result_count(db, product_id)} 条建议动作。",
                },
            ],
            "topActions": top_actions,
            "trendCards": trend_cards,
            "trendBars": trend_bars,
            "structureBuckets": structure_buckets,
            "executionEffect": execution_effect,
            "opsTemplates": ops_templates,
            "aiCopilotCards": [
                {
                    "title": "AI 汇总简报",
                    "context": f"当前产品：{product_name} · 上下文：最近一次分析结果",
                    "summary": top_actions[0]["description"]
                    if top_actions
                    else "先导入数据或运行分析。",
                    "prompts": [
                        "解释 ACOS 为什么高",
                        "给我 3 个最优先动作",
                        "生成老板摘要",
                    ],
                }
            ],
            "recentActivity": recent_activity,
            "analysisRows": _get_analysis_rows_payload(db, product_id),
            "executionBatches": execution_batches,
        }


def build_upload_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        stats = _get_dashboard_stats(db, product_id)
        snapshots = db.list_analysis_run_snapshots(product_id, limit=5)
        campaigns = [
            dict(row)
            for row in db.execute(
                "SELECT id, name, created_at FROM campaigns WHERE product_id = ? ORDER BY created_at DESC LIMIT 5",
                (product_id,),
            ).fetchall()
        ]
        return {
            **workbench,
            "upload": {
                "latestReportDate": stats.get("latest_report_date") or "暂无导入",
                "searchTerms": stats["term_count"],
                "campaigns": _campaign_count(db, product_id),
                "snapshotCount": len(
                    db.list_analysis_run_snapshots(product_id, limit=200)
                ),
                "recentSnapshots": [
                    {
                        "id": s["id"],
                        "createdAt": _format_timestamp(s["created_at"]),
                        "itemCount": int(
                            (s.get("summary") or {}).get("item_count")
                            or len(s.get("rows") or [])
                        ),
                    }
                    for s in snapshots
                ],
                "recentCampaigns": [
                    {
                        "id": c["id"],
                        "name": c["name"],
                        "createdAt": _format_timestamp(c["created_at"]),
                    }
                    for c in campaigns
                ],
            },
        }


def _cluster_pending_terms(
    items: list[dict[str, Any]], similarity_threshold: float = 0.7
) -> dict[str, int]:
    """Sprint A.1 — 用 SequenceMatcher.ratio() 给待审 terms 做轻量聚类。

    返回 `{term: cluster_id}` 映射；ratio >= threshold 归一类。
    cluster_id 从 0 开始递增；single-item 簇也分配 id 便于前端统一渲染。
    无外部依赖；O(N²) 但 N≤8（pending limit）成本可忽略。
    """
    from difflib import SequenceMatcher

    terms: list[str] = [
        str(it.get("term") or "").strip().lower() for it in items if it.get("term")
    ]
    cluster_of: dict[str, int] = {}
    next_id = 0
    for term in terms:
        if term in cluster_of:
            continue
        cluster_of[term] = next_id
        for other in terms:
            if other in cluster_of or other == term:
                continue
            if SequenceMatcher(None, term, other).ratio() >= similarity_threshold:
                cluster_of[other] = next_id
        next_id += 1
    return cluster_of


def _fetch_historical_decisions(
    db: "Database", product_id: int, term: str, *, limit: int = 5
) -> list[dict[str, Any]]:
    """Sprint A.1 — 按 term 拉历史决策给前端提示"32 天前已否定过"等。

    复用 `db.get_manual_reviews_by_term()`；按 decidedAt desc，最多 limit 条。
    跳过 status=pending 的（仅返回真正已决策的）。
    """
    if not term:
        return []
    rows = db.get_manual_reviews_by_term(product_id, term) or []
    history = []
    for row in rows:
        relevance = row.get("relevance")
        if not relevance or relevance == "pending":
            continue
        history.append(
            {
                "decidedAt": _format_timestamp(
                    row.get("updated_at") or row.get("created_at")
                ),
                "decision": relevance,
                "scope": row.get("scope") or "local",
                "campaignId": row.get("campaign_id"),
                "notes": (row.get("relevance_notes") or row.get("notes") or "")[:140],
            }
        )
    history.sort(key=lambda r: r.get("decidedAt") or "", reverse=True)
    return history[:limit]


def build_amazon_bulk_csv_export(
    product_id: int | None,
) -> tuple[bytes, str] | None:
    """Sprint D.2 — 当前产品所有 negative 推荐 → Amazon Bulk Operations CSV bytes。

    返回 (csv_bytes, file_name) 或 None（无 negative 时）。
    Endpoint 直接 Response(content=bytes, media_type="text/csv") 让浏览器下载。
    """
    from src.export.exporter import ReportExporter
    from src.rules.engine import AnalysisResult

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        df = db.get_analysis_results({"product_id": product_id})
        if df.empty:
            return None

        # DataFrame → list[AnalysisResult]
        # campaign_name 不是 dataclass 字段，按 exporter 测试 fixture 的做法
        # 在实例化之后用动态属性赋值（dataclass 默认无 slots，允许扩展属性）。
        results: list[AnalysisResult] = []
        for _, row in df.iterrows():
            ar = AnalysisResult(
                term=str(row.get("term") or ""),
                term_type=str(row.get("term_type") or "keyword"),
                triggered_rule=str(row.get("triggered_rule") or ""),
                suggested_action=str(row.get("suggested_action") or ""),
                action_type=str(row.get("action_type") or ""),
                confidence=float(row.get("confidence") or 0.0),
                data={},
            )
            ar.campaign_name = str(row.get("campaign_name") or "")
            results.append(ar)

        exporter = ReportExporter()
        return exporter.export_amazon_bulk_csv_bytes(
            results, product_name=str(product.get("name") or "")
        )


def build_term_detail_payload(
    product_id: int | None, term: str, *, days: int = 30
) -> dict[str, Any]:
    """Sprint A.2 — 单 term 30 天详情，给前端详情抽屉用。

    返回：
      - term / termType / firstSeen / lastSeen
      - dailySeries: [{date, spend, clicks, orders, sales}]（最近 N 天）
      - aggregates: 30d 总和（spend/clicks/orders/sales/cvr/acos）
      - appliedRules: 该 term 历次匹配的规则（unique by rule name）
      - historicalDecisions: 复用 _fetch_historical_decisions
      - currentRelevance: 最新一次的 relevance（pending 表示未审）
    """
    if not term:
        raise ValueError("term 不能为空")

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])

        # 1) 拉所有 search_term 行 + analysis_result 关联
        cursor = db.execute(
            """
            SELECT st.term, st.term_type, st.spend, st.clicks, st.orders, st.sales,
                   st.report_date, st.created_at, ar.triggered_rule, ar.action_type,
                   ar.confidence
              FROM search_terms st
              LEFT JOIN analysis_results ar ON ar.search_term_id = st.id
              JOIN campaigns c ON st.campaign_id = c.id
             WHERE c.product_id = ? AND st.term = ?
             ORDER BY COALESCE(st.report_date, st.created_at) DESC
             LIMIT 200
            """,
            (product_id, term),
        )
        rows = [dict(r) for r in cursor.fetchall()]

        if not rows:
            return {
                "term": term,
                "termType": "keyword",
                "found": False,
                "message": "该词在最近数据中未出现",
            }

        # 2) Daily 聚合（按 report_date 分组）
        from collections import defaultdict

        daily: dict[str, dict[str, float]] = defaultdict(
            lambda: {"spend": 0.0, "clicks": 0.0, "orders": 0.0, "sales": 0.0}
        )
        applied_rules: dict[str, int] = {}
        agg_total = {"spend": 0.0, "clicks": 0.0, "orders": 0.0, "sales": 0.0}
        for row in rows:
            day = (row.get("report_date") or row.get("created_at") or "")[:10]
            if not day:
                continue
            for k in ("spend", "clicks", "orders", "sales"):
                v = float(row.get(k) or 0.0)
                daily[day][k] += v
                agg_total[k] += v
            rule = row.get("triggered_rule")
            if rule:
                applied_rules[rule] = applied_rules.get(rule, 0) + 1

        # 截取最近 N 天
        sorted_days = sorted(daily.keys(), reverse=True)[:days]
        daily_series = [
            {"date": d, **{k: round(daily[d][k], 2) for k in daily[d]}}
            for d in sorted(sorted_days)
        ]

        cvr = (
            (agg_total["orders"] / agg_total["clicks"])
            if agg_total["clicks"] > 0
            else 0.0
        )
        acos = (
            (agg_total["spend"] / agg_total["sales"]) if agg_total["sales"] > 0 else 0.0
        )

        # 3) 历史决策（复用 helper）
        history = _fetch_historical_decisions(db, product_id, term, limit=10)
        current_relevance = history[0]["decision"] if history else "pending"

        first_seen = sorted(daily.keys())[0] if daily else None
        last_seen = sorted(daily.keys(), reverse=True)[0] if daily else None

        return {
            "term": term,
            "termType": rows[0].get("term_type") or "keyword",
            "found": True,
            "firstSeen": first_seen,
            "lastSeen": last_seen,
            "currentRelevance": current_relevance,
            "dailySeries": daily_series,
            "aggregates": {
                "spend": round(agg_total["spend"], 2),
                "clicks": int(agg_total["clicks"]),
                "orders": int(agg_total["orders"]),
                "sales": round(agg_total["sales"], 2),
                "cvr": round(cvr, 4),
                "acos": round(acos, 4),
                "rowCount": len(rows),
            },
            "appliedRules": [
                {"rule": k, "hits": v}
                for k, v in sorted(applied_rules.items(), key=lambda kv: -kv[1])
            ],
            "historicalDecisions": history,
        }


def build_review_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        review_stats = db.get_review_stats(product_id)
        pending_items = db.get_pending_reviews_list(product_id, limit=8)
        # Sprint A.1: 加 cluster_id（相似词聚簇）+ historicalDecisions（同 term 历史拍板）
        cluster_map = _cluster_pending_terms(pending_items)
        return {
            **workbench,
            "review": {
                "stats": review_stats,
                "pendingItems": [
                    {
                        "term": item.get("term"),
                        "termType": item.get("term_type", "keyword"),
                        "campaignName": item.get("campaign_name") or "全局",
                        "campaignId": item.get("campaign_id"),
                        "relevance": item.get("relevance") or "pending",
                        "createdAt": _format_timestamp(item.get("created_at")),
                        "clusterId": cluster_map.get(
                            str(item.get("term") or "").strip().lower(), -1
                        ),
                        "historicalDecisions": _fetch_historical_decisions(
                            db, product_id, str(item.get("term") or "")
                        ),
                    }
                    for item in pending_items
                ],
            },
        }


def update_settings_config_for_frontend(
    *,
    product_id: int,
    core_keywords: list[str],
    related_keywords: list[str],
    competitor_asins: list[str],
    own_variants: list[str],
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    normalized = {
        "core_keywords": [item.strip() for item in core_keywords if str(item).strip()],
        "related_keywords": [
            item.strip() for item in related_keywords if str(item).strip()
        ],
        "competitor_asins": [
            item.strip().upper() for item in competitor_asins if str(item).strip()
        ],
        "own_variants": [
            item.strip().upper() for item in own_variants if str(item).strip()
        ],
    }
    with Database(str(db_path)) as db:
        product = db.get_product(product_id)
        if not product:
            raise ValueError("产品不存在")
        previous_config = product.get("config") or {}
        next_config = {**previous_config, **normalized}
        save_config_version(db, product_id, previous_config, next_config)
        db.update_product_config(product_id, next_config)
        rule_versions = db.get_rule_versions(product_id)
        return {
            "status": "success",
            "message": "产品配置已更新。",
            "configEditor": {
                "coreKeywords": normalized["core_keywords"],
                "relatedKeywords": normalized["related_keywords"],
                "competitorAsins": normalized["competitor_asins"],
                "ownVariants": normalized["own_variants"],
            },
            "ruleVersionCount": len(rule_versions),
            "recentRuleVersions": [
                {
                    "version": int(item.get("version") or 0),
                    "createdAt": _format_timestamp(item.get("created_at")),
                    "description": str(item.get("description") or "配置更新")[:160],
                }
                for item in rule_versions[:5]
            ],
        }


def restore_settings_rule_version_for_frontend(
    *, product_id: int, version: int
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = db.get_product(product_id)
        if not product:
            raise ValueError("产品不存在")
        restored_snapshot = db.get_rule_version_snapshot(product_id, version)
        if not restored_snapshot:
            raise ValueError("指定规则版本不存在")
        previous_config = product.get("config") or {}
        next_config = {**previous_config, "rules": restored_snapshot}
        save_config_version(db, product_id, previous_config, next_config)
        db.update_product_config(product_id, next_config)
        rule_versions = db.get_rule_versions(product_id)
        return {
            "status": "success",
            "message": f"已恢复规则版本 v{version}。",
            "ruleVersionCount": len(rule_versions),
            "recentRuleVersions": [
                {
                    "version": int(item.get("version") or 0),
                    "createdAt": _format_timestamp(item.get("created_at")),
                    "description": str(item.get("description") or "配置更新")[:160],
                }
                for item in rule_versions[:5]
            ],
        }


def preview_settings_rule_version_for_frontend(
    *, product_id: int, version: int
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = db.get_product(product_id)
        if not product:
            raise ValueError("产品不存在")

        snapshot = db.get_rule_version_snapshot(product_id, version)
        if not snapshot:
            raise ValueError("指定规则版本不存在")

        current_config = product.get("config") or {}
        snapshot_core = [
            str(item).strip()
            for item in snapshot.get("core_keywords", [])
            if str(item).strip()
        ]
        snapshot_related = [
            str(item).strip()
            for item in snapshot.get("related_keywords", [])
            if str(item).strip()
        ]
        snapshot_competitors = [
            str(item).strip().upper()
            for item in snapshot.get("competitor_asins", [])
            if str(item).strip()
        ]
        snapshot_variants = [
            str(item).strip().upper()
            for item in snapshot.get("own_variants", [])
            if str(item).strip()
        ]

        current_core = [
            str(item).strip()
            for item in current_config.get("core_keywords", [])
            if str(item).strip()
        ]
        current_related = [
            str(item).strip()
            for item in current_config.get("related_keywords", [])
            if str(item).strip()
        ]
        current_competitors = [
            str(item).strip().upper()
            for item in current_config.get("competitor_asins", [])
            if str(item).strip()
        ]
        current_variants = [
            str(item).strip().upper()
            for item in current_config.get("own_variants", [])
            if str(item).strip()
        ]

        def _delta(target: list[str], current: list[str]) -> dict[str, list[str]]:
            target_set = set(target)
            current_set = set(current)
            return {
                "added": sorted(target_set - current_set),
                "removed": sorted(current_set - target_set),
            }

        return {
            "status": "success",
            "version": version,
            "configEditor": {
                "coreKeywords": snapshot_core,
                "relatedKeywords": snapshot_related,
                "competitorAsins": snapshot_competitors,
                "ownVariants": snapshot_variants,
            },
            "diff": {
                "coreKeywords": _delta(snapshot_core, current_core),
                "relatedKeywords": _delta(snapshot_related, current_related),
                "competitorAsins": _delta(snapshot_competitors, current_competitors),
                "ownVariants": _delta(snapshot_variants, current_variants),
            },
        }


def build_settings_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        product_config = product.get("config") or {}
        keyword_libraries = product_config.get("keyword_libraries") or {}
        backup_summary = {
            "searchTerms": _get_dashboard_stats(db, product_id)["term_count"],
            "analysisResults": _analysis_result_count(db, product_id),
            "manualReviews": _manual_review_count(db, product_id),
            "snapshots": len(db.list_analysis_run_snapshots(product_id, limit=200)),
            "executionBatches": len(db.list_execution_batches(product_id, limit=200)),
        }
        return {
            **workbench,
            "settings": {
                "ruleVersionCount": len(db.get_rule_versions(product_id)),
                "strategyProfileCount": len(db.list_strategy_profiles()),
                "keywordLibraryCounts": {
                    "irrelevant": len(keyword_libraries.get("irrelevant_keywords", [])),
                    "weak": len(keyword_libraries.get("weak_category_keywords", [])),
                    "generic": len(keyword_libraries.get("generic_keywords", [])),
                    "car": len(keyword_libraries.get("car_keywords", [])),
                    "variants": len(product_config.get("own_variants", [])),
                },
                "backupSummary": backup_summary,
                "configEditor": {
                    "coreKeywords": product_config.get("core_keywords", []),
                    "relatedKeywords": product_config.get("related_keywords", []),
                    "competitorAsins": product_config.get("competitor_asins", []),
                    "ownVariants": product_config.get("own_variants", []),
                },
                "recentRuleVersions": [
                    {
                        "version": int(item.get("version") or 0),
                        "createdAt": _format_timestamp(item.get("created_at")),
                        "description": str(item.get("description") or "配置更新")[:160],
                    }
                    for item in db.get_rule_versions(product_id)[:5]
                ],
            },
        }


def _build_weekly_compare(db: Database, product_id: int) -> dict[str, Any]:
    """Sprint B.3 — 最近 14 天日序列 + 本周 vs 上周对比。

    返回 4 字段：dailySeries / thisWeek / lastWeek / delta。
    delta 是比例（-0.12 = -12%），无上周数据时返回 1.0（增长）或 0.0（持平）。

    复用现有 search_terms.report_date 字段，无需 schema migration。
    """
    rows = db.execute(
        """
        SELECT
            COALESCE(st.report_date, date(st.created_at)) AS bucket_date,
            COALESCE(SUM(st.spend), 0) AS spend,
            COALESCE(SUM(st.orders), 0) AS orders,
            COALESCE(SUM(st.sales), 0) AS sales
        FROM search_terms st
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ?
          AND COALESCE(st.report_date, date(st.created_at)) >= date('now', '-14 days')
        GROUP BY bucket_date
        ORDER BY bucket_date ASC
        """,
        (product_id,),
    ).fetchall()

    daily = [
        {
            "date": str(r["bucket_date"] or ""),
            "spend": float(r["spend"] or 0.0),
            "orders": int(r["orders"] or 0),
            "sales": float(r["sales"] or 0.0),
        }
        for r in rows
    ]

    # 本周 = 最近 7 天日期范围（calendar），上周 = 之前 7 天日期范围
    today = dt.date.today()
    this_week_start = today - dt.timedelta(days=6)  # 含今天共 7 天
    last_week_start = today - dt.timedelta(days=13)
    last_week_end = today - dt.timedelta(days=7)

    def _in_range(item: dict, start: dt.date, end: dt.date) -> bool:
        try:
            d = dt.date.fromisoformat(item["date"])
        except (ValueError, TypeError):
            return False
        return start <= d <= end

    this_week_data = [i for i in daily if _in_range(i, this_week_start, today)]
    last_week_data = [i for i in daily if _in_range(i, last_week_start, last_week_end)]

    def _sum(items: list[dict]) -> dict[str, float]:
        return {
            "spend": float(sum(i["spend"] for i in items)),
            "orders": int(sum(i["orders"] for i in items)),
            "sales": float(sum(i["sales"] for i in items)),
        }

    this_week = _sum(this_week_data)
    last_week = _sum(last_week_data)

    def _delta(a: float, b: float) -> float:
        if b == 0:
            return 1.0 if a > 0 else 0.0
        return (a - b) / b

    return {
        "dailySeries": daily,
        "thisWeek": this_week,
        "lastWeek": last_week,
        "delta": {
            "spend": _delta(this_week["spend"], last_week["spend"]),
            "orders": _delta(this_week["orders"], last_week["orders"]),
            "sales": _delta(this_week["sales"], last_week["sales"]),
        },
    }


def build_actions_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        pending_stats = _get_pending_stats(db, product_id)
        weekly_compare = _build_weekly_compare(db, product_id)
        return {
            **workbench,
            "actions": {
                "negativeCount": int(pending_stats.get("negative_count") or 0),
                "manualCount": int(pending_stats.get("manual_count") or 0),
                "conflictCount": int(pending_stats.get("conflict_count") or 0),
                "latestBatchCode": (workbench.get("executionBatches") or [{}])[0].get(
                    "code"
                ),
            },
            "weeklyCompare": weekly_compare,
        }


def build_competitors_payload(product_id: int | None = None) -> dict[str, Any]:
    """Sprint C.1 — 内部竞品 ASIN 监控（复用现有 asin_rules 模块）。

    数据通路：
    - 读 products.config.competitor_asins（已配置的竞品列表）
    - 读 search_terms df（本产品所有搜索词，含作为 term 的对手 ASIN）
    - 调 src.rules.asin_rules.classify_asins → 4 类（own/competitor/negative/watch）
    - 调 get_competitor_insights → top/worst performers + 总览
    - 序列化为前端友好 JSON

    不需要 schema migration（实时计算，类似 B.1/B.2 聚合视图）。
    """
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        if not product:
            return {"source": "empty"}
        resolved_pid = int(product["id"])
        product_config = product.get("config") or {}
        configured = product_config.get("competitor_asins") or []
        configured_upper = {str(s).upper() for s in configured}

        df = db.get_search_terms({"product_id": resolved_pid})
        if df.empty:
            return {
                "source": "empty",
                "productId": resolved_pid,
                "productName": str(product.get("name") or ""),
                "configuredCompetitorAsins": list(configured),
                "discoveredCompetitors": [],
                "negativeAsinsCount": 0,
                "watchAsinsCount": 0,
                "insights": {
                    "totalCount": 0,
                    "totalSpend": 0.0,
                    "totalOrders": 0,
                    "avgAcos": 0.0,
                    "topPerformers": [],
                    "worstPerformers": [],
                },
            }

        from src.rules.asin_rules import classify_asins, get_competitor_insights

        classified = classify_asins(df, product_config)
        competitor_list = classified.get("competitor_asins", [])
        insights = get_competitor_insights(competitor_list)

        def _perf_brief(a):
            p = a.performance
            return {
                "asin": a.asin,
                "spend": float(p.get("spend") or 0.0),
                "orders": int(p.get("orders") or 0),
                "acos": float(p.get("acos") or 0.0),
            }

        return {
            "source": "live",
            "productId": resolved_pid,
            "productName": str(product.get("name") or ""),
            "configuredCompetitorAsins": list(configured),
            "discoveredCompetitors": [
                {
                    "asin": a.asin,
                    "isConfigured": a.asin in configured_upper,
                    "suggestedAction": a.suggested_action,
                    "impressions": int(a.performance.get("impressions") or 0),
                    "clicks": int(a.performance.get("clicks") or 0),
                    "spend": float(a.performance.get("spend") or 0.0),
                    "orders": int(a.performance.get("orders") or 0),
                    "sales": float(a.performance.get("sales") or 0.0),
                    "acos": float(a.performance.get("acos") or 0.0),
                }
                for a in competitor_list
            ],
            "negativeAsinsCount": len(classified.get("negative_asins", [])),
            "watchAsinsCount": len(classified.get("watch_asins", [])),
            "insights": {
                "totalCount": int(insights.get("total_count") or 0),
                "totalSpend": float(insights.get("total_spend") or 0.0),
                "totalOrders": int(insights.get("total_orders") or 0),
                "avgAcos": float(insights.get("avg_acos") or 0.0),
                "topPerformers": [
                    _perf_brief(a) for a in insights.get("top_performers", [])
                ],
                "worstPerformers": [
                    _perf_brief(a) for a in insights.get("worst_performers", [])
                ],
            },
        }


def build_analysis_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    rows = workbench.get("analysisRows") or []
    type_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    for row in rows:
        type_counts[row.get("type") or "unknown"] = (
            type_counts.get(row.get("type") or "unknown", 0) + 1
        )
        action_counts[row.get("action") or "unknown"] = (
            action_counts.get(row.get("action") or "unknown", 0) + 1
        )

    # Sprint B.1 / B.2 — Campaign + ASIN 聚合视图
    campaign_rows: list[dict[str, Any]] = []
    asin_rows: list[dict[str, Any]] = []
    resolved_pid = workbench.get("productId")
    if resolved_pid is not None:
        from src.data.aggregator import DataAggregator

        db_path = _get_app_database_path()
        with Database(str(db_path)) as db:
            agg = DataAggregator(db)
            try:
                campaign_df = agg.aggregate_by_campaign(product_id=int(resolved_pid))
                if not campaign_df.empty:
                    campaign_rows = [
                        {
                            "campaignName": str(r.get("campaign_name") or ""),
                            "matchType": str(r.get("match_type") or ""),
                            "asin": str(r.get("product_asin") or ""),
                            "productName": str(r.get("product_name") or ""),
                            "impressions": int(r.get("total_impressions") or 0),
                            "clicks": int(r.get("total_clicks") or 0),
                            "spend": float(r.get("total_spend") or 0.0),
                            "orders": int(r.get("total_orders") or 0),
                            "sales": float(r.get("total_sales") or 0.0),
                            "termCount": int(r.get("term_count") or 0),
                            "ctr": float(r.get("ctr") or 0.0),
                            "cpc": float(r.get("cpc") or 0.0),
                            "acos": float(r.get("acos") or 0.0),
                            "roas": float(r.get("roas") or 0.0),
                            "cvr": float(r.get("conversion_rate") or 0.0),
                        }
                        for r in campaign_df.to_dict(orient="records")
                    ]
            except Exception:  # noqa: BLE001 — 聚合失败不影响主 payload
                campaign_rows = []
            try:
                asin_df = agg.aggregate_by_asin(product_id=int(resolved_pid))
                if not asin_df.empty:
                    asin_rows = [
                        {
                            "asin": str(r.get("product_asin") or ""),
                            "productName": str(r.get("product_name") or ""),
                            "impressions": int(r.get("total_impressions") or 0),
                            "clicks": int(r.get("total_clicks") or 0),
                            "spend": float(r.get("total_spend") or 0.0),
                            "orders": int(r.get("total_orders") or 0),
                            "sales": float(r.get("total_sales") or 0.0),
                            "termCount": int(r.get("term_count") or 0),
                            "campaignCount": int(r.get("campaign_count") or 0),
                            "ctr": float(r.get("ctr") or 0.0),
                            "cpc": float(r.get("cpc") or 0.0),
                            "acos": float(r.get("acos") or 0.0),
                            "roas": float(r.get("roas") or 0.0),
                            "cvr": float(r.get("conversion_rate") or 0.0),
                        }
                        for r in asin_df.to_dict(orient="records")
                    ]
            except Exception:  # noqa: BLE001
                asin_rows = []

    return {
        **workbench,
        "analysis": {
            "rowCount": len(rows),
            "typeCounts": type_counts,
            "actionCounts": action_counts,
        },
        "campaignRows": campaign_rows,
        "asinRows": asin_rows,
    }
