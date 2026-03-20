"""检查ASIN分析结果"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")
from src.config.settings import Settings
from src.data.db import Database

settings = Settings()
db = Database(settings.database_path)

df = db.get_analysis_results(filters={"product_id": 1})
asin_df = df[df["term_type"] == "asin"]

print("ASIN分析结果 (前20条):")
print("=" * 80)
for _, row in asin_df.head(20).iterrows():
    print(f"ASIN: {row['term']}")
    print(f"  操作: {row['action_type']} | 规则: {row['triggered_rule']}")
    spend = row.get("spend", 0) or 0
    orders = row.get("orders", 0) or 0
    sales = row.get("sales", 0) or 0
    print(f"  花费: ${spend:.2f} | 订单: {orders} | 销售: ${sales:.2f}")
    print()

print("=" * 80)
print("ASIN操作类型分布:")
print(asin_df["action_type"].value_counts().to_string())
print()
print("ASIN触发规则分布:")
print(asin_df["triggered_rule"].value_counts().to_string())
