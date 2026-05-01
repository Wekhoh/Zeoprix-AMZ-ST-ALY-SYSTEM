"""Workbench 设置/备份/规则版本 mutation 模块 — Step 3 H3a 抽出。

把 settings/backup/rule-version 类的 6 个 *_for_frontend 写入函数从
workbench_payload.py 剥离：

  - clear_runtime_for_frontend
  - export_full_backup_for_frontend
  - restore_full_backup_for_frontend
  - update_settings_config_for_frontend
  - restore_settings_rule_version_for_frontend
  - preview_settings_rule_version_for_frontend

外部调用方（app.py）通过 workbench_payload 末尾的 re-export 保持不感知。
"""

from __future__ import annotations

from typing import Any

from src.backend.workbench_payload import (
    _format_timestamp,
    _get_app_database_path,
)
from src.data.db import Database
from src.services.settings_service import (
    build_full_backup_export_payload,
    clear_product_runtime_data,
    restore_full_backup,
    save_config_version,
)


def clear_runtime_for_frontend(*, product_id: int) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        clear_product_runtime_data(db, product_id)
        return {"status": "success", "message": "运行数据已清空。"}


def export_full_backup_for_frontend(*, product_id: int) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        payload = build_full_backup_export_payload(db, product_id)
        if not payload:
            raise ValueError("产品不存在")
        return {
            "fileName": payload["file_name"],
            "mime": payload["mime"],
            "content": payload["data"].decode("utf-8"),
            "summary": payload["summary"],
        }


def restore_full_backup_for_frontend(
    *,
    product_id: int | None,
    restore_as_new_product: bool,
    backup_data: dict,
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        restored_product_id = restore_full_backup(
            db,
            backup_data,
            current_product_id=product_id,
            restore_as_new_product=restore_as_new_product,
        )
        product = db.get_product(restored_product_id)
        return {
            "status": "success",
            "restoredProductId": restored_product_id,
            "productName": product.get("name") if product else "恢复产品",
        }


def update_settings_config_for_frontend(
    *,
    product_id: int,
    core_keywords: list[str],
    related_keywords: list[str],
    competitor_asins: list[str],
    own_variants: list[str],
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    normalized = {
        "core_keywords": [item.strip() for item in core_keywords if str(item).strip()],
        "related_keywords": [
            item.strip() for item in related_keywords if str(item).strip()
        ],
        "competitor_asins": [
            item.strip().upper() for item in competitor_asins if str(item).strip()
        ],
        "own_variants": [
            item.strip().upper() for item in own_variants if str(item).strip()
        ],
    }
    with Database(str(db_path)) as db:
        product = db.get_product(product_id)
        if not product:
            raise ValueError("产品不存在")
        previous_config = product.get("config") or {}
        next_config = {**previous_config, **normalized}
        save_config_version(db, product_id, previous_config, next_config)
        db.update_product_config(product_id, next_config)
        rule_versions = db.get_rule_versions(product_id)
        return {
            "status": "success",
            "message": "产品配置已更新。",
            "configEditor": {
                "coreKeywords": normalized["core_keywords"],
                "relatedKeywords": normalized["related_keywords"],
                "competitorAsins": normalized["competitor_asins"],
                "ownVariants": normalized["own_variants"],
            },
            "ruleVersionCount": len(rule_versions),
            "recentRuleVersions": [
                {
                    "version": int(item.get("version") or 0),
                    "createdAt": _format_timestamp(item.get("created_at")),
                    "description": str(item.get("description") or "配置更新")[:160],
                }
                for item in rule_versions[:5]
            ],
        }


def restore_settings_rule_version_for_frontend(
    *, product_id: int, version: int
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = db.get_product(product_id)
        if not product:
            raise ValueError("产品不存在")
        restored_snapshot = db.get_rule_version_snapshot(product_id, version)
        if not restored_snapshot:
            raise ValueError("指定规则版本不存在")
        previous_config = product.get("config") or {}
        next_config = {**previous_config, "rules": restored_snapshot}
        save_config_version(db, product_id, previous_config, next_config)
        db.update_product_config(product_id, next_config)
        rule_versions = db.get_rule_versions(product_id)
        return {
            "status": "success",
            "message": f"已恢复规则版本 v{version}。",
            "ruleVersionCount": len(rule_versions),
            "recentRuleVersions": [
                {
                    "version": int(item.get("version") or 0),
                    "createdAt": _format_timestamp(item.get("created_at")),
                    "description": str(item.get("description") or "配置更新")[:160],
                }
                for item in rule_versions[:5]
            ],
        }


def preview_settings_rule_version_for_frontend(
    *, product_id: int, version: int
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = db.get_product(product_id)
        if not product:
            raise ValueError("产品不存在")

        snapshot = db.get_rule_version_snapshot(product_id, version)
        if not snapshot:
            raise ValueError("指定规则版本不存在")

        current_config = product.get("config") or {}
        snapshot_core = [
            str(item).strip()
            for item in snapshot.get("core_keywords", [])
            if str(item).strip()
        ]
        snapshot_related = [
            str(item).strip()
            for item in snapshot.get("related_keywords", [])
            if str(item).strip()
        ]
        snapshot_competitors = [
            str(item).strip().upper()
            for item in snapshot.get("competitor_asins", [])
            if str(item).strip()
        ]
        snapshot_variants = [
            str(item).strip().upper()
            for item in snapshot.get("own_variants", [])
            if str(item).strip()
        ]

        current_core = [
            str(item).strip()
            for item in current_config.get("core_keywords", [])
            if str(item).strip()
        ]
        current_related = [
            str(item).strip()
            for item in current_config.get("related_keywords", [])
            if str(item).strip()
        ]
        current_competitors = [
            str(item).strip().upper()
            for item in current_config.get("competitor_asins", [])
            if str(item).strip()
        ]
        current_variants = [
            str(item).strip().upper()
            for item in current_config.get("own_variants", [])
            if str(item).strip()
        ]

        def _delta(target: list[str], current: list[str]) -> dict[str, list[str]]:
            target_set = set(target)
            current_set = set(current)
            return {
                "added": sorted(target_set - current_set),
                "removed": sorted(current_set - target_set),
            }

        return {
            "status": "success",
            "version": version,
            "configEditor": {
                "coreKeywords": snapshot_core,
                "relatedKeywords": snapshot_related,
                "competitorAsins": snapshot_competitors,
                "ownVariants": snapshot_variants,
            },
            "diff": {
                "coreKeywords": _delta(snapshot_core, current_core),
                "relatedKeywords": _delta(snapshot_related, current_related),
                "competitorAsins": _delta(snapshot_competitors, current_competitors),
                "ownVariants": _delta(snapshot_variants, current_variants),
            },
        }
