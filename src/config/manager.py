"""
配置版本管理模块
支持规则配置的版本控制和回滚
"""

import json
from typing import Any

from src.config.logger import get_logger
from src.data.db import Database

logger = get_logger(__name__)


class ConfigManager:
    """配置版本管理器"""

    def __init__(self, db: Database):
        """
        初始化配置管理器

        Args:
            db: 数据库实例
        """
        self.db = db

    # ==================== 产品配置 ====================

    def get_product_config(self, product_id: int) -> dict:
        """
        获取产品配置

        Args:
            product_id: 产品ID

        Returns:
            产品配置字典
        """
        product = self.db.get_product(product_id)
        if product:
            return product.get("config", {})
        return {}

    def update_product_config(
        self, product_id: int, config: dict, merge: bool = True
    ) -> None:
        """
        更新产品配置

        Args:
            product_id: 产品ID
            config: 新配置
            merge: 是否合并（True=合并，False=替换）
        """
        if merge:
            current_config = self.get_product_config(product_id)
            current_config.update(config)
            config = current_config

        self.db.update_product(product_id, config=config)
        logger.info(f"更新产品 {product_id} 配置")

    def set_core_keywords(self, product_id: int, keywords: list[str]) -> None:
        """设置核心关键词"""
        self.update_product_config(product_id, {"core_keywords": keywords})

    def set_related_keywords(self, product_id: int, keywords: list[str]) -> None:
        """设置相关关键词"""
        self.update_product_config(product_id, {"related_keywords": keywords})

    def set_own_asins(self, product_id: int, asins: list[str]) -> None:
        """设置自有ASIN列表"""
        self.update_product_config(product_id, {"own_asins": asins})

    # ==================== 规则管理 ====================

    def get_current_rules(self, product_id: int = None) -> list[dict]:
        """
        获取当前规则配置

        Args:
            product_id: 产品ID（为None时获取全局规则）

        Returns:
            规则列表
        """
        return self.db.get_rules(product_id)

    def update_rule(self, rule_id: int, **kwargs) -> None:
        """
        更新规则

        Args:
            rule_id: 规则ID
            **kwargs: 要更新的字段
        """
        self.db.update_rule(rule_id, **kwargs)
        logger.info(f"更新规则 {rule_id}")

    def update_rule_threshold(
        self, rule_id: int, threshold_name: str, value: Any
    ) -> None:
        """
        更新规则阈值

        Args:
            rule_id: 规则ID
            threshold_name: 阈值名称
            value: 新值
        """
        # 获取当前规则
        cursor = self.db.execute(
            "SELECT conditions FROM rules WHERE id = ?", (rule_id,)
        )
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"规则 {rule_id} 不存在")

        conditions = json.loads(row["conditions"]) if row["conditions"] else {}
        conditions[threshold_name] = value

        self.db.update_rule(rule_id, conditions=conditions)
        logger.info(f"更新规则 {rule_id} 阈值 {threshold_name}={value}")

    def enable_rule(self, rule_id: int) -> None:
        """启用规则"""
        self.db.update_rule(rule_id, enabled=1)
        logger.info(f"启用规则 {rule_id}")

    def disable_rule(self, rule_id: int) -> None:
        """禁用规则"""
        self.db.update_rule(rule_id, enabled=0)
        logger.info(f"禁用规则 {rule_id}")

    # ==================== 版本管理 ====================

    def create_version(self, product_id: int, description: str = None) -> int:
        """
        创建配置版本快照

        Args:
            product_id: 产品ID
            description: 版本描述

        Returns:
            新版本号
        """
        version = self.db.create_rule_version(product_id, description)
        logger.info(f"创建产品 {product_id} 配置版本 v{version}")
        return version

    def get_version_history(self, product_id: int) -> list[dict]:
        """
        获取版本历史

        Args:
            product_id: 产品ID

        Returns:
            版本历史列表
        """
        return self.db.get_rule_versions(product_id)

    def get_version_snapshot(self, product_id: int, version: int) -> list[dict]:
        """
        获取指定版本的规则快照

        Args:
            product_id: 产品ID
            version: 版本号

        Returns:
            规则快照
        """
        return self.db.get_rule_version_snapshot(product_id, version)

    def rollback(self, product_id: int, target_version: int) -> None:
        """
        回滚到指定版本

        Args:
            product_id: 产品ID
            target_version: 目标版本号
        """
        # 1. 创建当前状态的快照（保护性备份）
        self.create_version(product_id, "回滚前自动备份")

        # 2. 获取目标版本快照
        snapshot = self.get_version_snapshot(product_id, target_version)

        if not snapshot:
            raise ValueError(f"版本 {target_version} 不存在或快照为空")

        # 3. 删除当前产品规则
        self.db.execute("DELETE FROM rules WHERE product_id = ?", (product_id,))

        # 4. 恢复快照中的规则
        for rule in snapshot:
            # 跳过全局规则
            if rule.get("product_id") is None:
                continue

            self.db.execute(
                """
                INSERT INTO rules (product_id, name, rule_type, conditions, action, priority, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    rule["name"],
                    rule["rule_type"],
                    json.dumps(rule["conditions"])
                    if isinstance(rule["conditions"], dict)
                    else rule["conditions"],
                    rule["action"],
                    rule["priority"],
                    rule.get("enabled", 1),
                ),
            )

        self.db.commit()
        logger.info(f"回滚产品 {product_id} 配置到版本 v{target_version}")

    def compare_versions(self, product_id: int, version1: int, version2: int) -> dict:
        """
        对比两个版本的差异

        Args:
            product_id: 产品ID
            version1: 版本1
            version2: 版本2

        Returns:
            差异信息
        """
        snapshot1 = self.get_version_snapshot(product_id, version1)
        snapshot2 = self.get_version_snapshot(product_id, version2)

        rules1 = {r["name"]: r for r in snapshot1}
        rules2 = {r["name"]: r for r in snapshot2}

        added = set(rules2.keys()) - set(rules1.keys())
        removed = set(rules1.keys()) - set(rules2.keys())
        modified = []

        for name in set(rules1.keys()) & set(rules2.keys()):
            if rules1[name] != rules2[name]:
                modified.append(
                    {
                        "name": name,
                        "before": rules1[name],
                        "after": rules2[name],
                    }
                )

        return {
            "added": list(added),
            "removed": list(removed),
            "modified": modified,
        }


def get_config_manager(db: Database) -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager(db)
