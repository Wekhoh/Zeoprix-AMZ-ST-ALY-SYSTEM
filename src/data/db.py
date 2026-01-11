"""
数据库操作模块
提供SQLite数据库的初始化和CRUD操作
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.models import ALL_SCHEMAS, DEFAULT_RULES, INDEXES
from src.rules.asin_rules import is_valid_asin


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
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
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
            for table_name, schema in ALL_SCHEMAS:
                cursor.execute(schema)

            # 创建索引
            for index_sql in INDEXES:
                cursor.execute(index_sql)

            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"初始化数据库失败: {e}") from e

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

    def create_product(self, name: str, asin: str = None, category: str = None, config: dict = None) -> int:
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
            product["config"] = json.loads(product["config"]) if product["config"] else {}
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
            self.conn.execute(
                f"UPDATE products SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                tuple(values),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"更新产品失败: {e}") from e

    # ==================== 广告活动操作 ====================

    def create_campaign(self, product_id: int, name: str, match_type: str = None, bid_strategy: str = None) -> int:
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

    def get_or_create_campaign(self, product_id: int, name: str, match_type: str = None) -> int:
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

    def get_rules(self, product_id: int = None) -> list[dict]:
        """
        获取规则配置

        Args:
            product_id: 产品ID，为None时获取全局规则

        Returns:
            规则列表
        """
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
            rule["conditions"] = json.loads(rule["conditions"]) if rule["conditions"] else {}
            rules.append(rule)
        return rules

    def update_rule(self, rule_id: int, **kwargs) -> None:
        """更新规则"""
        if not kwargs:
            return  # 没有要更新的字段

        # 白名单验证防止SQL注入
        VALID_COLUMNS = {"name", "rule_type", "conditions", "action", "priority", "enabled"}
        invalid_cols = set(kwargs.keys()) - VALID_COLUMNS
        if invalid_cols:
            raise ValueError(f"Invalid column names: {invalid_cols}")

        if "conditions" in kwargs and isinstance(kwargs["conditions"], dict):
            kwargs["conditions"] = json.dumps(kwargs["conditions"])

        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [rule_id]

        try:
            self.conn.execute(f"UPDATE rules SET {set_clause} WHERE id = ?", tuple(values))
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
            (search_term_id, triggered_rule, suggested_action, action_type, confidence, ai_reasoning),
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
            "products", "campaigns", "search_terms", "rules",
            "rule_versions", "analysis_results", "action_plans"
        }
        if table_name not in VALID_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
