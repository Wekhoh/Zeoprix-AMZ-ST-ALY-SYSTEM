"""已审核真相回放：导入 workbook 真相并覆盖系统分析结果。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.db import Database
from src.data.models import ActionType
from src.rules.asin_rules import is_valid_asin

REVIEW_SOURCE_PRIORITY = {
    "upload_pending": 0,
    "aggregate_truth": 20,
    "campaign_truth": 30,
    "ui_review": 40,
}

CAMPAIGN_SHEET_ALIASES = {
    "asin_identifier": ("ASIN", "asin", "asin_identifier"),
    "campaign_name": ("广告组", "campaign_name", "campaign"),
    "term": ("关键词", "keyword", "term"),
    "plan": ("操作计划", "plan", "action_plan"),
}

AGGREGATE_ROW_ALIASES = {
    "term_type": ("Term类型", "term_type"),
    "relevance": ("相关性", "relevance"),
    "term": ("关键词", "Keyword", "keyword", "term"),
    "manual_action": ("手动动作", "manual_action"),
    "auto_action": ("自动动作", "auto_action"),
    "negate_keyword": ("否定关键词", "negate_keyword"),
    "negate_asin": ("否ASIN", "negate_asin"),
    "rule_trigger": ("规则触发", "rule_trigger"),
    "action_matrix": ("备注动作矩阵", "action_matrix"),
    "campaign_summary": ("活动表现汇总", "campaign_summary"),
    "campaign_conflict": ("活动分歧", "campaign_conflict"),
    "decision_source": ("判断来源", "decision_source"),
    "conflict": ("冲突", "conflict"),
    "original_notes": ("各活动原始备注", "original_notes"),
}

AGGREGATE_ROW_FALLBACK_INDEX = {
    "term_type": 0,
    "relevance": 1,
    "term": 2,
    "manual_action": 11,
    "auto_action": 12,
    "negate_keyword": 13,
    "negate_asin": 14,
    "rule_trigger": 15,
    "action_matrix": 16,
    "campaign_summary": 17,
    "campaign_conflict": 18,
    "decision_source": 19,
    "conflict": 20,
    "original_notes": 21,
}


def _normalize_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _normalize_term(term: Any) -> str:
    return _normalize_text(term).lower()


def _first_row_value(row: pd.Series, aliases: tuple[str, ...], fallback_index: int) -> Any:
    for alias in aliases:
        if alias in row.index:
            return row[alias]
    if len(row.index) > fallback_index:
        return row.iloc[fallback_index]
    return None


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    text_lower = text.lower()
    return any(needle.lower() in text_lower for needle in needles)


def _campaign_plan_to_action_type(plan: Any) -> str:
    value = _normalize_text(plan)
    if not value:
        return ActionType.OBSERVE
    if "自动直接否定精准" in value or "直接否定精准" in value:
        return ActionType.NEGATIVE_EXACT
    if "手动精准" in value and (
        "Neg Exact" in value or ("自动否" in value and "先不" not in value)
    ):
        return ActionType.MANUAL_EXACT_WITH_NEG
    if "手动精准" in value and ("先不否" in value or "自动先不" in value):
        return ActionType.MANUAL_EXACT_NO_NEG
    if "手动精准" in value or "去拉手动精准" in value:
        return ActionType.MANUAL_EXACT_NO_NEG
    if "手动商品定位" in value:
        if "Neg Product" in value or ("自动否" in value and "先不" not in value):
            return ActionType.MANUAL_PRODUCT_WITH_NEG
        return ActionType.MANUAL_PRODUCT_NO_NEG
    if "否定词组" in value:
        return ActionType.NEGATIVE_PHRASE
    if "继续观察" in value or value.startswith("观察") or "样本不足" in value:
        return ActionType.CONTINUE_OBSERVE
    return ActionType.OBSERVE


def _aggregate_row_to_action_type(row: dict[str, Any]) -> str:
    manual_action = _normalize_text(row.get("manual_action"))
    auto_action = _normalize_text(row.get("auto_action"))
    negate_keyword = _normalize_text(row.get("negate_keyword"))
    negate_asin = _normalize_text(row.get("negate_asin"))
    action_matrix = _normalize_text(row.get("action_matrix"))
    original_notes = _normalize_text(row.get("original_notes"))

    if "手动商品定位" in manual_action:
        if _contains_any(negate_asin, ("Neg Product",)) or _contains_any(
            auto_action, ("直接否", "自动否")
        ):
            return ActionType.MANUAL_PRODUCT_WITH_NEG
        return ActionType.MANUAL_PRODUCT_NO_NEG

    if "手动精准" in manual_action:
        if _contains_any(negate_keyword, ("Neg Exact",)) or _contains_any(
            auto_action, ("直接否", "自动否")
        ):
            return ActionType.MANUAL_EXACT_WITH_NEG
        return ActionType.MANUAL_EXACT_NO_NEG

    if _contains_any(negate_asin, ("Neg Product",)):
        return ActionType.NEGATIVE_EXACT
    if _contains_any(negate_keyword, ("Neg Exact",)):
        return ActionType.NEGATIVE_EXACT
    if _contains_any(auto_action, ("否定词组",)):
        return ActionType.NEGATIVE_PHRASE
    if _contains_any(auto_action, ("观察", "继续观察", "暂不")):
        return ActionType.CONTINUE_OBSERVE

    for text in (action_matrix, original_notes):
        inferred = _campaign_plan_to_action_type(text)
        if inferred != ActionType.OBSERVE:
            return inferred

    return ActionType.CONTINUE_OBSERVE


def action_type_to_label(action_type: str) -> str:
    mapping = {
        ActionType.NEGATIVE_EXACT: "否定精准",
        ActionType.NEGATIVE_PHRASE: "否定词组",
        ActionType.MANUAL_EXACT: "手动精准",
        ActionType.MANUAL_EXACT_NO_NEG: "手动精准",
        ActionType.MANUAL_EXACT_WITH_NEG: "手动精准",
        ActionType.MANUAL_PRODUCT: "手动商品定位",
        ActionType.MANUAL_PRODUCT_NO_NEG: "手动商品定位",
        ActionType.MANUAL_PRODUCT_WITH_NEG: "手动商品定位",
        ActionType.CONTINUE_OBSERVE: "观察",
        ActionType.OBSERVE: "观察",
        ActionType.EVALUATE: "评估",
    }
    return mapping.get(action_type, "观察")


def action_type_to_auto_action(action_type: str) -> str:
    if action_type in {
        ActionType.NEGATIVE_EXACT,
        ActionType.NEGATIVE_PHRASE,
        ActionType.MANUAL_EXACT_WITH_NEG,
        ActionType.MANUAL_PRODUCT_WITH_NEG,
    }:
        return "negate"
    if action_type in {
        ActionType.MANUAL_EXACT,
        ActionType.MANUAL_EXACT_NO_NEG,
        ActionType.MANUAL_PRODUCT,
        ActionType.MANUAL_PRODUCT_NO_NEG,
    }:
        return "keep"
    return "observe"


def _review_sort_key(review: dict[str, Any]) -> tuple[int, str]:
    return (
        REVIEW_SOURCE_PRIORITY.get(review.get("review_source") or "", 0),
        review.get("updated_at") or "",
    )


def _build_truth_lookup(db: Database, product_id: int) -> tuple[dict, dict, dict]:
    reviews = db.get_reviewed_truth_rows(product_id=product_id)
    global_truth: dict[str, dict[str, Any]] = {}
    campaign_truth: dict[tuple[str, int], dict[str, Any]] = {}
    asin_truth: dict[tuple[str, str], dict[str, Any]] = {}

    for review in reviews:
        action_type = review.get("truth_action_type")
        if not action_type:
            continue

        term_key = _normalize_term(review.get("term"))
        if not term_key:
            continue

        campaign_id = review.get("campaign_id")
        asin_identifier = _normalize_text(review.get("asin_identifier"))
        if campaign_id is None:
            if asin_identifier:
                asin_key = (term_key, asin_identifier)
                current = asin_truth.get(asin_key)
                if current is None or _review_sort_key(review) >= _review_sort_key(current):
                    asin_truth[asin_key] = review
                continue
            current = global_truth.get(term_key)
            if current is None or _review_sort_key(review) >= _review_sort_key(current):
                global_truth[term_key] = review
            continue

        key = (term_key, campaign_id)
        current = campaign_truth.get(key)
        if current is None or _review_sort_key(review) >= _review_sort_key(current):
            campaign_truth[key] = review

    return global_truth, campaign_truth, asin_truth


def apply_reviewed_truth(
    db: Database,
    product_id: int,
    results: list[Any],
) -> list[Any]:
    """对分析结果应用 reviewed truth 覆盖。"""
    if not product_id or not results:
        return results

    global_truth, campaign_truth, asin_truth = _build_truth_lookup(db, product_id)
    overridden = []

    for result in results:
        term_key = _normalize_term(getattr(result, "term", ""))
        campaign_id = getattr(result, "campaign_id", None)
        asin_identifier = _normalize_text(getattr(result, "asin_identifier", ""))
        review = None
        if campaign_id is not None:
            review = campaign_truth.get((term_key, campaign_id))
        if review is None and asin_identifier:
            review = asin_truth.get((term_key, asin_identifier))
        if review is None:
            review = global_truth.get(term_key)

        if review is None:
            overridden.append(result)
            continue

        action_type = review.get("truth_action_type") or getattr(result, "action_type", "")
        replay_data = {
            "review_id": review.get("id"),
            "review_source": review.get("review_source"),
            "manual_action": review.get("manual_action"),
            "auto_action": review.get("auto_action"),
            "negate_keyword": review.get("negate_keyword"),
            "negate_asin": review.get("negate_asin"),
            "conflict_flag": bool(review.get("conflict_flag")),
        }
        original_data = getattr(result, "data", {}) or {}
        new_data = {
            **original_data,
            "truth_replay": replay_data,
        }

        replacements = {
            "triggered_rule": "人工已审核回放",
            "suggested_action": action_type_to_label(action_type),
            "action_type": action_type,
            "confidence": 1.0,
            "data": new_data,
        }

        if hasattr(result, "need_ai_judgment"):
            replacements["need_ai_judgment"] = False
        if hasattr(result, "ai_reasoning"):
            replacements["ai_reasoning"] = None
        if hasattr(result, "needs_review"):
            replacements["needs_review"] = False
        if hasattr(result, "relevance") and review.get("relevance"):
            replacements["relevance"] = review.get("relevance")
        if hasattr(result, "auto_action"):
            replacements["auto_action"] = action_type_to_auto_action(action_type)

        overridden.append(replace(result, **replacements))

    return overridden


def has_reviewed_truth(db: Database, product_id: int) -> bool:
    """判断产品是否已导入 reviewed truth。"""
    if not product_id:
        return False
    cursor = db.execute(
        """
        SELECT 1
        FROM manual_reviews
        WHERE product_id = ?
          AND reviewed = 1
          AND truth_action_type IS NOT NULL
        LIMIT 1
        """,
        (product_id,),
    )
    return cursor.fetchone() is not None


def _truth_item_priority(item: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        float(item.get("orders", 0) or 0),
        float(item.get("sales", 0) or 0),
        float(item.get("clicks", 0) or 0),
        float(item.get("spend", 0) or 0),
    )


def _dedupe_truth_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        key = _normalize_term(item.get("term"))
        if not key:
            continue
        current = deduped.get(key)
        if current is None or _truth_item_priority(item) > _truth_item_priority(current):
            deduped[key] = item

    return sorted(
        deduped.values(),
        key=lambda item: (
            -float(item.get("orders", 0) or 0),
            -float(item.get("sales", 0) or 0),
            -float(item.get("clicks", 0) or 0),
            -float(item.get("spend", 0) or 0),
            item.get("term", ""),
        ),
    )


def get_truth_first_action_buckets(
    db: Database,
    product_id: int,
) -> dict[str, list[dict[str, Any]]] | None:
    """基于 reviewed truth 生成 truth-first 操作清单分桶。"""
    if not has_reviewed_truth(db, product_id):
        return None

    from src.rules.engine import analyze_search_terms_by_asin

    results = analyze_search_terms_by_asin(db, product_id)
    grouped_results: dict[str, list[Any]] = {}
    for result in results:
        truth_data = (getattr(result, "data", {}) or {}).get("truth_replay")
        if not truth_data:
            continue
        term_key = _normalize_term(getattr(result, "term", ""))
        if not term_key:
            continue
        grouped_results.setdefault(term_key, []).append(result)

    conflict_terms = {
        term_key
        for term_key, items in grouped_results.items()
        if len({getattr(item, "action_type", "") for item in items}) > 1
    }

    negative_exact_items: list[dict[str, Any]] = []
    negative_phrase_items: list[dict[str, Any]] = []
    negative_asin_items: list[dict[str, Any]] = []
    manual_keyword_items: list[dict[str, Any]] = []
    manual_product_items: list[dict[str, Any]] = []

    for result in results:
        truth_data = (getattr(result, "data", {}) or {}).get("truth_replay")
        if not truth_data:
            continue
        term_key = _normalize_term(getattr(result, "term", ""))
        if not term_key or term_key in conflict_terms:
            continue

        item = {
            "term": result.term,
            "term_type": result.term_type,
            "asin_identifier": getattr(result, "asin_identifier", None),
            "triggered_rule": result.triggered_rule,
            "suggested_action": result.suggested_action,
            "action_type": result.action_type,
            "auto_action": getattr(result, "auto_action", None)
            or truth_data.get("auto_action"),
            "confidence": result.confidence,
            "spend": result.data.get("total_spend", result.data.get("spend", 0)),
            "clicks": result.data.get("total_clicks", result.data.get("clicks", 0)),
            "orders": result.data.get("total_orders", result.data.get("orders", 0)),
            "sales": result.data.get("total_sales", result.data.get("sales", 0)),
            "truth_replay": truth_data,
        }
        negate_keyword = _normalize_text(truth_data.get("negate_keyword"))
        negate_asin = _normalize_text(truth_data.get("negate_asin"))

        is_asin_term = result.term_type == "asin" or is_valid_asin(
            _normalize_text(result.term).upper()
        )

        if is_asin_term:
            if ActionType.is_manual(result.action_type):
                manual_product_items.append(item)
            if negate_asin or ActionType.is_negative(result.action_type):
                negative_asin_items.append(item)
            continue

        if ActionType.is_manual(result.action_type):
            manual_keyword_items.append(item)

        if "Neg Exact" in negate_keyword or result.action_type == ActionType.MANUAL_EXACT_WITH_NEG:
            negative_exact_items.append(item)
        elif (
            result.action_type == ActionType.NEGATIVE_PHRASE
            or "词组" in result.suggested_action
        ):
            negative_phrase_items.append(item)
        elif ActionType.is_negative(result.action_type):
            negative_exact_items.append(item)

    return {
        "negative_keyword_exact": _dedupe_truth_items(negative_exact_items),
        "negative_keyword_phrase": _dedupe_truth_items(negative_phrase_items),
        "negative_asin": _dedupe_truth_items(negative_asin_items),
        "manual_keywords": _dedupe_truth_items(manual_keyword_items),
        "manual_products": _dedupe_truth_items(manual_product_items),
    }


def get_truth_first_pending_stats(db: Database, product_id: int) -> dict[str, int] | None:
    """返回 truth-first 首页待处理统计。"""
    buckets = get_truth_first_action_buckets(db, product_id)
    if buckets is None:
        return None

    pending_counts = db.get_pending_reviews_count(product_id)
    summary_rows = get_truth_first_summary_rows(db, product_id) or []
    return {
        "negative_count": (
            len(buckets["negative_keyword_exact"])
            + len(buckets["negative_keyword_phrase"])
            + len(buckets["negative_asin"])
        ),
        "manual_count": len(buckets["manual_keywords"])
        + len(buckets["manual_products"]),
        "conflict_count": sum(
            1 for row in summary_rows if row.get("action_type") == "conflict"
        ),
        "ai_pending_count": pending_counts["total"],
        "review_pending_count": pending_counts["total"],
    }


def get_truth_first_overview_distribution(
    db: Database,
    product_id: int,
) -> dict[str, int] | None:
    """返回首页 truth-first 数据概览分布。"""
    summary_rows = get_truth_first_summary_rows(db, product_id)
    if summary_rows is None:
        return None

    distribution = {
        "继续观察-关键词": 0,
        "继续观察-ASIN": 0,
        "手动精准-关键词": 0,
        "手动商品定位-ASIN": 0,
        "否定精准-关键词": 0,
        "否定词组-关键词": 0,
        "否定ASIN": 0,
        "跨ASIN分歧": 0,
    }

    for row in summary_rows:
        term_type = row.get("term_type")
        action_type = row.get("action_type")

        if row.get("has_conflict"):
            distribution["跨ASIN分歧"] += 1
            continue

        if action_type in {ActionType.CONTINUE_OBSERVE, ActionType.OBSERVE}:
            if term_type == "asin":
                distribution["继续观察-ASIN"] += 1
            else:
                distribution["继续观察-关键词"] += 1
            continue

        if ActionType.is_manual(action_type):
            if term_type == "asin":
                distribution["手动商品定位-ASIN"] += 1
            else:
                distribution["手动精准-关键词"] += 1
            continue

        if action_type == ActionType.NEGATIVE_PHRASE:
            distribution["否定词组-关键词"] += 1
            continue

        if ActionType.is_negative(action_type):
            if term_type == "asin":
                distribution["否定ASIN"] += 1
            else:
                distribution["否定精准-关键词"] += 1

    return distribution


def _summary_conflict_details(items: list[Any]) -> str:
    details = []
    for item in sorted(items, key=lambda row: row.asin_identifier or ""):
        label = action_type_to_label(item.action_type)
        asin_identifier = _normalize_text(getattr(item, "asin_identifier", "")) or "未知ASIN"
        details.append(f"{asin_identifier}: {label}")
    return " | ".join(details)


def _truth_summary_priority(item: Any) -> tuple[int, float, float, float]:
    action_type = getattr(item, "action_type", "")
    if ActionType.is_negative(action_type):
        priority = 3
    elif ActionType.is_manual(action_type):
        priority = 2
    else:
        priority = 1

    data = getattr(item, "data", {}) or {}
    return (
        priority,
        float(data.get("total_orders", data.get("orders", 0)) or 0),
        float(data.get("total_clicks", data.get("clicks", 0)) or 0),
        float(data.get("total_spend", data.get("spend", 0)) or 0),
    )


def get_truth_first_summary_rows(
    db: Database,
    product_id: int,
) -> list[dict[str, Any]] | None:
    """生成 truth-first 汇总模式视图（跨 ASIN 折叠到唯一 term）。"""
    if not has_reviewed_truth(db, product_id):
        return None

    from src.rules.engine import analyze_search_terms_by_asin

    grouped: dict[str, list[Any]] = {}
    for result in analyze_search_terms_by_asin(db, product_id):
        truth_data = (getattr(result, "data", {}) or {}).get("truth_replay")
        if not truth_data:
            continue
        term_key = _normalize_term(getattr(result, "term", ""))
        if not term_key:
            continue
        grouped.setdefault(term_key, []).append(result)

    summary_rows: list[dict[str, Any]] = []
    for items in grouped.values():
        primary = max(items, key=_truth_summary_priority)
        asin_identifiers = sorted(
            {
                _normalize_text(getattr(item, "asin_identifier", ""))
                for item in items
                if _normalize_text(getattr(item, "asin_identifier", ""))
            }
        )
        action_types = {getattr(item, "action_type", "") for item in items}
        has_conflict = len(action_types) > 1
        total_clicks = sum(float(getattr(item, "clicks", 0) or 0) for item in items)
        total_orders = sum(float(getattr(item, "orders", 0) or 0) for item in items)
        total_spend = sum(float(getattr(item, "spend", 0) or 0) for item in items)
        total_sales = sum(float(getattr(item, "sales", 0) or 0) for item in items)
        cvr = total_orders / total_clicks if total_clicks > 0 else 0.0
        acos = total_spend / total_sales if total_sales > 0 else 0.0

        if has_conflict:
            action_type = "conflict"
            suggested_action = "跨ASIN分歧"
            triggered_rule = "人工已审核回放（跨ASIN分歧）"
            action_detail = _summary_conflict_details(items)
        else:
            action_type = primary.action_type
            suggested_action = primary.suggested_action
            triggered_rule = primary.triggered_rule
            action_detail = action_type_to_label(primary.action_type)

        summary_rows.append(
            {
                "term": primary.term,
                "term_type": primary.term_type,
                "asin_identifiers": asin_identifiers,
                "asin_count": len(asin_identifiers),
                "triggered_rule": triggered_rule,
                "suggested_action": suggested_action,
                "action_type": action_type,
                "action_detail": action_detail,
                "confidence": 1.0,
                "reviewed": True,
                "has_conflict": has_conflict,
                "clicks": int(total_clicks),
                "orders": int(total_orders),
                "spend": total_spend,
                "sales": total_sales,
                "cvr": cvr,
                "acos": acos,
            }
        )

    return sorted(
        summary_rows,
        key=lambda item: (
            item["has_conflict"] is False,
            item["term_type"] != "asin",
            item["term"],
        ),
    )


def get_truth_first_campaign_rows(
    db: Database,
    product_id: int,
) -> list[dict[str, Any]] | None:
    """返回广告组级 truth-first 视图，仅包含 campaign truth 行。"""
    if not has_reviewed_truth(db, product_id):
        return None

    from src.rules.engine import analyze_search_terms_by_campaign

    rows: list[dict[str, Any]] = []
    for result in analyze_search_terms_by_campaign(db, product_id):
        truth_data = (getattr(result, "data", {}) or {}).get("truth_replay")
        if not truth_data or truth_data.get("review_source") != "campaign_truth":
            continue

        rows.append(
            {
                "term": result.term,
                "term_type": result.term_type,
                "campaign_id": result.campaign_id,
                "campaign_name": result.campaign_name,
                "triggered_rule": result.triggered_rule,
                "suggested_action": result.suggested_action,
                "auto_action": getattr(result, "auto_action", None),
                "action_type": result.action_type,
                "confidence": result.confidence,
                "clicks": getattr(result, "clicks", 0),
                "orders": getattr(result, "orders", 0),
                "spend": getattr(result, "spend", 0.0),
                "sales": getattr(result, "sales", 0.0),
                "cvr": getattr(result, "cvr", 0.0),
                "acos": getattr(result, "acos", 0.0),
                "reviewed": True,
                "truth_replay": truth_data,
            }
        )

    return sorted(
        rows,
        key=lambda item: (
            {"negate": 0, "keep": 1, "observe": 2}.get(item.get("auto_action"), 3),
            item.get("campaign_name", ""),
            item.get("term", ""),
        ),
    )


def _infer_term_type(value: Any, fallback_term: str) -> str:
    text = _normalize_text(value)
    if "ASIN" in text.upper() or is_valid_asin(_normalize_text(fallback_term).upper()):
        return "asin"
    return "keyword"


def load_campaign_truth_rows(workbook_path: str | Path) -> list[dict[str, Any]]:
    path = Path(workbook_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"广告组 truth workbook 不存在: {path}")

    df = pd.read_excel(path)
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        campaign_name = _normalize_text(
            _first_row_value(row, CAMPAIGN_SHEET_ALIASES["campaign_name"], 1)
        )
        term = _normalize_term(_first_row_value(row, CAMPAIGN_SHEET_ALIASES["term"], 2))
        plan = _normalize_text(_first_row_value(row, CAMPAIGN_SHEET_ALIASES["plan"], 3))
        asin_identifier = _normalize_text(
            _first_row_value(row, CAMPAIGN_SHEET_ALIASES["asin_identifier"], 0)
        )
        if not campaign_name or not term:
            continue

        rows.append(
            {
                "asin_identifier": asin_identifier,
                "campaign_name": campaign_name,
                "term": term,
                "term_type": "asin" if is_valid_asin(term) else "keyword",
                "truth_action_type": _campaign_plan_to_action_type(plan),
                "notes": plan,
                "review_source": "campaign_truth",
            }
        )
    return rows


def load_aggregate_truth_rows(workbook_path: str | Path) -> list[dict[str, Any]]:
    path = Path(workbook_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"汇总 truth workbook 不存在: {path}")

    rows: list[dict[str, Any]] = []
    with pd.ExcelFile(path) as workbook:
        relevant_sheets = workbook.sheet_names[:2]

        for sheet_name in relevant_sheets:
            df = workbook.parse(sheet_name)
            asin_identifier = sheet_name.split("汇")[0].strip()

            for _, row in df.iterrows():
                row_dict = {
                    key: _first_row_value(row, aliases, AGGREGATE_ROW_FALLBACK_INDEX[key])
                    for key, aliases in AGGREGATE_ROW_ALIASES.items()
                }
                term = _normalize_term(row_dict["term"])
                if not term:
                    continue

                term_type = _infer_term_type(row_dict["term_type"], term)
                truth_action_type = _aggregate_row_to_action_type(row_dict)
                rows.append(
                    {
                        "asin_identifier": asin_identifier,
                        "term": term,
                        "term_type": term_type,
                        "relevance": _normalize_text(row_dict["relevance"]) or None,
                        "manual_action": _normalize_text(row_dict["manual_action"]) or None,
                        "auto_action": _normalize_text(row_dict["auto_action"]) or None,
                        "negate_keyword": _normalize_text(row_dict["negate_keyword"]) or None,
                        "negate_asin": _normalize_text(row_dict["negate_asin"]) or None,
                        "rule_trigger": _normalize_text(row_dict["rule_trigger"]) or None,
                        "action_matrix": _normalize_text(row_dict["action_matrix"]) or None,
                        "campaign_summary": _normalize_text(row_dict["campaign_summary"]) or None,
                        "campaign_conflict": _normalize_text(row_dict["campaign_conflict"]) or None,
                        "decision_source": _normalize_text(row_dict["decision_source"]) or None,
                        "conflict_flag": bool(_normalize_text(row_dict["conflict"])),
                        "original_notes": _normalize_text(row_dict["original_notes"]) or None,
                        "truth_action_type": truth_action_type,
                        "review_source": "aggregate_truth",
                    }
                )
    return rows


def import_campaign_truth(
    db: Database,
    product_id: int,
    workbook_path: str | Path,
) -> dict[str, int]:
    """导入广告组级 truth 到 manual_reviews。"""
    rows = load_campaign_truth_rows(workbook_path)
    campaigns = db.execute(
        "SELECT id, name FROM campaigns WHERE product_id = ?",
        (product_id,),
    ).fetchall()
    campaign_lookup = {
        _normalize_text(row["name"]).lower(): row["id"] for row in campaigns if row["name"]
    }

    imported = 0
    missing_campaigns = 0
    for row in rows:
        campaign_id = campaign_lookup.get(_normalize_text(row["campaign_name"]).lower())
        if campaign_id is None:
            missing_campaigns += 1
            continue

        db.upsert_manual_review(
            product_id=product_id,
            term=row["term"],
            term_type=row["term_type"],
            campaign_id=campaign_id,
            final_action=action_type_to_label(row["truth_action_type"]),
            reviewed=True,
            notes=row["notes"],
            review_source=row["review_source"],
            truth_action_type=row["truth_action_type"],
            evidence_payload={
                "asin_identifier": row["asin_identifier"],
                "campaign_name": row["campaign_name"],
                "notes": row["notes"],
            },
        )
        imported += 1

    return {"campaign_rows": imported, "campaign_missing": missing_campaigns}


def import_aggregate_truth(
    db: Database,
    product_id: int,
    workbook_path: str | Path,
) -> dict[str, int]:
    """导入汇总级 truth 到 manual_reviews。"""
    rows = load_aggregate_truth_rows(workbook_path)
    imported = 0

    for row in rows:
        competition_level = None
        if row["term_type"] == "asin":
            if row["truth_action_type"] == ActionType.NEGATIVE_EXACT:
                competition_level = "cannot_compete"
            elif row["truth_action_type"] in {
                ActionType.MANUAL_PRODUCT,
                ActionType.MANUAL_PRODUCT_NO_NEG,
                ActionType.MANUAL_PRODUCT_WITH_NEG,
            }:
                competition_level = "can_compete"
            else:
                competition_level = "need_observe"

        db.upsert_manual_review(
            product_id=product_id,
            term=row["term"],
            term_type=row["term_type"],
            campaign_id=None,
            asin_identifier=row["asin_identifier"],
            final_action=action_type_to_label(row["truth_action_type"]),
            reviewed=True,
            notes=row["original_notes"],
            relevance=row["relevance"],
            competition_level=competition_level,
            review_source=row["review_source"],
            truth_action_type=row["truth_action_type"],
            manual_action=row["manual_action"],
            auto_action=row["auto_action"],
            negate_keyword=row["negate_keyword"],
            negate_asin=row["negate_asin"],
            action_matrix=row["action_matrix"],
            conflict_flag=row["conflict_flag"],
            evidence_payload={
                "asin_identifier": row["asin_identifier"],
                "rule_trigger": row["rule_trigger"],
                "campaign_summary": row["campaign_summary"],
                "campaign_conflict": row["campaign_conflict"],
                "decision_source": row["decision_source"],
                "original_notes": row["original_notes"],
            },
        )
        imported += 1

    return {"aggregate_rows": imported}


def seed_truth_workbooks(
    db: Database,
    product_id: int,
    campaign_workbook_path: str | Path | None = None,
    aggregate_workbook_path: str | Path | None = None,
) -> dict[str, int]:
    """导入已审核 truth workbook，并用于后续回放。"""
    summary = {
        "campaign_rows": 0,
        "campaign_missing": 0,
        "aggregate_rows": 0,
    }

    if campaign_workbook_path:
        summary.update(import_campaign_truth(db, product_id, campaign_workbook_path))
    if aggregate_workbook_path:
        summary.update(import_aggregate_truth(db, product_id, aggregate_workbook_path))
    return summary

