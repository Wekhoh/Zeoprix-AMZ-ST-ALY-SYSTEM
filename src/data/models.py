"""
数据模型定义
定义数据库表结构的SQL Schema
"""

from enum import StrEnum


# ==================== 枚举常量定义 ====================


class NegativeType(StrEnum):
    """否定类型枚举（StrEnum：成员即字符串，向后兼容 == 比较）"""

    EXACT = "negative_exact"  # 否定精准
    PHRASE = "negative_phrase"  # 否定词组
    NONE = "none"  # 不否定


class ManualType(StrEnum):
    """手动投放类型枚举"""

    EXACT = "manual_exact"  # 手动精准匹配
    PHRASE = "manual_phrase"  # 手动词组匹配
    BROAD = "manual_broad"  # 手动广泛匹配
    PRODUCT = "manual_product"  # 手动商品定位


class RelevanceLevel:
    """相关性等级常量"""

    # 原有值（自动检测使用）
    STRONG = "strong"  # 强相关（核心词）- 兼容旧代码
    WEAK = "weak"  # 弱相关（边缘类目）→ 词组否定
    IRRELEVANT = "irrelevant"  # 不相关
    GENERIC = "generic"  # 太泛泛的词
    CAR = "car"  # 汽车相关（特殊处理）

    # v2.0: 人工审核细分值
    STRONG_CORE = "strong_core"  # 强相关核心词（产品核心功能）
    STRONG_LONGTAIL = "strong_longtail"  # 强相关长尾词
    NEED_OBSERVE = "need_observe"  # 待观察（样本不足，继续观察）
    PENDING = "pending"  # 待人工审核

    # 映射：将细分值归类到大类（用于规则匹配）
    @classmethod
    def to_category(cls, value: str) -> str:
        """将细分相关性映射到大类（用于规则条件匹配）"""
        if value in (cls.STRONG, cls.STRONG_CORE, cls.STRONG_LONGTAIL):
            return cls.STRONG
        return value


class ActionType(StrEnum):
    """动作类型枚举（StrEnum：成员即字符串，旧字符串比较仍然成立）"""

    # ==================== 单一否定动作 ====================
    NEGATIVE_EXACT = "negative_exact"  # 否定精准
    NEGATIVE_PHRASE = "negative_phrase"  # 否定词组

    # ==================== 单一手动动作 ====================
    MANUAL_EXACT = "manual_exact"  # 手动精准
    MANUAL_PRODUCT = "manual_product"  # 手动商品定位

    # ==================== 组合动作：手动 + 是否否定 ====================
    # 手动精准测试 + 自动先不否（表现好，值得测试，但先不否定保留自动流量）
    MANUAL_EXACT_NO_NEG = "manual_exact_no_neg"
    # 手动精准 + 自动否定（表现差但强相关，需要控制匹配类型）
    MANUAL_EXACT_WITH_NEG = "manual_exact_with_neg"
    # 手动商品定位 + 自动先不否（ASIN表现好，先定位观察）
    MANUAL_PRODUCT_NO_NEG = "manual_product_no_neg"
    # 手动商品定位 + 自动否定（自家变体互相保护）
    MANUAL_PRODUCT_WITH_NEG = "manual_product_with_neg"

    # ==================== 观察类动作 ====================
    OBSERVE = "observe"  # 观察
    CONTINUE_OBSERVE = "continue_observe"  # 继续观察（样本不足）
    EVALUATE = "evaluate"  # 评估（需要人工判断）

    @classmethod
    def is_negative(cls, value: str | None) -> bool:
        """Return whether an action includes a negative component."""
        return value in {
            "negative",
            cls.NEGATIVE_EXACT,
            cls.NEGATIVE_PHRASE,
            cls.MANUAL_EXACT_WITH_NEG,
            cls.MANUAL_PRODUCT_WITH_NEG,
        }

    @classmethod
    def is_manual(cls, value: str | None) -> bool:
        """Return whether an action includes a manual targeting component."""
        return value in {
            "manual",
            cls.MANUAL_EXACT,
            cls.MANUAL_PRODUCT,
            cls.MANUAL_EXACT_NO_NEG,
            cls.MANUAL_EXACT_WITH_NEG,
            cls.MANUAL_PRODUCT_NO_NEG,
            cls.MANUAL_PRODUCT_WITH_NEG,
        }

    @classmethod
    def is_observe(cls, value: str | None) -> bool:
        """Return whether an action is an observe-style action."""
        return value in {cls.OBSERVE, cls.CONTINUE_OBSERVE}


# ==================== 产品配置结构说明 ====================
# 产品的config字段应包含以下结构:
#
# PRODUCT_CONFIG_SCHEMA = {
#     # 原有配置
#     "core_keywords": [],          # 核心关键词列表
#     "related_keywords": [],       # 相关关键词列表
#     "own_asins": [],              # 自有ASIN列表
#     "competitor_asins": [],       # 竞品ASIN列表
#
#     # 新增配置
#     "own_variants": [],           # 自家变体ASIN列表
#     "is_new_product": False,      # 是否新品期
#     "new_product_days": 30,       # 新品期天数
#
#     # 关键词库配置
#     "keyword_libraries": {
#         "irrelevant_keywords": [],     # 明显不相关词库
#         "weak_category_keywords": [],   # 弱相关类目词（massager, blanket等）→ 词组否定
#         "weak_exact_keywords": [],      # 弱相关精准词（neck support pillow等）→ 精准否定
#         "generic_keywords": [],         # 太泛的词（pillow, pillows, neck）
#         "car_keywords": [],             # 汽车相关词
#     },
#
#     # 阈值配置
#     "thresholds": {
#         "min_clicks_for_analysis": 20,    # 可靠分析的最小点击数
#         "high_spend_no_order": 20.0,      # 高花费无订单阈值
#         "min_clicks_for_asin_neg": 6,     # ASIN否定的最小点击数
#         "good_cvr": 0.10,                  # 好的转化率阈值
#         "bad_cvr": 0.05,                   # 差的转化率阈值
#     }
# }


# ==================== 数据库表结构 ====================

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

# 用户表（多人协作骨架）
USERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# 产品工作区成员关系表（当前以 products 作为工作区）
WORKSPACE_MEMBERSHIPS_SCHEMA = """
CREATE TABLE IF NOT EXISTS workspace_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, user_id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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

# 可复用策略组合表
STRATEGY_PROFILES_SCHEMA = """
CREATE TABLE IF NOT EXISTS strategy_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    lifecycle TEXT,
    goal TEXT,
    config_snapshot JSON NOT NULL,
    notes TEXT,
    source_product_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_product_id) REFERENCES products(id) ON DELETE SET NULL
);
"""

# 执行批次表
EXECUTION_BATCHES_SCHEMA = """
CREATE TABLE IF NOT EXISTS execution_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    batch_code TEXT NOT NULL UNIQUE,
    batch_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'prepared',
    item_count INTEGER DEFAULT 0,
    summary_json TEXT NOT NULL,
    draft_note TEXT,
    execution_note TEXT,
    review_note TEXT,
    executed_at DATETIME,
    reviewed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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

# 人工审核表
# 用于存储用户对系统分析结果的审核决策
# v2.0: 增加相关性人工审核功能（relevance, scope, competition_level等）
MANUAL_REVIEWS_SCHEMA = """
CREATE TABLE IF NOT EXISTS manual_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    term TEXT NOT NULL,
    term_type TEXT DEFAULT 'keyword',  -- keyword | asin
    campaign_id INTEGER,  -- NULL = 全局, 有值 = 仅该活动
    asin_identifier TEXT,  -- NULL = 不区分ASIN汇总, 有值 = BLK/DBL级 truth

    -- ==================== 相关性人工审核字段 ====================
    -- 相关性标记（人工判断）
    relevance TEXT,  -- strong_core | strong_longtail | weak | generic | irrelevant | pending
    relevance_notes TEXT,  -- 相关性判断理由

    -- 范围控制
    scope TEXT DEFAULT 'local',  -- local | global
    -- local: 仅当前活动生效（默认）
    -- global: 同步到该ASIN下所有活动（仅用于"绝对不相关/绝对要屏蔽"的词）

    -- ASIN专用：竞争力评估
    competition_level TEXT,  -- can_compete | cannot_compete | need_observe
    competition_notes TEXT,  -- 竞争力判断理由

    -- AI辅助
    ai_suggestion TEXT,  -- AI建议的相关性
    ai_confidence REAL,  -- AI置信度 (0.0-1.0)

    -- 已审核真相回放/导入字段
    review_source TEXT,  -- upload_pending | campaign_truth | aggregate_truth | ui_review
    truth_action_type TEXT,  -- 规范化动作类型，用于回放
    manual_action TEXT,  -- workbook中的手动动作
    auto_action TEXT,  -- workbook中的自动动作
    negate_keyword TEXT,  -- workbook中的否定关键词
    negate_asin TEXT,  -- workbook中的否定ASIN
    action_matrix TEXT,  -- 广告组动作矩阵
    conflict_flag INTEGER DEFAULT 0,  -- 是否存在活动冲突
    evidence_payload TEXT,  -- JSON结构化证据

    -- ==================== 原有字段 ====================
    system_action TEXT,  -- 系统建议
    final_action TEXT,   -- 用户最终决定
    reviewed INTEGER DEFAULT 0,  -- 是否已审核
    notes TEXT,          -- 通用备注

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL
);
"""

# 每日 pacing 快照表（Sprint B.4）
# 每天每 campaign 一条快照；NULL campaign_id 表示 product 级聚合
# UNIQUE 约束 + INSERT OR REPLACE 保证同 (product, date, campaign) 单条
DAILY_PACING_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_pacing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    campaign_id INTEGER,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    spend REAL DEFAULT 0.0,
    orders INTEGER DEFAULT 0,
    sales REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, snapshot_date, campaign_id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL
);
"""

# 所有表Schema的有序列表（按依赖顺序）
ALL_SCHEMAS = [
    ("products", PRODUCTS_SCHEMA),
    ("users", USERS_SCHEMA),
    ("workspace_memberships", WORKSPACE_MEMBERSHIPS_SCHEMA),
    ("campaigns", CAMPAIGNS_SCHEMA),
    ("search_terms", SEARCH_TERMS_SCHEMA),
    ("rules", RULES_SCHEMA),
    ("rule_versions", RULE_VERSIONS_SCHEMA),
    ("strategy_profiles", STRATEGY_PROFILES_SCHEMA),
    ("execution_batches", EXECUTION_BATCHES_SCHEMA),
    ("analysis_results", ANALYSIS_RESULTS_SCHEMA),
    ("action_plans", ACTION_PLANS_SCHEMA),
    ("manual_reviews", MANUAL_REVIEWS_SCHEMA),
    ("daily_pacing", DAILY_PACING_SCHEMA),
]

# 创建索引以提升查询性能
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
    "CREATE INDEX IF NOT EXISTS idx_workspace_memberships_product_id ON workspace_memberships(product_id);",
    "CREATE INDEX IF NOT EXISTS idx_workspace_memberships_user_id ON workspace_memberships(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_campaigns_product_id ON campaigns(product_id);",
    "CREATE INDEX IF NOT EXISTS idx_search_terms_campaign_id ON search_terms(campaign_id);",
    "CREATE INDEX IF NOT EXISTS idx_search_terms_term ON search_terms(term);",
    "CREATE INDEX IF NOT EXISTS idx_rules_product_id ON rules(product_id);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_results_search_term_id ON analysis_results(search_term_id);",
    "CREATE INDEX IF NOT EXISTS idx_execution_batches_product_id ON execution_batches(product_id);",
    "CREATE INDEX IF NOT EXISTS idx_execution_batches_product_created ON execution_batches(product_id, created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_manual_reviews_product_term ON manual_reviews(product_id, term);",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_manual_reviews_unique ON manual_reviews(product_id, term, COALESCE(campaign_id, 0), COALESCE(asin_identifier, ''));",
    # v2.0: 相关性人工审核索引
    "CREATE INDEX IF NOT EXISTS idx_manual_reviews_relevance ON manual_reviews(product_id, relevance);",
    "CREATE INDEX IF NOT EXISTS idx_manual_reviews_scope ON manual_reviews(product_id, scope);",
    "CREATE INDEX IF NOT EXISTS idx_manual_reviews_reviewed ON manual_reviews(product_id, reviewed);",
    "CREATE INDEX IF NOT EXISTS idx_manual_reviews_truth_action ON manual_reviews(product_id, truth_action_type);",
    "CREATE INDEX IF NOT EXISTS idx_strategy_profiles_name ON strategy_profiles(name);",
    # Sprint B.4: 每日 pacing 快照查询索引
    "CREATE INDEX IF NOT EXISTS idx_daily_pacing_product_date ON daily_pacing(product_id, snapshot_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_daily_pacing_campaign ON daily_pacing(campaign_id);",
]

# 默认规则配置（系统初始化时插入）
# 规则按优先级从小到大执行，第一个匹配的规则生效
DEFAULT_RULES = [
    # ==================== 关键词规则 ====================
    # 1. 明显不相关词 → 否定精准 (基于关键词库判断)
    {
        "name": "明显不相关词",
        "rule_type": "keyword",
        "conditions": {"relevance": "irrelevant"},
        "action": "否定精准",
        "priority": 5,
    },
    # 2. 弱相关类目词 → 否定词组 (massager, blanket等)
    {
        "name": "弱相关类目词",
        "rule_type": "keyword",
        "conditions": {"relevance": "weak"},
        "action": "否定词组",
        "priority": 6,
    },
    # 2.5 弱相关精准词 → 否定精准 (neck support pillow等，虽弱相关但用精准否定)
    {
        "name": "弱相关精准词",
        "rule_type": "keyword",
        "conditions": {"relevance": "weak_exact"},
        "action": "否定精准",
        "priority": 6,
    },
    # 3. 太泛的词 → 否定精准 (pillow, neck等，不用词组避免误伤)
    {
        "name": "太泛的词",
        "rule_type": "keyword",
        "conditions": {"relevance": "generic"},
        "action": "否定精准",
        "priority": 7,
    },
    # 4. 汽车相关词 → 否定精准 (car相关特殊处理)
    {
        "name": "汽车相关词",
        "rule_type": "keyword",
        "conditions": {"relevance": "car"},
        "action": "否定精准",
        "priority": 8,
    },
    # 5. 高花费零转化 → 否定精准
    {
        "name": "高花费零转化",
        "rule_type": "keyword",
        "conditions": {"spend_min": 10.0, "orders_max": 0},
        "action": "否定精准",
        "priority": 10,
    },
    # 6. 强相关+样本充足+表现差 → 手动精准+自动否
    {
        "name": "强相关表现差",
        "rule_type": "keyword",
        "conditions": {
            "relevance": "strong",
            "clicks_min": 20,
            "cvr_max": 0.05,
        },
        "action": "手动精准+自动否定",
        "priority": 15,
    },
    # 7. 低转化高花费 → 评估否定 (需要样本充足)
    {
        "name": "低转化高花费",
        "rule_type": "keyword",
        "conditions": {"acos_min": 0.5, "spend_min": 15.0, "clicks_min": 20},
        "action": "评估否定",
        "priority": 20,
    },
    # 8. 高转化词 → 手动精准
    {
        "name": "高转化词",
        "rule_type": "keyword",
        "conditions": {"acos_max": 0.25, "orders_min": 3},
        "action": "手动精准",
        "priority": 30,
    },
    # 9. 强相关+有单 → 手动精准测试+自动先不否
    #    （强相关词只要有订单，就值得手动精准测试，且先保留自动广告流量）
    #    注意：优先级需高于"高转化词"(P30)，确保强相关词走这条规则
    #    用户逻辑：强相关词的转化是可以接受的，不轻易否定
    {
        "name": "强相关有单",
        "rule_type": "keyword",
        "conditions": {
            "relevance": "strong",
            "cvr_min": 0.05,  # 降低阈值：只要CVR>=5%就算可接受
            "orders_min": 1,
        },
        "action": "手动精准测试+自动先不否",
        "priority": 28,  # 高于"高转化词"(P30)
    },
    # 10. 强相关+已出单+样本不足 → 手动精准测试+自动先不否
    #    （用户逻辑：只要强相关+出单，不管样本量，都值得手动精准测试）
    #    注意：优先级略低于"强相关表现好"(P28)，作为补充规则捕获低CVR但有单的情况
    {
        "name": "强相关已出单样本不足",
        "rule_type": "keyword",
        "conditions": {
            "relevance": "strong",
            "orders_min": 1,
            "clicks_max": 19,
        },
        "action": "手动精准测试+自动先不否",
        "priority": 29,  # 紧随"强相关表现好"(P28)
    },
    # 11. 强相关+未出单+样本不足 → 继续观察
    {
        "name": "强相关未出单样本不足",
        "rule_type": "keyword",
        "conditions": {
            "relevance": "strong",
            "orders_max": 0,
            "clicks_max": 19,
        },
        "action": "继续观察",
        "priority": 40,
    },
    # 12. 低相关性需AI判断 → 短语否定
    {
        "name": "低相关性",
        "rule_type": "keyword",
        "conditions": {"need_ai_judgment": True},
        "action": "短语否定",
        "priority": 50,
    },
    # ==================== ASIN规则 ====================
    # 13. 自家变体ASIN → 手动商品定位 (互相防御)
    {
        "name": "自家变体ASIN",
        "rule_type": "asin",
        "conditions": {"is_own_variant": True},
        "action": "手动商品定位",
        "priority": 5,
    },
    # 14. ASIN未出单+高花费 → 否定精准
    {
        "name": "ASIN未出单高花费",
        "rule_type": "asin",
        "conditions": {
            "orders_max": 0,
            "clicks_min": 6,
            "spend_min": 20.0,
        },
        "action": "否定精准",
        "priority": 10,
    },
    # 15. ASIN出单+低转化 → 否定精准
    {
        "name": "ASIN出单低转化",
        "rule_type": "asin",
        "conditions": {
            "orders_min": 1,
            "clicks_min": 10,
            "cvr_max": 0.10,
        },
        "action": "否定精准",
        "priority": 15,
    },
    # 15.5. ASIN有单但样本不足 → 继续观察
    #    （有订单但点击量过少，样本不足以判断表现，需继续观察积累数据）
    {
        "name": "ASIN有单样本不足",
        "rule_type": "asin",
        "conditions": {
            "orders_min": 1,
            "clicks_max": 9,  # 少于10次点击视为样本不足
        },
        "action": "继续观察",
        "priority": 17,
    },
    # 16. ASIN出单+表现好 → 手动商品定位+自动先不否
    #    （表现好的ASIN值得手动定位测试，但先保留自动广告流量）
    #    要求：orders>=1, CVR>=10%, clicks>=10（确保样本充足）
    {
        "name": "ASIN出单表现好",
        "rule_type": "asin",
        "conditions": {
            "orders_min": 1,
            "cvr_min": 0.10,
            "clicks_min": 10,  # 增加样本量要求
        },
        "action": "手动商品定位+自动先不否",
        "priority": 20,
    },
    # 17. 竞品ASIN → 监控
    {
        "name": "竞品ASIN",
        "rule_type": "asin",
        "conditions": {"is_competitor": True},
        "action": "监控",
        "priority": 50,
    },
]
