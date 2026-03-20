"""
数据库操作模块
提供SQLite数据库的初始化和CRUD操作
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

from src.config.logger import get_logger
from src.data.models import ALL_SCHEMAS, DEFAULT_RULES, INDEXES
from src.rules.asin_rules import is_valid_asin

logger = get_logger(__name__)


class Database:
    """数据库操作类"""

    def __init__(self, db_path: str):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_dir()
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
        # 启用外键约束
        self.conn.execute("PRAGMA foreign_keys = ON")
        # 返回字典形式的行
        self.conn.row_factory = sqlite3.Row

    def _ensure_dir(self) -> None:
        """确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def init_schema(self) -> None:
        """初始化数据库表结构"""
        cursor = self.conn.cursor()
        try:
            # 创建所有表
            for _table_name, schema in ALL_SCHEMAS:
                cursor.execute(schema)

            # 执行数据库迁移（确保旧数据库兼容新schema）
            # 注意：迁移必须在索引创建之前，因为新索引可能依赖迁移添加的列
            self._migrate_schema(cursor)

            # 创建索引（在迁移之后，确保所有列都存在）
            for index_sql in INDEXES:
                cursor.execute(index_sql)

            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"初始化数据库失败: {e}") from e

    def _migrate_schema(self, cursor: sqlite3.Cursor) -> None:
        """数据库迁移：确保旧数据库兼容新schema"""
        # 迁移1: 检查products表是否有updated_at列
        cursor.execute("PRAGMA table_info(products)")
        products_columns = {row[1] for row in cursor.fetchall()}
        if "updated_at" not in products_columns:
            cursor.execute(
                "ALTER TABLE products ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            )

        # 迁移2: 检查campaigns表是否有product_id列
        cursor.execute("PRAGMA table_info(campaigns)")
        columns = {row[1] for row in cursor.fetchall()}

        if "product_id" not in columns:
            # 旧版本的campaigns表没有product_id列，需要重建表
            # SQLite不支持直接添加带外键的列，需要重建
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS campaigns_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL DEFAULT 1,
                    name TEXT NOT NULL,
                    match_type TEXT,
                    bid_strategy TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)
            # 复制数据（假设有一个默认产品ID=1）
            cursor.execute("""
                INSERT INTO campaigns_new (id, product_id, name, match_type, bid_strategy, created_at)
                SELECT id, 1, name, match_type, bid_strategy, created_at FROM campaigns
            """)
            cursor.execute("DROP TABLE campaigns")
            cursor.execute("ALTER TABLE campaigns_new RENAME TO campaigns")
            # 重建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_campaigns_product_id ON campaigns(product_id)"
            )

        # 迁移3: manual_reviews表添加相关性人工审核字段 (v2.0)
        cursor.execute("PRAGMA table_info(manual_reviews)")
        mr_columns = {row[1] for row in cursor.fetchall()}

        # 相关性字段
        if "relevance" not in mr_columns:
            cursor.execute("ALTER TABLE manual_reviews ADD COLUMN relevance TEXT")
        if "relevance_notes" not in mr_columns:
            cursor.execute("ALTER TABLE manual_reviews ADD COLUMN relevance_notes TEXT")

        # 范围控制字段
        if "scope" not in mr_columns:
            cursor.execute(
                "ALTER TABLE manual_reviews ADD COLUMN scope TEXT DEFAULT 'local'"
            )

        # ASIN竞争力评估字段
        if "competition_level" not in mr_columns:
            cursor.execute(
                "ALTER TABLE manual_reviews ADD COLUMN competition_level TEXT"
            )
        if "competition_notes" not in mr_columns:
            cursor.execute(
                "ALTER TABLE manual_reviews ADD COLUMN competition_notes TEXT"
            )

        # AI辅助字段
        if "ai_suggestion" not in mr_columns:
            cursor.execute("ALTER TABLE manual_reviews ADD COLUMN ai_suggestion TEXT")
        if "ai_confidence" not in mr_columns:
            cursor.execute("ALTER TABLE manual_reviews ADD COLUMN ai_confidence REAL")

        # 创建新索引
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_manual_reviews_relevance ON manual_reviews(product_id, relevance)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_manual_reviews_scope ON manual_reviews(product_id, scope)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_manual_reviews_reviewed ON manual_reviews(product_id, reviewed)"
        )

        # 将已审核但无相关性标记的记录设为pending
        cursor.execute("""
            UPDATE manual_reviews
            SET relevance = 'pending'
            WHERE reviewed = 1 AND relevance IS NULL
        """)

    def init_default_rules(self) -> None:
        """插入默认规则配置"""
        cursor = self.conn.cursor()
        try:
            # 检查是否已有规则
            cursor.execute("SELECT COUNT(*) FROM rules WHERE product_id IS NULL")
            count = cursor.fetchone()[0]
            if count > 0:
                return  # 已有默认规则，跳过

            for rule in DEFAULT_RULES:
                cursor.execute(
                    """
                    INSERT INTO rules (product_id, name, rule_type, conditions, action, priority)
                    VALUES (NULL, ?, ?, ?, ?, ?)
                    """,
                    (
                        rule["name"],
                        rule["rule_type"],
                        json.dumps(rule["conditions"]),
                        rule["action"],
                        rule["priority"],
                    ),
                )
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"插入默认规则失败: {e}") from e

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行SQL语句"""
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """批量执行SQL语句"""
        return self.conn.executemany(sql, params_list)

    def commit(self) -> None:
        """提交事务"""
        self.conn.commit()

    def rollback(self) -> None:
        """回滚事务"""
        self.conn.rollback()

    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    # ==================== 产品操作 ====================

    def create_product(
        self, name: str, asin: str = None, category: str = None, config: dict = None
    ) -> int:
        """
        创建产品档案

        Args:
            name: 产品名称
            asin: 产品ASIN
            category: 产品类目
            config: 产品配置（核心关键词等）

        Returns:
            产品ID
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO products (name, asin, category, config)
            VALUES (?, ?, ?, ?)
            """,
            (name, asin, category, json.dumps(config or {})),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_product(self, product_id: int) -> dict | None:
        """获取产品信息"""
        cursor = self.conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result["config"] = json.loads(result["config"]) if result["config"] else {}
            return result
        return None

    def get_all_products(self) -> list[dict]:
        """获取所有产品"""
        cursor = self.conn.execute("SELECT * FROM products ORDER BY created_at DESC")
        products = []
        for row in cursor.fetchall():
            product = dict(row)
            product["config"] = (
                json.loads(product["config"]) if product["config"] else {}
            )
            products.append(product)
        return products

    def update_product(self, product_id: int, **kwargs) -> None:
        """更新产品信息"""
        if not kwargs:
            return  # 没有要更新的字段

        # 白名单验证防止SQL注入
        VALID_COLUMNS = {"name", "asin", "category", "config"}
        invalid_cols = set(kwargs.keys()) - VALID_COLUMNS
        if invalid_cols:
            raise ValueError(f"Invalid column names: {invalid_cols}")

        if "config" in kwargs and isinstance(kwargs["config"], dict):
            kwargs["config"] = json.dumps(kwargs["config"])

        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [product_id]

        try:
            # 先尝试带 updated_at 的更新
            self.conn.execute(
                f"UPDATE products SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                tuple(values),
            )
            self.conn.commit()
        except sqlite3.OperationalError as e:
            # 如果 updated_at 列不存在，回退到不带该列的更新
            if "updated_at" in str(e):
                self.conn.rollback()
                self.conn.execute(
                    f"UPDATE products SET {set_clause} WHERE id = ?",
                    tuple(values),
                )
                self.conn.commit()
            else:
                self.conn.rollback()
                raise RuntimeError(f"更新产品失败: {e}") from e
        except sqlite3.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"更新产品失败: {e}") from e

    def update_product_config(self, product_id: int, config: dict) -> None:
        """
        更新产品配置（便捷方法）

        Args:
            product_id: 产品ID
            config: 新的配置字典
        """
        self.update_product(product_id, config=config)

    # ==================== 广告活动操作 ====================

    def create_campaign(
        self,
        product_id: int,
        name: str,
        match_type: str = None,
        bid_strategy: str = None,
    ) -> int:
        """创建广告活动"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO campaigns (product_id, name, match_type, bid_strategy)
            VALUES (?, ?, ?, ?)
            """,
            (product_id, name, match_type, bid_strategy),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_campaign_by_name(self, product_id: int, name: str) -> dict | None:
        """根据名称获取广告活动"""
        cursor = self.conn.execute(
            "SELECT * FROM campaigns WHERE product_id = ? AND name = ?",
            (product_id, name),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_or_create_campaign(
        self, product_id: int, name: str, match_type: str = None
    ) -> int:
        """获取或创建广告活动，返回ID"""
        campaign = self.get_campaign_by_name(product_id, name)
        if campaign:
            return campaign["id"]
        return self.create_campaign(product_id, name, match_type)

    # ==================== 搜索词操作 ====================

    def save_search_terms(self, df: pd.DataFrame, campaign_id: int) -> int:
        """
        批量保存搜索词数据

        Args:
            df: 包含搜索词数据的DataFrame
            campaign_id: 广告活动ID

        Returns:
            插入的行数
        """
        if df.empty:
            return 0

        # 准备插入数据
        columns = [
            "campaign_id",
            "term",
            "term_type",
            "impressions",
            "clicks",
            "ctr",
            "spend",
            "cpc",
            "orders",
            "sales",
            "acos",
            "roas",
            "conversion_rate",
            "report_date",
        ]

        rows = []
        for _, row in df.iterrows():
            # 使用统一的ASIN验证函数
            term = str(row.get("term", ""))
            term_type = "asin" if is_valid_asin(term) else "keyword"

            rows.append(
                (
                    campaign_id,
                    term,
                    term_type,
                    int(row.get("impressions", 0)),
                    int(row.get("clicks", 0)),
                    float(row.get("ctr", 0)),
                    float(row.get("spend", 0)),
                    float(row.get("cpc", 0)),
                    int(row.get("orders", 0)),
                    float(row.get("sales", 0)),
                    float(row.get("acos", 0)),
                    float(row.get("roas", 0)),
                    float(row.get("conversion_rate", 0)),
                    row.get("report_date"),
                )
            )

        placeholders = ", ".join(["?"] * len(columns))
        columns_str = ", ".join(columns)

        cursor = self.conn.cursor()
        cursor.executemany(
            f"INSERT INTO search_terms ({columns_str}) VALUES ({placeholders})",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def get_search_terms(self, filters: dict = None) -> pd.DataFrame:
        """
        按条件查询搜索词

        Args:
            filters: 筛选条件字典，支持:
                - campaign_id: 广告活动ID
                - product_id: 产品ID（通过campaigns关联）
                - term_type: keyword/asin
                - min_spend: 最小花费
                - min_orders: 最小订单数

        Returns:
            搜索词DataFrame
        """
        sql = """
            SELECT st.*, c.name as campaign_name, c.match_type, p.name as product_name, p.asin as product_asin
            FROM search_terms st
            JOIN campaigns c ON st.campaign_id = c.id
            JOIN products p ON c.product_id = p.id
            WHERE 1=1
        """
        params = []

        if filters:
            if "campaign_id" in filters:
                sql += " AND st.campaign_id = ?"
                params.append(filters["campaign_id"])
            if "product_id" in filters:
                sql += " AND c.product_id = ?"
                params.append(filters["product_id"])
            if "term_type" in filters:
                sql += " AND st.term_type = ?"
                params.append(filters["term_type"])
            if "min_spend" in filters:
                sql += " AND st.spend >= ?"
                params.append(filters["min_spend"])
            if "min_orders" in filters:
                sql += " AND st.orders >= ?"
                params.append(filters["min_orders"])

        sql += " ORDER BY st.spend DESC"

        return pd.read_sql_query(sql, self.conn, params=params)

    # ==================== 规则操作 ====================

    def get_rules(
        self, product_id: int = None, include_disabled: bool = False
    ) -> list[dict]:
        """
        获取规则配置

        Args:
            product_id: 产品ID，为None时获取全局规则
            include_disabled: 是否包含禁用的规则

        Returns:
            规则列表
        """
        if include_disabled:
            sql = """
                SELECT * FROM rules
                WHERE (product_id = ? OR product_id IS NULL)
                ORDER BY priority ASC
            """
        else:
            sql = """
                SELECT * FROM rules
                WHERE (product_id = ? OR product_id IS NULL)
                AND enabled = 1
                ORDER BY priority ASC
            """
        cursor = self.conn.execute(sql, (product_id,))
        rules = []
        for row in cursor.fetchall():
            rule = dict(row)
            rule["conditions"] = (
                json.loads(rule["conditions"]) if rule["conditions"] else {}
            )
            rules.append(rule)
        return rules

    def get_all_rules(self, include_disabled: bool = True) -> list[dict]:
        """
        获取所有规则（用于管理界面）

        Args:
            include_disabled: 是否包含禁用的规则

        Returns:
            规则列表
        """
        if include_disabled:
            sql = "SELECT * FROM rules ORDER BY priority ASC"
        else:
            sql = "SELECT * FROM rules WHERE enabled = 1 ORDER BY priority ASC"

        cursor = self.conn.execute(sql)
        rules = []
        for row in cursor.fetchall():
            rule = dict(row)
            rule["conditions"] = (
                json.loads(rule["conditions"]) if rule["conditions"] else {}
            )
            rules.append(rule)
        return rules

    def create_rule(
        self,
        name: str,
        conditions: dict,
        action: str,
        rule_type: str = "keyword",
        priority: int = 100,
        product_id: int = None,
        enabled: bool = True,
    ) -> int:
        """
        创建新规则

        Args:
            name: 规则名称
            conditions: 条件字典
            action: 动作
            rule_type: 规则类型 (keyword/asin/all)
            priority: 优先级（数值越小优先级越高）
            product_id: 产品ID，为None时为全局规则
            enabled: 是否启用

        Returns:
            规则ID
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO rules (product_id, name, rule_type, conditions, action, priority, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                name,
                rule_type,
                json.dumps(conditions),
                action,
                priority,
                1 if enabled else 0,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def delete_rule(self, rule_id: int) -> bool:
        """
        删除规则

        Args:
            rule_id: 规则ID

        Returns:
            是否删除成功
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def toggle_rule(self, rule_id: int, enabled: bool) -> None:
        """
        切换规则启用/禁用状态

        Args:
            rule_id: 规则ID
            enabled: 是否启用
        """
        self.conn.execute(
            "UPDATE rules SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, rule_id),
        )
        self.conn.commit()

    def reset_rules_to_default(self, product_id: int = None) -> int:
        """
        重置规则为默认值

        Args:
            product_id: 产品ID，为None时重置全局规则

        Returns:
            插入的规则数量
        """
        cursor = self.conn.cursor()
        try:
            # 删除现有规则
            if product_id is None:
                cursor.execute("DELETE FROM rules WHERE product_id IS NULL")
            else:
                cursor.execute("DELETE FROM rules WHERE product_id = ?", (product_id,))

            # 插入默认规则
            for rule in DEFAULT_RULES:
                cursor.execute(
                    """
                    INSERT INTO rules (product_id, name, rule_type, conditions, action, priority)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product_id,
                        rule["name"],
                        rule["rule_type"],
                        json.dumps(rule["conditions"]),
                        rule["action"],
                        rule["priority"],
                    ),
                )
            self.conn.commit()
            return len(DEFAULT_RULES)
        except sqlite3.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"重置规则失败: {e}") from e

    def update_rule(self, rule_id: int, **kwargs) -> None:
        """更新规则"""
        if not kwargs:
            return  # 没有要更新的字段

        # 白名单验证防止SQL注入
        VALID_COLUMNS = {
            "name",
            "rule_type",
            "conditions",
            "action",
            "priority",
            "enabled",
        }
        invalid_cols = set(kwargs.keys()) - VALID_COLUMNS
        if invalid_cols:
            raise ValueError(f"Invalid column names: {invalid_cols}")

        if "conditions" in kwargs and isinstance(kwargs["conditions"], dict):
            kwargs["conditions"] = json.dumps(kwargs["conditions"])

        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [rule_id]

        try:
            self.conn.execute(
                f"UPDATE rules SET {set_clause} WHERE id = ?", tuple(values)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"更新规则失败: {e}") from e

    # ==================== 规则版本操作 ====================

    def create_rule_version(self, product_id: int, description: str = None) -> int:
        """
        创建规则版本快照

        Args:
            product_id: 产品ID
            description: 版本描述

        Returns:
            版本号
        """
        # 获取当前最大版本号
        cursor = self.conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM rule_versions WHERE product_id = ?",
            (product_id,),
        )
        max_version = cursor.fetchone()[0]
        new_version = max_version + 1

        # 获取当前规则
        rules = self.get_rules(product_id)
        snapshot = json.dumps(rules)

        # 保存版本
        self.conn.execute(
            """
            INSERT INTO rule_versions (product_id, version, rules_snapshot, description)
            VALUES (?, ?, ?, ?)
            """,
            (product_id, new_version, snapshot, description),
        )
        self.conn.commit()
        return new_version

    def get_rule_versions(self, product_id: int) -> list[dict]:
        """获取规则版本历史"""
        cursor = self.conn.execute(
            """
            SELECT id, product_id, version, description, created_at
            FROM rule_versions
            WHERE product_id = ?
            ORDER BY version DESC
            """,
            (product_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_rule_version_snapshot(self, product_id: int, version: int) -> list[dict]:
        """获取指定版本的规则快照"""
        cursor = self.conn.execute(
            "SELECT rules_snapshot FROM rule_versions WHERE product_id = ? AND version = ?",
            (product_id, version),
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row["rules_snapshot"])
        return []

    # ==================== 分析结果操作 ====================

    def save_analysis_result(
        self,
        search_term_id: int,
        triggered_rule: str,
        suggested_action: str,
        action_type: str = None,
        confidence: float = 1.0,
        ai_reasoning: str = None,
    ) -> int:
        """保存分析结果"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO analysis_results
            (search_term_id, triggered_rule, suggested_action, action_type, confidence, ai_reasoning)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                search_term_id,
                triggered_rule,
                suggested_action,
                action_type,
                confidence,
                ai_reasoning,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def save_analysis_result_by_term(
        self,
        product_id: int,
        term: str,
        triggered_rule: str,
        suggested_action: str,
        action_type: str = None,
        confidence: float = 1.0,
        ai_reasoning: str = None,
    ) -> int | None:
        """
        通过 term 和 product_id 保存分析结果

        Args:
            product_id: 产品ID
            term: 搜索词
            triggered_rule: 触发的规则
            suggested_action: 建议操作
            action_type: 操作类型
            confidence: 置信度
            ai_reasoning: AI推理说明

        Returns:
            分析结果ID，如果找不到对应的search_term则返回None
        """
        # 查找对应的 search_term_id（取第一个匹配的）
        cursor = self.conn.execute(
            """
            SELECT st.id FROM search_terms st
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ? AND st.term = ?
            LIMIT 1
            """,
            (product_id, term),
        )
        row = cursor.fetchone()

        if not row:
            return None

        return self.save_analysis_result(
            search_term_id=row["id"],
            triggered_rule=triggered_rule,
            suggested_action=suggested_action,
            action_type=action_type,
            confidence=confidence,
            ai_reasoning=ai_reasoning,
        )

    def get_analysis_results(self, filters: dict = None) -> pd.DataFrame:
        """获取分析结果"""
        sql = """
            SELECT ar.*, st.term, st.term_type, st.spend, st.orders, st.acos,
                   c.name as campaign_name, p.name as product_name
            FROM analysis_results ar
            JOIN search_terms st ON ar.search_term_id = st.id
            JOIN campaigns c ON st.campaign_id = c.id
            JOIN products p ON c.product_id = p.id
            WHERE 1=1
        """
        params = []

        if filters:
            if "product_id" in filters:
                sql += " AND c.product_id = ?"
                params.append(filters["product_id"])
            if "action_type" in filters:
                sql += " AND ar.action_type = ?"
                params.append(filters["action_type"])

        sql += " ORDER BY ar.created_at DESC"

        return pd.read_sql_query(sql, self.conn, params=params)

    # ==================== 工具方法 ====================

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return cursor.fetchone() is not None

    def get_table_count(self, table_name: str) -> int:
        """获取表中记录数"""
        # 白名单验证防止SQL注入
        VALID_TABLES = {
            "products",
            "campaigns",
            "search_terms",
            "rules",
            "rule_versions",
            "analysis_results",
            "action_plans",
            "manual_reviews",
        }
        if table_name not in VALID_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]

    # ==================== 人工审核操作 ====================

    def get_manual_reviews(
        self,
        product_id: int,
        campaign_id: int = None,
        reviewed_only: bool = False,
    ) -> dict[str, dict]:
        """
        获取人工审核记录

        Args:
            product_id: 产品ID
            campaign_id: 活动ID（可选，按活动模式时使用）
            reviewed_only: 是否只返回已审核的记录

        Returns:
            以 (term, campaign_id) 为键的审核记录字典
        """
        sql = """
            SELECT * FROM manual_reviews
            WHERE product_id = ?
        """
        params = [product_id]

        if campaign_id is not None:
            sql += " AND (campaign_id = ? OR campaign_id IS NULL)"
            params.append(campaign_id)

        if reviewed_only:
            sql += " AND reviewed = 1"

        cursor = self.conn.execute(sql, tuple(params))
        result = {}
        for row in cursor.fetchall():
            r = dict(row)
            # 使用 (term, campaign_id) 作为键
            key = (r["term"], r.get("campaign_id"))
            result[key] = r
        return result

    def get_manual_reviews_by_term(self, product_id: int, term: str) -> list[dict]:
        """
        获取指定词的所有审核记录

        Args:
            product_id: 产品ID
            term: 搜索词

        Returns:
            审核记录列表
        """
        cursor = self.conn.execute(
            "SELECT * FROM manual_reviews WHERE product_id = ? AND term = ?",
            (product_id, term),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_manual_review_relevance(
        self,
        product_id: int,
        term: str,
        campaign_id: int = None,
    ) -> dict | None:
        """
        获取词的人工相关性标记（用于规则引擎）

        查询优先级:
        1. Local标记 - 特定活动 (campaign_id匹配)
        2. Local标记 - 全局记录 (campaign_id IS NULL)
        3. Global标记 (scope='global')

        Args:
            product_id: 产品ID
            term: 搜索词
            campaign_id: 活动ID（可选）

        Returns:
            包含relevance等字段的字典，或None（未找到）
        """
        cursor = self.conn.cursor()

        # 优先级1: 查找Local标记（特定活动）
        if campaign_id is not None:
            cursor.execute(
                """
                SELECT relevance, relevance_notes, scope,
                       competition_level, competition_notes,
                       ai_suggestion, ai_confidence
                FROM manual_reviews
                WHERE product_id = ? AND term = ? AND campaign_id = ?
                  AND relevance IS NOT NULL
                """,
                (product_id, term, campaign_id),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

        # 优先级2: 查找Local标记（全局记录，campaign_id IS NULL）
        cursor.execute(
            """
            SELECT relevance, relevance_notes, scope,
                   competition_level, competition_notes,
                   ai_suggestion, ai_confidence
            FROM manual_reviews
            WHERE product_id = ? AND term = ? AND campaign_id IS NULL
              AND relevance IS NOT NULL
            """,
            (product_id, term),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)

        # 优先级3: 查找Global标记 (任意campaign_id但scope='global')
        cursor.execute(
            """
            SELECT relevance, relevance_notes, scope,
                   competition_level, competition_notes,
                   ai_suggestion, ai_confidence
            FROM manual_reviews
            WHERE product_id = ? AND term = ? AND scope = 'global'
              AND relevance IS NOT NULL
            LIMIT 1
            """,
            (product_id, term),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)

        return None

    def upsert_manual_review(
        self,
        product_id: int,
        term: str,
        term_type: str = "keyword",
        campaign_id: int = None,
        system_action: str = None,
        final_action: str = None,
        reviewed: bool = False,
        notes: str = None,
        # v2.0: 相关性人工审核字段
        relevance: str = None,
        relevance_notes: str = None,
        scope: str = "local",
        competition_level: str = None,
        competition_notes: str = None,
        ai_suggestion: str = None,
        ai_confidence: float = None,
    ) -> int:
        """
        插入或更新人工审核记录（Upsert）

        Args:
            product_id: 产品ID
            term: 搜索词
            term_type: 词类型 (keyword | asin)
            campaign_id: 活动ID（可选，NULL=全局）
            system_action: 系统建议的动作
            final_action: 用户最终决定的动作
            reviewed: 是否已审核
            notes: 备注
            relevance: 相关性等级 (strong_core|strong_longtail|weak|generic|irrelevant|pending)
            relevance_notes: 相关性判断理由
            scope: 范围 (local|global)
            competition_level: ASIN竞争力 (can_compete|cannot_compete|need_observe)
            competition_notes: 竞争力判断理由
            ai_suggestion: AI建议的相关性
            ai_confidence: AI置信度 (0.0-1.0)

        Returns:
            记录ID
        """
        cursor = self.conn.cursor()

        # 检查是否已存在
        if campaign_id is not None:
            cursor.execute(
                """
                SELECT id FROM manual_reviews
                WHERE product_id = ? AND term = ? AND campaign_id = ?
                """,
                (product_id, term, campaign_id),
            )
        else:
            cursor.execute(
                """
                SELECT id FROM manual_reviews
                WHERE product_id = ? AND term = ? AND campaign_id IS NULL
                """,
                (product_id, term),
            )

        existing = cursor.fetchone()

        if existing:
            # 更新现有记录
            cursor.execute(
                """
                UPDATE manual_reviews
                SET term_type = ?,
                    system_action = COALESCE(?, system_action),
                    final_action = COALESCE(?, final_action),
                    reviewed = ?,
                    notes = COALESCE(?, notes),
                    relevance = COALESCE(?, relevance),
                    relevance_notes = COALESCE(?, relevance_notes),
                    scope = COALESCE(?, scope),
                    competition_level = COALESCE(?, competition_level),
                    competition_notes = COALESCE(?, competition_notes),
                    ai_suggestion = COALESCE(?, ai_suggestion),
                    ai_confidence = COALESCE(?, ai_confidence),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    term_type,
                    system_action,
                    final_action,
                    1 if reviewed else 0,
                    notes,
                    relevance,
                    relevance_notes,
                    scope,
                    competition_level,
                    competition_notes,
                    ai_suggestion,
                    ai_confidence,
                    existing["id"],
                ),
            )
            self.conn.commit()
            return existing["id"]
        else:
            # 插入新记录
            cursor.execute(
                """
                INSERT INTO manual_reviews
                (product_id, term, term_type, campaign_id, system_action, final_action, reviewed, notes,
                 relevance, relevance_notes, scope, competition_level, competition_notes,
                 ai_suggestion, ai_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    term,
                    term_type,
                    campaign_id,
                    system_action,
                    final_action,
                    1 if reviewed else 0,
                    notes,
                    relevance,
                    relevance_notes,
                    scope,
                    competition_level,
                    competition_notes,
                    ai_suggestion,
                    ai_confidence,
                ),
            )
            self.conn.commit()
            return cursor.lastrowid

    def get_pending_reviews_count(self, product_id: int) -> dict:
        """
        获取待审核词的数量统计

        Args:
            product_id: 产品ID

        Returns:
            {
                'total': 总数,
                'keywords': 关键词数量,
                'asins': ASIN数量,
                'no_relevance': 无相关性标记的数量
            }
        """
        cursor = self.conn.cursor()

        # 统计无相关性标记的搜索词（需要人工审核）
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN term_type = 'keyword' THEN 1 ELSE 0 END) as keywords,
                SUM(CASE WHEN term_type = 'asin' THEN 1 ELSE 0 END) as asins
            FROM manual_reviews
            WHERE product_id = ?
              AND (relevance IS NULL OR relevance = 'pending')
            """,
            (product_id,),
        )
        row = cursor.fetchone()

        return {
            "total": row["total"] or 0,
            "keywords": row["keywords"] or 0,
            "asins": row["asins"] or 0,
        }

    def get_pending_reviews_list(
        self,
        product_id: int,
        term_type: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        获取待审核词列表

        Args:
            product_id: 产品ID
            term_type: 筛选词类型 (keyword|asin)，None=全部
            limit: 返回数量限制
            offset: 分页偏移

        Returns:
            待审核记录列表
        """
        cursor = self.conn.cursor()

        query = """
            SELECT mr.*, c.name as campaign_name
            FROM manual_reviews mr
            LEFT JOIN campaigns c ON mr.campaign_id = c.id
            WHERE mr.product_id = ?
              AND (mr.relevance IS NULL OR mr.relevance = 'pending')
        """
        params = [product_id]

        if term_type:
            query += " AND mr.term_type = ?"
            params.append(term_type)

        query += " ORDER BY mr.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def batch_update_relevance(
        self,
        product_id: int,
        updates: list[dict],
    ) -> int:
        """
        批量更新相关性标记

        Args:
            product_id: 产品ID
            updates: 更新列表，每条包含:
                - term: 搜索词
                - campaign_id: 活动ID（可选）
                - relevance: 相关性等级
                - relevance_notes: 备注（可选）
                - scope: 范围（可选，默认'local'）

        Returns:
            更新的记录数
        """
        count = 0
        for update in updates:
            self.upsert_manual_review(
                product_id=product_id,
                term=update["term"],
                campaign_id=update.get("campaign_id"),
                relevance=update.get("relevance"),
                relevance_notes=update.get("relevance_notes"),
                scope=update.get("scope", "local"),
                reviewed=True,  # 标记为已审核
            )
            count += 1
        return count

    def update_manual_review_ai_suggestion(
        self,
        product_id: int,
        term: str,
        ai_suggestion: str,
        ai_confidence: float,
    ) -> bool:
        """
        更新manual_review的AI建议字段（T53）

        Args:
            product_id: 产品ID
            term: 搜索词
            ai_suggestion: AI建议的相关性等级
            ai_confidence: AI置信度

        Returns:
            是否更新成功
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE manual_reviews
                SET ai_suggestion = ?,
                    ai_confidence = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ? AND term = ?
                """,
                [ai_suggestion, ai_confidence, product_id, term],
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新AI建议失败: {e}")
            return False

    def get_keywords_by_category(
        self,
        product_id: int,
        category: str,
    ) -> list[str]:
        """
        获取指定类别的关键词列表（T53用于构建产品上下文）

        Args:
            product_id: 产品ID
            category: 关键词类别 (core|generic|weak|irrelevant|car)

        Returns:
            关键词列表
        """
        product = self.get_product(product_id)
        if not product:
            return []

        config = product.get("config", {})

        # 直接在config顶层的关键词
        if category == "core":
            return config.get("core_keywords", [])
        elif category == "related":
            return config.get("related_keywords", [])

        # keyword_libraries 中的关键词
        libraries = config.get("keyword_libraries", {})
        category_mapping = {
            "generic": "generic_keywords",
            "irrelevant": "irrelevant_keywords",
            "car": "car_keywords",
            "weak_category": "weak_category_keywords",
            "weak_exact": "weak_exact_keywords",
        }

        if category in category_mapping:
            return libraries.get(category_mapping[category], [])

        # weak 包含两种弱相关词
        if category == "weak":
            weak_category = libraries.get("weak_category_keywords", [])
            weak_exact = libraries.get("weak_exact_keywords", [])
            return weak_category + weak_exact

        return []

    def batch_update_reviews(
        self,
        product_id: int,
        reviews: list[dict],
    ) -> int:
        """
        批量更新审核状态

        Args:
            product_id: 产品ID
            reviews: 审核记录列表，每条包含:
                - term: 搜索词
                - campaign_id: 活动ID（可选）
                - reviewed: 是否已审核
                - final_action: 最终动作（可选）

        Returns:
            更新的记录数
        """
        count = 0
        for review in reviews:
            self.upsert_manual_review(
                product_id=product_id,
                term=review["term"],
                term_type=review.get("term_type", "keyword"),
                campaign_id=review.get("campaign_id"),
                system_action=review.get("system_action"),
                final_action=review.get("final_action"),
                reviewed=review.get("reviewed", False),
                notes=review.get("notes"),
            )
            count += 1
        return count

    def get_review_stats(self, product_id: int) -> dict:
        """
        获取审核统计

        Args:
            product_id: 产品ID

        Returns:
            统计信息字典
        """
        cursor = self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN reviewed = 1 THEN 1 ELSE 0 END) as reviewed,
                SUM(CASE WHEN reviewed = 0 THEN 1 ELSE 0 END) as pending
            FROM manual_reviews
            WHERE product_id = ?
            """,
            (product_id,),
        )
        row = cursor.fetchone()
        return {
            "total": row["total"] or 0,
            "reviewed": row["reviewed"] or 0,
            "pending": row["pending"] or 0,
        }
