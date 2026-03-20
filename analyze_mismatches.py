"""对比 Excel 预期动作与数据库规则结果的对齐情况。"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings  # noqa: E402
from src.data.aggregator import DataAggregator  # noqa: E402
from src.data.db import Database  # noqa: E402
from src.rules.engine import RuleEngine  # noqa: E402

DEFAULT_WORKBOOK = Path(
    r"C:\Users\jackl\OneDrive\桌面\否词TODO\广告组级别的否词和搜索词分析.xlsx"
)

ACTION_PRIORITY = {
    "negative_exact": 1,
    "negative_phrase": 2,
    "manual_exact_with_neg": 3,
    "manual_exact_no_neg": 4,
    "manual_product_no_neg": 5,
    "continue_observe": 6,
    "other": 7,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="分析 Excel 预期动作与规则引擎结果的差异。")
    parser.add_argument(
        "--workbook",
        type=Path,
        default=DEFAULT_WORKBOOK,
        help="人工校验 Excel 路径。",
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
        help="用于聚合分析的产品 ID。",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="可选：将 mismatch 明细导出为 CSV。",
    )
    return parser.parse_args()


def extract_action(text: object) -> str:
    value = str(text or "")
    if "自动直接否定精准" in value or "直接否定精准" in value:
        return "negative_exact"
    if "手动精准" in value and (
        "Neg Exact" in value or ("自动否" in value and "先不" not in value)
    ):
        return "manual_exact_with_neg"
    if "手动精准" in value and ("先不否" in value or "自动先不" in value):
        return "manual_exact_no_neg"
    if "手动精准" in value or "去拉手动精准" in value:
        return "manual_exact_no_neg"
    if "手动商品定位" in value:
        return "manual_product_no_neg"
    if "否定词组" in value:
        return "negative_phrase"
    if "继续观察" in value or value.startswith("观察") or "样本不足" in value:
        return "continue_observe"
    return "other"


def get_strictest_action(actions: pd.Series) -> str:
    return min(actions.tolist(), key=lambda item: ACTION_PRIORITY.get(item, 99))


def load_expected_actions(workbook_path: Path) -> pd.DataFrame:
    if not workbook_path.exists():
        raise FileNotFoundError(f"Excel 文件不存在: {workbook_path}")

    df_excel = pd.read_excel(workbook_path)
    required_columns = {"关键词", "操作计划"}
    missing = required_columns - set(df_excel.columns)
    if missing:
        raise ValueError(f"Excel 缺少必需列: {sorted(missing)}")

    df_excel = df_excel[df_excel["关键词"].notna()].copy()
    df_excel["keyword"] = df_excel["关键词"].astype(str).str.strip().str.lower()
    df_excel = df_excel[df_excel["keyword"] != ""]
    df_excel["expected_action"] = df_excel["操作计划"].apply(extract_action)

    df_unique = (
        df_excel.groupby("keyword", as_index=False)
        .agg({"expected_action": get_strictest_action})
        .reset_index(drop=True)
    )
    return df_unique


def compare_actions(expected_df: pd.DataFrame, db: Database, product_id: int) -> dict:
    aggregator = DataAggregator(db)
    aggregated_df = aggregator.aggregate_by_term(product_id)
    if aggregated_df.empty:
        return {
            "aggregated_count": 0,
            "result_count": 0,
            "aligned": 0,
            "mismatches": [],
            "missing_terms": [],
        }

    engine = RuleEngine(db, product_id=product_id)
    results = engine.analyze(aggregated_df)
    result_lookup = {result.term.lower().strip(): result for result in results}

    mismatches = []
    missing_terms = []
    aligned = 0
    for row in expected_df.itertuples(index=False):
        keyword = row.keyword
        expected_action = row.expected_action
        result = result_lookup.get(keyword)
        if result is None:
            missing_terms.append(keyword)
            continue

        actual_action = result.action_type or "none"
        if expected_action == actual_action:
            aligned += 1
            continue

        mismatches.append(
            {
                "keyword": keyword,
                "expected": expected_action,
                "actual": actual_action,
                "rule": result.triggered_rule,
                "clicks": result.data.get("clicks", 0),
                "orders": result.data.get("orders", 0),
                "spend": result.data.get("spend", 0),
            }
        )

    return {
        "aggregated_count": len(aggregated_df),
        "result_count": len(results),
        "aligned": aligned,
        "mismatches": mismatches,
        "missing_terms": missing_terms,
    }


def print_report(expected_df: pd.DataFrame, comparison: dict) -> None:
    print(f"Excel 去重后唯一关键词: {len(expected_df)} 个")
    print(f"数据库聚合后唯一关键词: {comparison['aggregated_count']} 个")
    print(f"规则引擎输出结果: {comparison['result_count']} 个")

    matched_total = comparison["aligned"] + len(comparison["mismatches"])
    if matched_total == 0:
        print("\n数据库中没有可用于对齐的分析结果；请先导入真实 CSV 并运行分析。")
        return

    alignment_rate = comparison["aligned"] / matched_total * 100
    print(f"\n对齐率: {comparison['aligned']}/{matched_total} = {alignment_rate:.1f}%")
    print(f"剩余不匹配: {len(comparison['mismatches'])} 个")
    print(f"Excel 中未命中数据库结果: {len(comparison['missing_terms'])} 个")

    mismatch_types = Counter(
        (item["expected"], item["actual"]) for item in comparison["mismatches"]
    )
    if mismatch_types:
        print("\n不匹配类型统计:")
        for (expected, actual), count in mismatch_types.most_common():
            print(f"  {expected} -> {actual}: {count} 个")

    if comparison["missing_terms"]:
        preview = ", ".join(comparison["missing_terms"][:10])
        suffix = " ..." if len(comparison["missing_terms"]) > 10 else ""
        print(f"\n未命中关键词示例: {preview}{suffix}")

    if comparison["mismatches"]:
        print("\n详细列表:")
        for idx, mismatch in enumerate(comparison["mismatches"], start=1):
            print(f"{idx}. {mismatch['keyword']}")
            print(f"   期望={mismatch['expected']} 实际={mismatch['actual']}")
            print(f"   规则={mismatch['rule']}")
            print(
                "   "
                f"clicks={mismatch['clicks']} "
                f"orders={mismatch['orders']} "
                f"spend=${mismatch['spend']:.2f}"
            )


def main() -> int:
    args = parse_args()
    settings = Settings()
    db_path = (args.db_path or Path(settings.database_path)).expanduser().resolve()
    workbook_path = args.workbook.expanduser().resolve()

    expected_df = load_expected_actions(workbook_path)
    db = Database(str(db_path))
    try:
        if not db.table_exists("search_terms") or db.get_table_count("search_terms") == 0:
            print(
                "数据库当前没有 search_terms 数据；"
                "请先导入真实 CSV（例如运行 scripts/import_test_data.py）。"
            )
            return 0

        comparison = compare_actions(expected_df, db, args.product_id)
        print_report(expected_df, comparison)

        if args.output_csv and comparison["mismatches"]:
            output_path = args.output_csv.expanduser().resolve()
            pd.DataFrame(comparison["mismatches"]).to_csv(output_path, index=False)
            print(f"\nMismatch 明细已导出: {output_path}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
