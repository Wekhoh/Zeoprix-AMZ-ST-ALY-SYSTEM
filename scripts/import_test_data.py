"""
测试数据导入脚本
导入用户提供的6份CSV文件
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.data.db import Database
from src.data.parser import FileParser
from src.data.aggregator import DataAggregator
from src.rules.engine import RuleEngine


def import_csv_files():
    """导入CSV文件"""
    # CSV文件路径
    csv_dir = Path(r"C:\Users\jackl\OneDrive\桌面\否词TODO")
    csv_files = [
        "BLK-TP01-LOT01-SP自动紧密固定-1.88bid.csv",
        "DBL-TP01-LOT01-SP自动紧密动低-1.94bid.csv",
        "DBL-TP01-LOT01-SP自动紧密固定-1.88bid.csv",
        "DBL-TP01-LOT01-SP自动紧密动提高低-1.29bid.csv",
        "BLK-TP01-LOT01-SP自动紧密固定-1.5bid.csv",
        "BLK-TP01-LOT01-SP自动紧密固定-1.2bid.csv",
    ]

    # 初始化数据库
    settings = Settings()
    db = Database(settings.database_path)
    parser = FileParser()

    # 获取或创建测试产品
    products = db.get_all_products()
    test_product = next((p for p in products if p["name"] == "测试产品"), None)

    if test_product:
        product_id = test_product["id"]
        print(f"使用现有产品: 测试产品 (ID: {product_id})")
    else:
        product_id = db.create_product(name="测试产品", asin="B0TEST12345")
        print(f"创建新产品: 测试产品 (ID: {product_id})")

    total_terms = 0

    # 导入每个CSV文件
    for csv_file in csv_files:
        csv_path = csv_dir / csv_file
        if not csv_path.exists():
            print(f"警告: 文件不存在 - {csv_path}")
            continue

        print(f"\n正在处理: {csv_file}")

        try:
            # 解析文件
            with open(csv_path, "rb") as f:
                df = parser.parse(f, csv_file)

            if df is not None and not df.empty:
                print(f"  解析成功: {len(df)} 条记录")

                # 创建广告活动
                campaign_name = csv_file.replace(".csv", "")
                campaign_id = db.create_campaign(
                    product_id=product_id,
                    name=campaign_name,
                )
                print(f"  创建广告活动: {campaign_name} (ID: {campaign_id})")

                # 保存搜索词
                count = db.save_search_terms(df, campaign_id)
                print(f"  导入搜索词: {count} 条")
                total_terms += count

            else:
                print("  警告: 文件为空或解析失败")

        except Exception as e:
            print(f"  错误: {e}")

    print(f"\n总计导入: {total_terms} 条搜索词记录")

    # 运行分析
    print("\n开始运行规则分析...")
    run_analysis(db, product_id)

    return product_id, total_terms


def run_analysis(db, product_id: int):
    """运行规则分析"""
    # 聚合数据
    aggregator = DataAggregator(db)
    df = aggregator.aggregate_by_term(product_id)

    if df.empty:
        print("没有数据可供分析")
        return

    print(f"聚合数据: {len(df)} 条唯一搜索词")

    # 规则分析
    engine = RuleEngine(db, product_id)
    results = engine.analyze(df)

    print(f"分析结果: {len(results)} 条规则触发")

    # 统计
    negative_count = sum(1 for r in results if r.action_type == "negative")
    manual_count = sum(1 for r in results if r.action_type == "manual")
    observe_count = sum(1 for r in results if r.action_type == "observe")

    print(f"  - 否词建议: {negative_count}")
    print(f"  - 手动投放: {manual_count}")
    print(f"  - 继续观察: {observe_count}")

    # 保存结果
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

    print("分析结果已保存")


if __name__ == "__main__":
    product_id, total_terms = import_csv_files()
    print(f"\n完成! 产品ID: {product_id}, 总记录: {total_terms}")
