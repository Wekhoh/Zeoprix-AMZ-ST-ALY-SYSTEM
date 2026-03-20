"""测试/验收数据导入脚本。"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings  # noqa: E402
from src.data.aggregator import DataAggregator  # noqa: E402
from src.data.db import Database  # noqa: E402
from src.data.models import ActionType  # noqa: E402
from src.data.parser import FileParser  # noqa: E402
from src.rules.engine import RuleEngine  # noqa: E402

DEFAULT_INPUT_DIR = Path(r"C:\Users\jackl\OneDrive\桌面\否词TODO")
DEFAULT_CONFIG_TEMPLATE_PATH = (
    project_root / "data" / "fixtures" / "acceptance_product_config.json"
)
DEFAULT_CSV_FILENAMES = [
    "BLK-TP01-LOT01-SP自动紧密固定-1.88bid.csv",
    "DBL-TP01-LOT01-SP自动紧密动低-1.94bid.csv",
    "DBL-TP01-LOT01-SP自动紧密固定-1.88bid.csv",
    "DBL-TP01-LOT01-SP自动紧密动提高低-1.29bid.csv",
    "BLK-TP01-LOT01-SP自动紧密固定-1.5bid.csv",
    "BLK-TP01-LOT01-SP自动紧密固定-1.2bid.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="导入 Amazon 搜索词 CSV，并可选自动运行规则分析。"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="显式指定一个或多个 CSV 文件路径；提供后会忽略 --input-dir。",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="CSV 所在目录；默认指向当前验收数据目录。",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="目标 SQLite 路径；默认使用项目配置中的 database_path。",
    )
    parser.add_argument(
        "--product-name",
        default="测试产品",
        help="导入到的产品名称；若不存在会自动创建。",
    )
    parser.add_argument(
        "--product-asin",
        default="B0TEST12345",
        help="创建新产品时使用的 ASIN。",
    )
    parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="仅导入原始数据，不自动运行规则分析。",
    )
    parser.add_argument(
        "--config-template",
        type=Path,
        default=DEFAULT_CONFIG_TEMPLATE_PATH,
        help="产品配置模板 JSON 路径；默认使用仓库内的验收配置模板。",
    )
    parser.add_argument(
        "--skip-config-seed",
        action="store_true",
        help="跳过产品配置模板注入（默认会自动补齐产品配置）。",
    )
    return parser.parse_args()


def resolve_csv_files(explicit_files: list[str], input_dir: Path) -> list[Path]:
    if explicit_files:
        return [Path(file).expanduser().resolve() for file in explicit_files]

    input_dir = input_dir.expanduser().resolve()
    preferred = [input_dir / name for name in DEFAULT_CSV_FILENAMES]
    existing_preferred = [path for path in preferred if path.exists()]
    if existing_preferred:
        return existing_preferred

    return sorted(path.resolve() for path in input_dir.glob("*.csv"))


def infer_match_type(csv_path: Path) -> str | None:
    stem = csv_path.stem
    if "自动" in stem:
        return "auto"
    if "精准" in stem:
        return "exact"
    if "词组" in stem:
        return "phrase"
    return None


def get_or_create_product(db: Database, product_name: str, product_asin: str) -> int:
    products = db.get_all_products()
    existing = next((p for p in products if p["name"] == product_name), None)
    if existing:
        print(f"使用现有产品: {product_name} (ID: {existing['id']})")
        return existing["id"]

    product_id = db.create_product(name=product_name, asin=product_asin)
    print(f"创建新产品: {product_name} (ID: {product_id})")
    return product_id


def load_config_template(template_path: str | Path) -> dict:
    """加载验收环境的产品配置模板。"""
    path = Path(template_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"配置模板不存在: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"配置模板必须是 JSON object: {path}")

    return data


def _merge_config_value(existing, template):
    """深度合并配置：保留现有标量，列表 union，字典递归补缺。"""
    if isinstance(existing, dict) and isinstance(template, dict):
        merged = copy.deepcopy(existing)
        for key, value in template.items():
            if key in merged:
                merged[key] = _merge_config_value(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged

    if isinstance(existing, list) and isinstance(template, list):
        merged: list = []
        for item in existing + template:
            if item not in merged:
                merged.append(item)
        return merged

    if existing in (None, ""):
        return copy.deepcopy(template)

    return copy.deepcopy(existing)


def ensure_product_config(
    db: Database,
    product_id: int,
    product_asin: str | None,
    template_config: dict,
) -> bool:
    """确保产品具备验收所需配置。"""
    product = db.get_product(product_id)
    if not product:
        raise ValueError(f"产品不存在: {product_id}")

    existing_config = product.get("config", {}) or {}
    merged_config = _merge_config_value(existing_config, template_config)

    own_asins = merged_config.get("own_asins", [])
    if not isinstance(own_asins, list):
        own_asins = []

    for asin in [product.get("asin"), product_asin]:
        normalized = (asin or "").strip().upper()
        if normalized and normalized not in own_asins:
            own_asins.append(normalized)
    merged_config["own_asins"] = own_asins

    changed = merged_config != existing_config
    if changed:
        db.update_product_config(product_id, merged_config)
    return changed


def import_csv_files(
    db: Database,
    parser: FileParser,
    product_id: int,
    csv_paths: list[Path],
) -> tuple[int, list[Path]]:
    total_terms = 0
    imported_files: list[Path] = []

    for csv_path in csv_paths:
        if not csv_path.exists():
            print(f"警告: 文件不存在 - {csv_path}")
            continue

        print(f"\n正在处理: {csv_path.name}")
        try:
            with csv_path.open("rb") as file_obj:
                df = parser.parse(file_obj, csv_path.name)

            if df is None or df.empty:
                print("  警告: 文件为空或解析失败")
                continue

            print(f"  解析成功: {len(df)} 条记录")
            campaign_name = csv_path.stem
            campaign_id = db.get_or_create_campaign(
                product_id=product_id,
                name=campaign_name,
                match_type=infer_match_type(csv_path),
            )
            print(f"  使用广告活动: {campaign_name} (ID: {campaign_id})")

            count = db.save_search_terms(df, campaign_id)
            print(f"  导入搜索词: {count} 条")
            total_terms += count
            imported_files.append(csv_path)
        except Exception as exc:  # pragma: no cover - CLI 可见错误
            print(f"  错误: {exc}")

    return total_terms, imported_files


def run_analysis(db: Database, product_id: int) -> dict[str, int]:
    aggregator = DataAggregator(db)
    df = aggregator.aggregate_by_term(product_id)
    if df.empty:
        print("没有数据可供分析")
        return {"total": 0, "negative": 0, "manual": 0, "observe": 0}

    print(f"\n聚合数据: {len(df)} 条唯一搜索词")
    engine = RuleEngine(db, product_id)
    results = engine.analyze(df)
    print(f"分析结果: {len(results)} 条规则触发")

    counts = {
        "total": len(results),
        "negative": sum(
            1 for item in results if ActionType.is_negative(item.action_type)
        ),
        "manual": sum(1 for item in results if ActionType.is_manual(item.action_type)),
        "observe": sum(
            1 for item in results if ActionType.is_observe(item.action_type)
        ),
    }
    print(f"  - 否词建议: {counts['negative']}")
    print(f"  - 手动投放: {counts['manual']}")
    print(f"  - 继续观察: {counts['observe']}")

    for result in results:
        db.save_analysis_result_by_term(
            product_id=product_id,
            term=result.term,
            triggered_rule=result.triggered_rule,
            suggested_action=result.suggested_action,
            action_type=result.action_type,
            confidence=result.confidence,
            ai_reasoning=result.ai_reasoning,
        )

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

    print("分析结果已保存")
    return counts


def main() -> int:
    args = parse_args()
    settings = Settings()
    db_path = (args.db_path or Path(settings.database_path)).expanduser().resolve()
    config_template_path = args.config_template.expanduser().resolve()
    csv_paths = resolve_csv_files(args.files, args.input_dir)
    if not csv_paths:
        print("未找到可导入的 CSV 文件。请传入文件列表或检查 --input-dir。")
        return 1

    db = Database(str(db_path))
    db.init_schema()
    db.init_default_rules()
    parser = FileParser()

    try:
        product_id = get_or_create_product(db, args.product_name, args.product_asin)
        if args.skip_config_seed:
            print("跳过产品配置模板注入")
        else:
            template_config = load_config_template(config_template_path)
            config_seeded = ensure_product_config(
                db=db,
                product_id=product_id,
                product_asin=args.product_asin,
                template_config=template_config,
            )
            if config_seeded:
                print(f"产品配置已补齐: {config_template_path}")
            else:
                print("产品配置已存在，无需补齐")

        total_terms, imported_files = import_csv_files(db, parser, product_id, csv_paths)
        print(f"\n总计导入: {total_terms} 条搜索词记录")
        print(f"成功处理文件: {len(imported_files)} 个")

        if not args.skip_analysis:
            counts = run_analysis(db, product_id)
            print(
                "完成! "
                f"产品ID: {product_id}, "
                f"总记录: {total_terms}, "
                f"汇总结果: {counts['total']}"
            )
        else:
            print(f"完成! 产品ID: {product_id}, 总记录: {total_terms}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
