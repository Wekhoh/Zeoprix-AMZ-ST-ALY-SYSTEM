"""Workbench mutation 模块 — Step 3 H2 抽出（review / batch 类）。

把 review/batch 类的 5 个写入函数从 workbench_payload.py 剥离：
  - _build_execution_batch_summary   (helper, 仅本模块 + truth_replay 准备)
  - create_execution_batch_for_frontend
  - update_execution_batch_for_frontend
  - _check_decision_conflicts        (Sprint A.4 helper, 测试直接 import)
  - submit_review_decision_for_frontend

为保持外部调用方（app.py / tests）不感知，本拆分通过
workbench_payload.py 末尾的 re-export 维持兼容；新代码可直接从
workbench_mutations import 拿。

后续 sprint (H3) 再续抽 upload/clear/backup/settings 类。
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from src.analysis.truth_replay import (
    get_execution_batch_effect_preview,
    summarize_execution_batch_effect,
)
from src.backend.workbench_payload import (
    _format_timestamp,
    _get_app_database_path,
    _latest_snapshot,
)
from src.data.db import Database


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
