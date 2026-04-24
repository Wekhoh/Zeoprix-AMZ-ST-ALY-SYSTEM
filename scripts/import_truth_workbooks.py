"""导入已人工审核的 workbook 真相，并可保存为命名策略组合。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.truth_replay import seed_truth_workbooks  # noqa: E402
from src.config.settings import Settings  # noqa: E402
from src.data.db import Database  # noqa: E402

DEFAULT_CAMPAIGN_WORKBOOK = Path(
    r"C:\Users\jackl\OneDrive\桌面\否词TODO\广告组级别的否词和搜索词分析.xlsx"
)
DEFAULT_AGGREGATE_WORKBOOK = Path(
    r"C:\Users\jackl\OneDrive\桌面\否词TODO\ASIN层面汇总分析_v7.xlsx"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入已审核 workbook 真相数据。")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="SQLite 数据库路径；默认使用项目配置中的 database_path。",
    )
    parser.add_argument(
        "--product-id",
        type=int,
        default=None,
        help="目标产品 ID。",
    )
    parser.add_argument(
        "--product-name",
        default=None,
        help="可选：按产品名称定位产品。",
    )
    parser.add_argument(
        "--campaign-workbook",
        type=Path,
        default=DEFAULT_CAMPAIGN_WORKBOOK,
        help="广告组级真相 workbook 路径。",
    )
    parser.add_argument(
        "--aggregate-workbook",
        type=Path,
        default=DEFAULT_AGGREGATE_WORKBOOK,
        help="汇总级真相 workbook 路径。",
    )
    parser.add_argument(
        "--profile-name",
        default=None,
        help="可选：将当前产品配置保存为命名策略组合。",
    )
    parser.add_argument(
        "--lifecycle",
        default="launch",
        help="保存策略组合时的 lifecycle 元数据。",
    )
    parser.add_argument(
        "--goal",
        default="precision_traffic",
        help="保存策略组合时的 goal 元数据。",
    )
    parser.add_argument(
        "--notes",
        default="truth replay calibrated",
        help="保存策略组合时的备注。",
    )
    return parser.parse_args()


def resolve_product_id(
    db: Database, product_id: int | None, product_name: str | None
) -> int:
    if product_id is not None:
        product = db.get_product(product_id)
        if not product:
            raise ValueError(f"未找到产品 ID: {product_id}")
        return product_id

    if product_name:
        products = db.get_all_products()
        product = next(
            (item for item in products if item["name"] == product_name), None
        )
        if not product:
            raise ValueError(f"未找到产品名称: {product_name}")
        return int(product["id"])

    raise ValueError("请提供 --product-id 或 --product-name。")


def main() -> int:
    args = parse_args()
    settings = Settings()
    db_path = (args.db_path or Path(settings.database_path)).expanduser().resolve()
    db = Database(str(db_path))
    db.init_schema()

    try:
        product_id = resolve_product_id(db, args.product_id, args.product_name)
        summary = seed_truth_workbooks(
            db=db,
            product_id=product_id,
            campaign_workbook_path=args.campaign_workbook,
            aggregate_workbook_path=args.aggregate_workbook,
        )

        print(f"已导入广告组 truth: {summary['campaign_rows']} 条")
        print(f"广告组未命中 campaign: {summary['campaign_missing']} 条")
        print(f"已导入汇总 truth: {summary['aggregate_rows']} 条")

        if args.profile_name:
            product = db.get_product(product_id)
            db.save_strategy_profile(
                name=args.profile_name,
                config_snapshot=product.get("config", {}),
                lifecycle=args.lifecycle,
                goal=args.goal,
                notes=args.notes,
                source_product_id=product_id,
            )
            print(f"已保存策略组合: {args.profile_name}")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
