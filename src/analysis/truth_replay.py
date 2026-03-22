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


def _infer_term_type(value: Any, fallback_term: str) -> str:
    text = _normalize_text(value)
    if "ASIN" in text.upper() or is_valid_asin(fallback_term):
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

    workbook = pd.ExcelFile(path)
    rows: list[dict[str, Any]] = []
    relevant_sheets = workbook.sheet_names[:2]

    for sheet_name in relevant_sheets:
        df = pd.read_excel(path, sheet_name=sheet_name)
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
