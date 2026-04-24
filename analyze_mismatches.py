"""对比 workbook 真相与系统当前有效结果的对齐情况。"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.analysis.truth_replay import (  # noqa: E402
    load_aggregate_truth_rows,
    load_campaign_truth_rows,
)
from src.config.settings import Settings  # noqa: E402
from src.data.db import Database  # noqa: E402
from src.rules.engine import (  # noqa: E402
    analyze_search_terms_by_asin,
    analyze_search_terms_by_campaign,
)

DEFAULT_CAMPAIGN_WORKBOOK = Path(
    r"C:\Users\jackl\OneDrive\桌面\否词TODO\广告组级别的否词和搜索词分析.xlsx"
)
DEFAULT_AGGREGATE_WORKBOOK = Path(
    r"C:\Users\jackl\OneDrive\桌面\否词TODO\ASIN层面汇总分析_v7.xlsx"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="分析 workbook 真相与系统结果的差异。")
    parser.add_argument(
        "--campaign-workbook",
        type=Path,
        default=DEFAULT_CAMPAIGN_WORKBOOK,
        help="广告组级人工校验 workbook。",
    )
    parser.add_argument(
        "--aggregate-workbook",
        type=Path,
        default=DEFAULT_AGGREGATE_WORKBOOK,
        help="汇总级人工校验 workbook。",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="SQLite 数据库路径；默认使用项目配置中的 database_path。",
    )
    parser.add_argument(
        "--product-id",
        type=int,
        default=1,
        help="用于分析的产品 ID。",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="可选：将 mismatch 明细导出为 CSV。",
    )
    return parser.parse_args()


def load_campaign_expected_actions(workbook_path: Path) -> pd.DataFrame:
    rows = load_campaign_truth_rows(workbook_path)
    return pd.DataFrame(
        [
            {
                "campaign_name": row["campaign_name"].strip().lower(),
                "term": row["term"],
                "expected_action": row["truth_action_type"],
            }
            for row in rows
        ]
    )


def load_aggregate_expected_actions(workbook_path: Path) -> pd.DataFrame:
    rows = load_aggregate_truth_rows(workbook_path)
    return pd.DataFrame(
        [
            {
                "asin_identifier": row["asin_identifier"],
                "term": row["term"],
                "term_type": row["term_type"],
                "expected_action": row["truth_action_type"],
                "conflict_flag": row["conflict_flag"],
            }
            for row in rows
        ]
    )


def compare_campaign_actions(
    expected_df: pd.DataFrame, db: Database, product_id: int
) -> dict:
    results = analyze_search_terms_by_campaign(db, product_id)
    result_lookup = {
        (result.campaign_name.strip().lower(), result.term.strip().lower()): result
        for result in results
    }

    mismatches = []
    missing = []
    aligned = 0

    for row in expected_df.itertuples(index=False):
        result = result_lookup.get((row.campaign_name, row.term))
        if result is None:
            missing.append({"campaign_name": row.campaign_name, "term": row.term})
            continue

        actual_action = result.action_type or "none"
        if row.expected_action == actual_action:
            aligned += 1
            continue

        mismatches.append(
            {
                "level": "campaign",
                "campaign_name": row.campaign_name,
                "term": row.term,
                "expected": row.expected_action,
                "actual": actual_action,
                "rule": result.triggered_rule,
                "clicks": result.clicks,
                "orders": result.orders,
                "spend": result.spend,
            }
        )

    return {
        "expected_count": len(expected_df),
        "result_count": len(results),
        "aligned": aligned,
        "mismatches": mismatches,
        "missing": missing,
    }


def compare_aggregate_actions(
    expected_df: pd.DataFrame, db: Database, product_id: int
) -> dict:
    results = analyze_search_terms_by_asin(db, product_id)
    result_lookup = {
        (result.asin_identifier.strip(), result.term.strip().lower()): result
        for result in results
    }

    mismatches = []
    missing = []
    aligned = 0

    for row in expected_df.itertuples(index=False):
        result = result_lookup.get((row.asin_identifier.strip(), row.term))
        if result is None:
            missing.append(
                {
                    "asin_identifier": row.asin_identifier,
                    "term": row.term,
                    "term_type": row.term_type,
                }
            )
            continue

        actual_action = result.action_type or "none"
        if row.expected_action == actual_action:
            aligned += 1
            continue

        mismatches.append(
            {
                "level": "aggregate",
                "asin_identifier": row.asin_identifier,
                "term": row.term,
                "term_type": row.term_type,
                "expected": row.expected_action,
                "actual": actual_action,
                "rule": result.triggered_rule,
                "clicks": result.data.get("clicks", 0),
                "orders": result.data.get("orders", 0),
                "spend": result.data.get("spend", 0),
                "conflict_flag": row.conflict_flag,
            }
        )

    return {
        "expected_count": len(expected_df),
        "result_count": len(results),
        "aligned": aligned,
        "mismatches": mismatches,
        "missing": missing,
        "ambiguous_source_count": int(expected_df["conflict_flag"].sum())
        if not expected_df.empty
        else 0,
    }


def _print_section(title: str, comparison: dict) -> None:
    print(f"\n=== {title} ===")
    print(f"期望行数: {comparison['expected_count']}")
    print(f"系统结果数: {comparison['result_count']}")

    matched_total = comparison["aligned"] + len(comparison["mismatches"])
    if matched_total == 0:
        print("没有可用于对齐的结果。")
        return

    alignment_rate = comparison["aligned"] / matched_total * 100
    print(f"对齐率: {comparison['aligned']}/{matched_total} = {alignment_rate:.1f}%")
    print(f"剩余不匹配: {len(comparison['mismatches'])}")
    print(f"未命中系统结果: {len(comparison['missing'])}")

    if "ambiguous_source_count" in comparison:
        print(f"源数据冲突标记: {comparison['ambiguous_source_count']}")

    mismatch_types = Counter(
        (item["expected"], item["actual"]) for item in comparison["mismatches"]
    )
    if mismatch_types:
        print("不匹配类型统计:")
        for (expected, actual), count in mismatch_types.most_common():
            print(f"  {expected} -> {actual}: {count} 个")


def main() -> int:
    args = parse_args()
    settings = Settings()
    db_path = (args.db_path or Path(settings.database_path)).expanduser().resolve()
    db = Database(str(db_path))

    try:
        if (
            not db.table_exists("search_terms")
            or db.get_table_count("search_terms") == 0
        ):
            print(
                "数据库当前没有 search_terms 数据；"
                "请先导入真实 CSV（例如运行 scripts/import_test_data.py）。"
            )
            return 0

        campaign_expected = load_campaign_expected_actions(args.campaign_workbook)
        aggregate_expected = load_aggregate_expected_actions(args.aggregate_workbook)

        campaign_comparison = compare_campaign_actions(
            campaign_expected, db, args.product_id
        )
        aggregate_comparison = compare_aggregate_actions(
            aggregate_expected, db, args.product_id
        )

        _print_section("广告组级对齐", campaign_comparison)
        _print_section("汇总级对齐", aggregate_comparison)

        if args.output_csv:
            output_path = args.output_csv.expanduser().resolve()
            combined = (
                campaign_comparison["mismatches"] + aggregate_comparison["mismatches"]
            )
            if combined:
                pd.DataFrame(combined).to_csv(output_path, index=False)
                print(f"\nMismatch 明细已导出: {output_path}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
