"""
数据模型定义
定义数据库表结构的SQL Schema
"""

# 产品档案表
PRODUCTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    asin TEXT,
    category TEXT,
    config JSON DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# 广告活动表
CAMPAIGNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    match_type TEXT,
    bid_strategy TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
"""

# 搜索词明细表
SEARCH_TERMS_SCHEMA = """
CREATE TABLE IF NOT EXISTS search_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    term TEXT NOT NULL,
    term_type TEXT DEFAULT 'keyword',
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0.0,
    spend REAL DEFAULT 0.0,
    cpc REAL DEFAULT 0.0,
    orders INTEGER DEFAULT 0,
    sales REAL DEFAULT 0.0,
    acos REAL DEFAULT 0.0,
    roas REAL DEFAULT 0.0,
    conversion_rate REAL DEFAULT 0.0,
    report_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);
"""

# 规则配置表
RULES_SCHEMA = """
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    name TEXT NOT NULL,
    rule_type TEXT DEFAULT 'keyword',
    conditions JSON NOT NULL,
    action TEXT NOT NULL,
    priority INTEGER DEFAULT 100,
    enabled INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);
"""

# 规则版本历史表
RULE_VERSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS rule_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    version INTEGER NOT NULL,
    rules_snapshot JSON NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
"""

# 分析结果表
ANALYSIS_RESULTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term_id INTEGER NOT NULL,
    triggered_rule TEXT,
    suggested_action TEXT,
    action_type TEXT,
    confidence REAL DEFAULT 1.0,
    ai_reasoning TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (search_term_id) REFERENCES search_terms(id) ON DELETE CASCADE
);
"""

# 操作计划表
ACTION_PLANS_SCHEMA = """
CREATE TABLE IF NOT EXISTS action_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_result_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    notes TEXT,
    executed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_result_id) REFERENCES analysis_results(id) ON DELETE CASCADE
);
"""

# 所有表Schema的有序列表（按依赖顺序）
ALL_SCHEMAS = [
    ("products", PRODUCTS_SCHEMA),
    ("campaigns", CAMPAIGNS_SCHEMA),
    ("search_terms", SEARCH_TERMS_SCHEMA),
    ("rules", RULES_SCHEMA),
    ("rule_versions", RULE_VERSIONS_SCHEMA),
    ("analysis_results", ANALYSIS_RESULTS_SCHEMA),
    ("action_plans", ACTION_PLANS_SCHEMA),
]

# 创建索引以提升查询性能
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_campaigns_product_id ON campaigns(product_id);",
    "CREATE INDEX IF NOT EXISTS idx_search_terms_campaign_id ON search_terms(campaign_id);",
    "CREATE INDEX IF NOT EXISTS idx_search_terms_term ON search_terms(term);",
    "CREATE INDEX IF NOT EXISTS idx_rules_product_id ON rules(product_id);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_results_search_term_id ON analysis_results(search_term_id);",
]

# 默认规则配置（系统初始化时插入）
DEFAULT_RULES = [
    {
        "name": "高花费零转化",
        "rule_type": "keyword",
        "conditions": {"spend_min": 10.0, "orders_max": 0},
        "action": "精确否定",
        "priority": 10,
    },
    {
        "name": "低转化高花费",
        "rule_type": "keyword",
        "conditions": {"acos_min": 0.5, "spend_min": 15.0},
        "action": "评估否定",
        "priority": 20,
    },
    {
        "name": "高转化词",
        "rule_type": "keyword",
        "conditions": {"acos_max": 0.25, "orders_min": 3},
        "action": "手动投放",
        "priority": 30,
    },
    {
        "name": "低相关性",
        "rule_type": "keyword",
        "conditions": {"need_ai_judgment": True},
        "action": "短语否定",
        "priority": 40,
    },
    {
        "name": "竞品ASIN",
        "rule_type": "asin",
        "conditions": {"is_competitor": True},
        "action": "监控",
        "priority": 50,
    },
]
