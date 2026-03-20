import pandas as pd
import sys

sys.path.insert(0, ".")
from src.data.db import Database
from src.rules.engine import RuleEngine

# Load Excel
excel_path = r"C:/Users/jackl/OneDrive/桌面/否词TODO/广告组级别的否词和搜索词分析.xlsx"
df_excel = pd.read_excel(excel_path)


def extract_action(text):
    text = str(text)
    if "自动直接否定精准" in text or "直接否定精准" in text:
        return "negative_exact"
    if "手动精准" in text and (
        "Neg Exact" in text or ("自动否" in text and "先不" not in text)
    ):
        return "manual_exact_with_neg"
    if "手动精准" in text and ("先不否" in text or "自动先不" in text):
        return "manual_exact_no_neg"
    if "手动精准" in text or "去拉手动精准" in text:
        return "manual_exact_no_neg"
    if "手动商品定位" in text:
        return "manual_product_no_neg"
    if "否定词组" in text:
        return "negative_phrase"
    if "继续观察" in text or text.startswith("观察") or "样本不足" in text:
        return "continue_observe"
    return "other"


df_excel["expected_action"] = df_excel["操作计划"].apply(extract_action)

# 动作优先级（数字越小越严格）
# 汇总模式下，同一个词如果有多种期望，取最严格的
ACTION_PRIORITY = {
    "negative_exact": 1,  # 最严格：否定精准
    "negative_phrase": 2,  # 次严格：否定词组
    "manual_exact_with_neg": 3,  # 手动精准+自动否定
    "manual_exact_no_neg": 4,  # 手动精准+先不否
    "manual_product_no_neg": 5,  # 手动商品定位
    "continue_observe": 6,  # 继续观察
    "other": 7,
}


# 对每个唯一关键词，取最严格的期望动作
def get_strictest_action(actions):
    actions_list = actions.tolist()
    sorted_actions = sorted(actions_list, key=lambda x: ACTION_PRIORITY.get(x, 99))
    return sorted_actions[0]


df_unique = (
    df_excel.groupby(df_excel["关键词"].str.lower().str.strip())
    .agg({"expected_action": get_strictest_action})
    .reset_index()
)
df_unique.columns = ["keyword", "expected_action"]
print(f"Excel去重后唯一关键词: {len(df_unique)}个")

# Setup engine
db = Database("data/db/app.db")
engine = RuleEngine(db, product_id=1)

# Get aggregated data from database
cursor = db.conn.cursor()
cursor.execute("""
    SELECT term, term_type,
           SUM(impressions) as impressions,
           SUM(clicks) as clicks,
           SUM(spend) as spend,
           SUM(orders) as orders,
           SUM(sales) as sales
    FROM search_terms
    GROUP BY term
""")
rows = cursor.fetchall()
columns = ["term", "term_type", "impressions", "clicks", "spend", "orders", "sales"]
df_terms = pd.DataFrame(rows, columns=columns)

# Run analysis
results = engine.analyze(df_terms)

# Build lookup
result_lookup = {r.term.lower().strip(): r for r in results}

# Compare
mismatches = []
aligned = 0
for _, row in df_excel.iterrows():
    kw = str(row["关键词"]).lower().strip()
    exp = row["expected_action"]
    if kw in result_lookup:
        r = result_lookup[kw]
        act = r.action_type if r.action_type else "none"
        if exp != act:
            mismatches.append(
                {
                    "keyword": kw,
                    "expected": exp,
                    "actual": act,
                    "rule": r.triggered_rule,
                    "clicks": r.data.get("clicks", 0),
                    "orders": r.data.get("orders", 0),
                    "spend": r.data.get("spend", 0),
                }
            )
        else:
            aligned += 1
    else:
        print(f"Warning: {kw} not found in results")

total = aligned + len(mismatches)
print(f"对齐率: {aligned}/{total} = {aligned / total * 100:.1f}%")
print(f"剩余不匹配: {len(mismatches)}个")
print()

# Group by mismatch type
from collections import Counter

mismatch_types = Counter([(m["expected"], m["actual"]) for m in mismatches])
print("不匹配类型统计:")
for (exp, act), count in mismatch_types.most_common():
    print(f"  {exp} -> {act}: {count}个")

print()
print("详细列表:")
for i, m in enumerate(mismatches, 1):
    print(f"{i}. {m['keyword']}")
    print(f"   期望={m['expected']} 实际={m['actual']}")
    print(f"   规则={m['rule']}")
    print(f"   clicks={m['clicks']} orders={m['orders']} spend=${m['spend']:.2f}")
    print()

db.close()
