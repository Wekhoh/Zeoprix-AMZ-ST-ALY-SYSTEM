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
from src.rules.engine import analyze_search_terms
from src.ui.pages.settings_data import (
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
    return int(db.execute("SELECT COUNT(*) AS count FROM campaigns WHERE product_id = ?", (product_id,)).fetchone()["count"])


def _manual_review_count(db: Database, product_id: int) -> int:
    return int(db.execute("SELECT COUNT(*) AS count FROM manual_reviews WHERE product_id = ?", (product_id,)).fetchone()["count"])


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
        return {"term_count": 0, "total_spend": 0.0, "total_orders": 0, "total_sales": 0.0, "acos": 0.0, "latest_report_date": None}
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

    results = analyze_search_terms(db, product_id)
    stats = {"negative_count": 0, "manual_count": 0, "ai_pending_count": 0, "review_pending_count": 0, "conflict_count": 0}
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


def _build_top_actions(pending_stats: dict[str, int], snapshot_rows: list[dict]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    review_pending = int(pending_stats.get("review_pending_count") or 0)
    negative_pending = int(pending_stats.get("negative_count") or 0)
    manual_pending = int(pending_stats.get("manual_count") or 0)
    conflict_pending = int(pending_stats.get("conflict_count") or 0)

    negative_rows = sorted([r for r in snapshot_rows if str(r.get("action_type", "")).startswith("negative")], key=lambda r: float(r.get("spend") or 0.0), reverse=True)
    manual_rows = sorted([r for r in snapshot_rows if str(r.get("action_type", "")).startswith("manual")], key=lambda r: float(r.get("sales") or 0.0), reverse=True)
    conflict_rows = sorted([r for r in snapshot_rows if str(r.get("action_type", "")) == "conflict"], key=lambda r: float(r.get("spend") or 0.0), reverse=True)

    if review_pending > 0:
        actions.append({"tag": "先审核", "title": f"先处理 {review_pending} 个待审核词", "description": "先把低置信度和分歧词拍板，后面的执行才会稳定。"})
    if negative_pending > 0:
        top = negative_rows[0] if negative_rows else None
        if top:
            actions.append({"tag": "止损优先", "title": f"优先止损：{top.get('term', '高花费词')}", "description": f"花费 ${float(top.get('spend') or 0):.2f}，来源规则：{top.get('triggered_rule') or '最近分析'}。"})
        else:
            actions.append({"tag": "止损优先", "title": f"优先止损 {negative_pending} 个高花费词", "description": "先处理高花费无转化词。"})
    if manual_pending > 0:
        top = manual_rows[0] if manual_rows else None
        if top:
            actions.append({"tag": "补量机会", "title": f"补量词：{top.get('term', '高转化词')}", "description": f"销售额 ${float(top.get('sales') or 0):.2f}，建议动作：{top.get('suggested_action') or '手动补量'}。"})
        else:
            actions.append({"tag": "补量机会", "title": f"补量 {manual_pending} 个高转化词", "description": "止损后优先处理高转化手动机会。"})
    if conflict_pending > 0:
        top = conflict_rows[0] if conflict_rows else None
        actions.append({"tag": "风险处理", "title": f"拍板 {conflict_pending} 个分歧词", "description": f"{top.get('term')} 存在跨结论分歧。" if top else "执行前先稳定分歧词。"})

    return actions[:3] or [{"tag": "继续推进", "title": "先导入或运行分析", "description": "当前还没有足够结果，先建立本轮数据。"}]


def _build_trend(points: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, int | str]]]:
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
    bars = [{"label": p["label"], "value": int(round(float(p["spend"]))) or 1} for p in points[-5:]]
    return cards, bars


def _get_trend_payload(db: Database, product_id: int) -> tuple[list[dict[str, str]], list[dict[str, int | str]]]:
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
        points.append({"label": label, "spend": float(row["spend"] or 0.0), "orders": int(row["orders"] or 0), "sales": float(row["sales"] or 0.0)})
    return _build_trend(points)


def _classify_bucket(term: str, term_type: str, product_config: dict) -> str:
    normalized_term = str(term or "").strip().lower()
    if not normalized_term:
        return "其它长尾"
    own_variants = {str(item).strip().upper() for item in (product_config.get("own_variants") or []) + (product_config.get("own_asins") or []) if str(item).strip()}
    competitor_asins = {str(item).strip().upper() for item in product_config.get("competitor_asins", []) if str(item).strip()}
    if term_type == "asin":
        normalized_asin = normalized_term.upper()
        if normalized_asin in own_variants:
            return "自家变体 ASIN"
        if normalized_asin in competitor_asins:
            return "竞品 ASIN"
        return "其它 ASIN"

    libraries = product_config.get("keyword_libraries") or {}
    generic_keywords = {str(item).strip().lower() for item in libraries.get("generic_keywords", []) if str(item).strip()}
    core_keywords = [str(item).strip().lower() for item in product_config.get("core_keywords", []) if str(item).strip()]
    related_keywords = [str(item).strip().lower() for item in product_config.get("related_keywords", []) if str(item).strip()]
    if normalized_term in generic_keywords:
        return "泛词"
    if any(keyword and keyword in normalized_term for keyword in core_keywords):
        return "核心词"
    if any(keyword and keyword in normalized_term for keyword in related_keywords):
        return "相关词"
    return "其它长尾"


def _get_structure_payload(db: Database, product_id: int, product_config: dict) -> list[dict[str, Any]]:
    rows = _latest_snapshot_rows(db, product_id)
    source_rows = rows if rows else [dict(r) for r in db.execute(
        """
        SELECT DISTINCT st.term, st.term_type
        FROM search_terms st
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ?
        """,
        (product_id,),
    ).fetchall()]
    counts: dict[str, int] = {}
    for row in source_rows:
        bucket = _classify_bucket(row.get("term", ""), row.get("term_type", "keyword"), product_config)
        counts[bucket] = counts.get(bucket, 0) + 1
    total = sum(counts.values()) or 1
    return [{"label": label, "count": count, "ratio": f"{round((count / total) * 100)}%"} for label, count in sorted(counts.items(), key=lambda i: i[1], reverse=True)]


def _get_execution_effect_payload(db: Database, product_id: int) -> dict[str, Any]:
    batches = db.list_execution_batches(product_id, limit=1)
    if not batches:
        return {"status": "暂无批次", "summary": "当前还没有执行批次，先在操作清单里生成一批动作。", "chips": [], "improving": [], "risky": [], "batchCode": None, "batchStatus": None}
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
                "action": row.get("suggested_action") or row.get("action_type") or "观察",
                "spend": f"${float(row.get('spend') or 0.0):.2f}",
                "orders": int(row.get("orders") or 0),
                "confidence": f"{float(row.get('confidence') or 0):.0%}" if isinstance(row.get("confidence"), (int, float)) else str(row.get("confidence") or "-")
            }
            for row in rows[:8]
        ]

    results = analyze_search_terms(db, product_id)
    payload = []
    for result in results[:8]:
        payload.append({
            "term": result.term,
            "type": result.term_type,
            "rule": result.triggered_rule,
            "action": result.suggested_action,
            "spend": f"${float(result.data.get('spend') or result.data.get('total_spend') or 0.0):.2f}",
            "orders": int(result.data.get('orders') or result.data.get('total_orders') or 0),
            "confidence": f"{float(result.confidence):.0%}",
        })
    return payload


def _get_execution_batches_payload(db: Database, product_id: int) -> list[dict[str, Any]]:
    batches = db.list_execution_batches(product_id, limit=5)
    payload = []
    for batch in batches:
        preview = get_execution_batch_effect_preview(db, batch)
        summary = summarize_execution_batch_effect(preview)
        items = (batch.get("summary") or {}).get("items") or []
        payload.append({
            "id": batch.get("id"),
            "code": batch.get("batch_code"),
            "type": batch.get("batch_type"),
            "status": batch.get("status"),
            "itemCount": batch.get("item_count") or len(items),
            "spend": f"${float(((batch.get('summary') or {}).get('spend_total') or 0.0)):.2f}",
            "sales": f"${float(((batch.get('summary') or {}).get('sales_total') or 0.0)):.2f}",
            "verdict": summary.get("status", "待观察"),
            "summary": summary.get("summary", batch.get("draft_note") or "暂无复盘结论。"),
            "improving": summary.get("top_improving_terms", []),
            "risky": summary.get("top_risky_terms", []),
            "itemsPreview": [
                {
                    "term": str(item.get("term") or "未命名词"),
                    "action": str(item.get("suggested_action") or item.get("action_type") or "待执行"),
                    "spend": f"${float(item.get('spend') or 0.0):.2f}",
                }
                for item in items[:5]
            ],
            "itemsDetail": [
                {
                    "term": str(item.get("term") or "未命名词"),
                    "action": str(item.get("suggested_action") or item.get("action_type") or "待执行"),
                    "actionType": str(item.get("action_type") or "pending"),
                    "spend": f"${float(item.get('spend') or 0.0):.2f}",
                    "sales": f"${float(item.get('sales') or 0.0):.2f}",
                }
                for item in items
            ],
        })
    return payload


def _build_execution_batch_summary(db: Database, product_id: int, batch_type: str) -> dict[str, Any]:
    snapshot = _latest_snapshot(db, product_id)
    snapshot_rows = snapshot.get("rows") or [] if snapshot else []
    normalized_batch_type = str(batch_type).strip().lower() or "general"
    if normalized_batch_type == "negative":
        filtered = [row for row in snapshot_rows if str(row.get("action_type", "")).startswith("negative")]
    elif normalized_batch_type == "manual":
        filtered = [row for row in snapshot_rows if str(row.get("action_type", "")).startswith("manual")]
    elif normalized_batch_type == "conflict":
        filtered = [row for row in snapshot_rows if str(row.get("action_type", "")) == "conflict"]
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


def submit_review_decision_for_frontend(
    *,
    product_id: int,
    term: str,
    term_type: str,
    campaign_id: int | None,
    relevance: str,
    notes: str | None = None,
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
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
            return {"status": "warning", "message": "当前导入数据暂时不足以生成搜索词分析结果。", "termsAnalyzed": 0, "resultsSaved": 0}

        engine = RuleEngine(db, product_id)
        results = engine.analyze(df)
        if not results:
            return {"status": "warning", "message": "规则分析已运行，但当前没有生成可保存的建议。", "termsAnalyzed": len(df), "resultsSaved": 0}

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
                failures.append({"fileName": upload_name, "reason": "文件中没有可导入的数据。"})
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
        item_count = int((latest_snapshot.get("summary") or {}).get("item_count") or len(latest_snapshot.get("rows") or []))
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


def _derive_stage_title(pending_stats: dict[str, int], latest_snapshot: dict | None) -> tuple[str, str]:
    if pending_stats.get("negative_count") or pending_stats.get("manual_count") or pending_stats.get("conflict_count"):
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
        top_actions = _build_top_actions(pending_stats, _latest_snapshot_rows(db, product_id))
        trend_cards, trend_bars = _get_trend_payload(db, product_id)
        structure_buckets = _get_structure_payload(db, product_id, product_config)
        execution_effect = _get_execution_effect_payload(db, product_id)
        execution_batches = _get_execution_batches_payload(db, product_id)
        recent_activity = _build_recent_activity(db, product_id, latest_snapshot, execution_batches, pending_stats)
        ops_templates = {
            "boss_summary": f"{product_name} 当前处于「{stage_title}」。最近执行效果判断为「{execution_effect['status']}」，建议今天优先处理：" + "；".join(item['title'] for item in top_actions[:3]),
            "handoff_note": f"【执行交接】先处理：" + "；".join(item['title'] for item in top_actions[:3]),
            "weekly_review": f"【周度复盘】最近执行效果：{execution_effect['status']}；改善线索：{'、'.join(execution_effect.get('improving') or ['暂无'])}；仍需关注：{'、'.join(execution_effect.get('risky') or ['暂无'])}",
        }

        return {
            "source": "live",
            "productId": product_id,
            "productContext": {
                "name": product_name,
                "role": (workspace_summary.get("current_role") or "viewer").capitalize(),
                "workspace": f"{product_name}工作区",
                "lastAnalysisAt": _format_timestamp(latest_snapshot.get("created_at") if latest_snapshot else None),
                "lastBackupAt": "暂无完整备份",
            },
            "workbenchStats": [
                {"label": "当前阶段", "value": stage_title, "detail": stage_detail},
                {"label": "最近一次分析", "value": _format_timestamp(latest_snapshot.get("created_at") if latest_snapshot else None).replace(" ", " · ", 1), "detail": "latest snapshot 已形成。" if latest_snapshot else "还没有分析快照。"},
                {"label": "历史沉淀", "value": f"{len(db.list_analysis_run_snapshots(product_id, limit=200))} 个分析快照", "detail": f"{_manual_review_count(db, product_id)} 条人工审核、{len(db.list_execution_batches(product_id, limit=200))} 个执行批次。"},
                {"label": "数据规模", "value": f"{stats['term_count']} 条词 · {_campaign_count(db, product_id)} 个活动", "detail": f"当前已形成 {_analysis_result_count(db, product_id)} 条建议动作。"},
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
                    "summary": top_actions[0]["description"] if top_actions else "先导入数据或运行分析。",
                    "prompts": ["解释 ACOS 为什么高", "给我 3 个最优先动作", "生成老板摘要"],
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
        campaigns = [dict(row) for row in db.execute("SELECT id, name, created_at FROM campaigns WHERE product_id = ? ORDER BY created_at DESC LIMIT 5", (product_id,)).fetchall()]
        return {
            **workbench,
            "upload": {
                "latestReportDate": stats.get("latest_report_date") or "暂无导入",
                "searchTerms": stats["term_count"],
                "campaigns": _campaign_count(db, product_id),
                "snapshotCount": len(db.list_analysis_run_snapshots(product_id, limit=200)),
                "recentSnapshots": [
                    {"id": s["id"], "createdAt": _format_timestamp(s["created_at"]), "itemCount": int((s.get("summary") or {}).get("item_count") or len(s.get("rows") or []))}
                    for s in snapshots
                ],
                "recentCampaigns": [{"id": c["id"], "name": c["name"], "createdAt": _format_timestamp(c["created_at"])} for c in campaigns],
            },
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
        "related_keywords": [item.strip() for item in related_keywords if str(item).strip()],
        "competitor_asins": [item.strip().upper() for item in competitor_asins if str(item).strip()],
        "own_variants": [item.strip().upper() for item in own_variants if str(item).strip()],
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


def restore_settings_rule_version_for_frontend(*, product_id: int, version: int) -> dict[str, Any]:
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


def preview_settings_rule_version_for_frontend(*, product_id: int, version: int) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = db.get_product(product_id)
        if not product:
            raise ValueError("产品不存在")

        snapshot = db.get_rule_version_snapshot(product_id, version)
        if not snapshot:
            raise ValueError("指定规则版本不存在")

        current_config = product.get("config") or {}
        snapshot_core = [str(item).strip() for item in snapshot.get("core_keywords", []) if str(item).strip()]
        snapshot_related = [str(item).strip() for item in snapshot.get("related_keywords", []) if str(item).strip()]
        snapshot_competitors = [str(item).strip().upper() for item in snapshot.get("competitor_asins", []) if str(item).strip()]
        snapshot_variants = [str(item).strip().upper() for item in snapshot.get("own_variants", []) if str(item).strip()]

        current_core = [str(item).strip() for item in current_config.get("core_keywords", []) if str(item).strip()]
        current_related = [str(item).strip() for item in current_config.get("related_keywords", []) if str(item).strip()]
        current_competitors = [str(item).strip().upper() for item in current_config.get("competitor_asins", []) if str(item).strip()]
        current_variants = [str(item).strip().upper() for item in current_config.get("own_variants", []) if str(item).strip()]

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


def build_actions_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        pending_stats = _get_pending_stats(db, product_id)
        return {
            **workbench,
            "actions": {
                "negativeCount": int(pending_stats.get("negative_count") or 0),
                "manualCount": int(pending_stats.get("manual_count") or 0),
                "conflictCount": int(pending_stats.get("conflict_count") or 0),
                "latestBatchCode": (workbench.get("executionBatches") or [{}])[0].get("code"),
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
        type_counts[row.get("type") or "unknown"] = type_counts.get(row.get("type") or "unknown", 0) + 1
        action_counts[row.get("action") or "unknown"] = action_counts.get(row.get("action") or "unknown", 0) + 1
    return {
        **workbench,
        "analysis": {
            "rowCount": len(rows),
            "typeCounts": type_counts,
            "actionCounts": action_counts,
        },
    }
