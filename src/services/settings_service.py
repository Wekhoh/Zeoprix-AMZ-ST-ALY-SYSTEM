"""Settings + backup service — Sprint 5 · B.5a (实际实现已内联)。

本模块是"设置 / 备份 / 清空 / 配置版本"业务逻辑的**唯一官方入口**，
被 backend（`src/backend/workbench_payload.py`）以及遗留 Streamlit UI
（`src/ui/pages/settings_data.py` 现已 re-export 回来）共同使用。

## 历史演进

- B.2（shim 阶段，9d852eb）：新建 service 层，re-export 自
  `src/ui/pages/settings_data.py` —— backend 从"直接 import src.ui.*"解耦。
- B.2 续（f2717e9）：re-export 改为惰性 wrapper，backend 冷启动不再拖
  streamlit。
- **B.5a（当前）：** 6 个纯数据函数 + 2 个 helper 的 body 内联到本文件；
  `settings_data.py` 反向 re-export，为 B.5d 删除 `src/ui/*` 扫清依赖。

## 依赖

- `db` 参数为 `src.data.db.Database` 实例；未在签名强类型化，与原 Streamlit
  代码保持一致。
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from uuid import uuid4

from src.config.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "build_full_backup_export_payload",
    "build_rule_config_export_payload",
    "clear_product_runtime_data",
    "get_default_config",
    "restore_full_backup",
    "save_config_version",
]


# ── 内部 helpers ─────────────────────────────────────────────────────────


def _fetch_rows(db, sql: str, params: tuple = ()) -> list[dict]:
    """以 dict 列表形式读取查询结果。"""
    cursor = db.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]


def _delete_product_backup_records(db, product_id: int) -> None:
    """删除产品级备份 / 版本数据，供完整恢复覆盖当前产品时使用。"""
    db.execute("DELETE FROM rule_versions WHERE product_id = ?", (product_id,))
    db.execute(
        "DELETE FROM strategy_profiles WHERE source_product_id = ?", (product_id,)
    )
    db.commit()


# ── 公共 API ─────────────────────────────────────────────────────────────


def clear_product_runtime_data(db, product_id: int) -> None:
    """清空产品运行数据，保留产品配置与规则配置。

    所有 DELETE 包在显式事务（BEGIN IMMEDIATE）内，中途失败 rollback 全部，
    避免半清空状态。daily_pacing 用 sqlite_master 探测代替 try/except，
    不再吞 sqlite3.Error。
    """
    has_pacing = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='daily_pacing'"
    ).fetchone()
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM execution_batches WHERE product_id = ?", (product_id,))
        db.execute(
            """
            DELETE FROM action_plans
            WHERE analysis_result_id IN (
                SELECT ar.id FROM analysis_results ar
                JOIN search_terms st ON ar.search_term_id = st.id
                JOIN campaigns c ON st.campaign_id = c.id
                WHERE c.product_id = ?
            )
            """,
            (product_id,),
        )
        db.execute(
            """
            DELETE FROM analysis_results
            WHERE search_term_id IN (
                SELECT st.id FROM search_terms st
                JOIN campaigns c ON st.campaign_id = c.id
                WHERE c.product_id = ?
            )
            """,
            (product_id,),
        )
        db.execute(
            "DELETE FROM analysis_run_snapshots WHERE product_id = ?",
            (product_id,),
        )
        db.execute(
            """
            DELETE FROM search_terms
            WHERE campaign_id IN (
                SELECT id FROM campaigns WHERE product_id = ?
            )
            """,
            (product_id,),
        )
        db.execute("DELETE FROM manual_reviews WHERE product_id = ?", (product_id,))
        if has_pacing:
            db.execute("DELETE FROM daily_pacing WHERE product_id = ?", (product_id,))
        db.execute("DELETE FROM campaigns WHERE product_id = ?", (product_id,))
        db.commit()
    except sqlite3.Error as exc:
        try:
            db.conn.rollback()
        except Exception:
            pass
        logger.error("clear_product_runtime_data 失败已回滚: %s", exc, exc_info=True)
        raise


def build_rule_config_export_payload(db, product_id: int) -> dict | None:
    """构建规则配置的直接下载载荷。"""
    product = db.get_product(product_id)
    if not product:
        return None

    export_data = {
        "export_type": "rule_config",
        "product_name": product.get("name", ""),
        "config": product.get("config", {}),
    }
    return {
        "data": json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8"),
        "file_name": f"rules_{product.get('name', 'config')}.json",
        "mime": "application/json",
    }


def build_full_backup_export_payload(db, product_id: int) -> dict | None:
    """构建完整数据备份的直接下载载荷。"""
    product = db.get_product(product_id)
    if not product:
        return None

    backup_data = {
        "export_type": "full_backup",
        "export_time": datetime.datetime.now().isoformat(),
        "product": {
            "name": product.get("name", ""),
            "asin": product.get("asin", ""),
            "category": product.get("category", ""),
            "config": product.get("config", {}),
        },
        "schema_version": 2,
        "campaigns": [],
        "search_terms": [],
        "analysis_results": [],
        "action_plans": [],
        "manual_reviews": [],
        "analysis_run_snapshots": [],
        "execution_batches": [],
        "rule_versions": [],
        "strategy_profiles": [],
        "search_terms_count": 0,
        "analysis_results_count": 0,
    }
    backup_data["campaigns"] = _fetch_rows(
        db,
        "SELECT id, name, match_type, bid_strategy, created_at FROM campaigns WHERE product_id = ? ORDER BY id",
        (product_id,),
    )
    backup_data["search_terms"] = _fetch_rows(
        db,
        """
        SELECT st.*
        FROM search_terms st
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ?
        ORDER BY st.id
        """,
        (product_id,),
    )
    backup_data["analysis_results"] = _fetch_rows(
        db,
        """
        SELECT ar.*
        FROM analysis_results ar
        JOIN search_terms st ON ar.search_term_id = st.id
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ?
        ORDER BY ar.id
        """,
        (product_id,),
    )
    backup_data["action_plans"] = _fetch_rows(
        db,
        """
        SELECT ap.*
        FROM action_plans ap
        JOIN analysis_results ar ON ap.analysis_result_id = ar.id
        JOIN search_terms st ON ar.search_term_id = st.id
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ?
        ORDER BY ap.id
        """,
        (product_id,),
    )
    backup_data["manual_reviews"] = _fetch_rows(
        db,
        "SELECT * FROM manual_reviews WHERE product_id = ? ORDER BY id",
        (product_id,),
    )
    backup_data["analysis_run_snapshots"] = _fetch_rows(
        db,
        """
        SELECT id, product_id, run_source, summary_json, snapshot_json, created_at
        FROM analysis_run_snapshots
        WHERE product_id = ?
        ORDER BY id
        """,
        (product_id,),
    )
    backup_data["execution_batches"] = _fetch_rows(
        db,
        """
        SELECT id, product_id, batch_code, batch_type, status, item_count, summary_json,
               draft_note, execution_note, review_note, executed_at, reviewed_at,
               created_at, updated_at
        FROM execution_batches
        WHERE product_id = ?
        ORDER BY id
        """,
        (product_id,),
    )
    backup_data["rule_versions"] = _fetch_rows(
        db,
        """
        SELECT id, version, rules_snapshot, description, created_at
        FROM rule_versions
        WHERE product_id = ?
        ORDER BY version
        """,
        (product_id,),
    )
    backup_data["strategy_profiles"] = _fetch_rows(
        db,
        """
        SELECT id, name, lifecycle, goal, config_snapshot, notes, source_product_id, created_at, updated_at
        FROM strategy_profiles
        WHERE source_product_id = ?
        ORDER BY id
        """,
        (product_id,),
    )
    backup_data["search_terms_count"] = len(backup_data["search_terms"])
    backup_data["analysis_results_count"] = len(backup_data["analysis_results"])

    return {
        "data": json.dumps(backup_data, ensure_ascii=False, indent=2).encode("utf-8"),
        "file_name": f"backup_{product.get('name', 'data')}_{datetime.datetime.now().strftime('%Y%m%d')}.json",
        "mime": "application/json",
        "summary": {
            "search_terms_count": backup_data["search_terms_count"],
            "analysis_results_count": backup_data["analysis_results_count"],
            "manual_reviews_count": len(backup_data["manual_reviews"]),
            "snapshots_count": len(backup_data["analysis_run_snapshots"]),
            "execution_batches_count": len(backup_data["execution_batches"]),
        },
    }


_BACKUP_LIST_KEYS = (
    "campaigns",
    "search_terms",
    "analysis_results",
    "action_plans",
    "manual_reviews",
    "execution_batches",
    "analysis_run_snapshots",
)

# 必须含 id (int) 的 list — 跨表外键映射依赖
_BACKUP_LISTS_NEEDING_ID = ("campaigns", "search_terms", "analysis_results")


def _validate_backup_schema(backup_data: object) -> None:
    """Audit HIGH-1 — schema 校验 backup JSON。

    防止恶意/损坏文件破坏数据库：在写循环开始前一次性 validate，校验失败
    raise ValueError 不进 DB。否则中途 TypeError/KeyError 会留下半写入的
    脏数据（campaign 已插入但 search_terms 失败回不去）。

    校验规则：
      - 顶层必须 dict
      - export_type == "full_backup"
      - product 必须 dict
      - 列表字段（若存在）必须 list of dict
      - campaigns/search_terms/analysis_results 每项必须有 int id
      - analysis_results 每项必须有 int search_term_id
      - action_plans 每项必须有 int analysis_result_id
    """
    if not isinstance(backup_data, dict):
        raise ValueError("备份文件不是有效的 JSON 对象。")
    if backup_data.get("export_type") != "full_backup":
        raise ValueError("当前文件不是完整数据备份。")
    if not isinstance(backup_data.get("product"), dict):
        raise ValueError("备份缺少 product 字段或类型错误。")

    for key in _BACKUP_LIST_KEYS:
        value = backup_data.get(key)
        if value is None:
            continue
        if not isinstance(value, list):
            raise ValueError(f"备份字段 {key} 类型错误，应为 list。")
        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                raise ValueError(f"备份字段 {key}[{idx}] 类型错误，应为 object。")

    for key in _BACKUP_LISTS_NEEDING_ID:
        for idx, item in enumerate(backup_data.get(key) or []):
            if not isinstance(item.get("id"), int):
                raise ValueError(f"备份 {key}[{idx}].id 缺失或非整数。")

    for idx, item in enumerate(backup_data.get("analysis_results") or []):
        if not isinstance(item.get("search_term_id"), int):
            raise ValueError(
                f"备份 analysis_results[{idx}].search_term_id 缺失或非整数。"
            )

    for idx, item in enumerate(backup_data.get("action_plans") or []):
        if not isinstance(item.get("analysis_result_id"), int):
            raise ValueError(
                f"备份 action_plans[{idx}].analysis_result_id 缺失或非整数。"
            )


def restore_full_backup(
    db,
    backup_data: dict,
    *,
    current_product_id: int | None = None,
    restore_as_new_product: bool = False,
) -> int:
    """从完整备份恢复产品数据，支持覆盖当前产品或恢复为新产品副本。"""
    # Audit HIGH-1: 写库之前先 schema 校验，杜绝半写入留脏数据
    _validate_backup_schema(backup_data)

    product_payload = backup_data.get("product") or {}
    product_name = str(product_payload.get("name") or "恢复产品").strip() or "恢复产品"
    product_asin = (product_payload.get("asin") or "").strip() or None
    product_category = (product_payload.get("category") or "").strip() or None
    product_config = product_payload.get("config") or {}

    if restore_as_new_product:
        target_name = f"{product_name}（恢复）"
        target_product_id = db.create_product(
            name=target_name,
            asin=product_asin,
            category=product_category,
            config=product_config,
        )
    else:
        if not current_product_id:
            raise ValueError("覆盖当前产品恢复时必须先选择产品。")
        target_product_id = current_product_id
        db.update_product(
            target_product_id,
            name=product_name,
            asin=product_asin,
            category=product_category,
            config=product_config,
        )
        clear_product_runtime_data(db, target_product_id)
        _delete_product_backup_records(db, target_product_id)

    campaign_id_map: dict[int, int] = {}
    for campaign in backup_data.get("campaigns", []):
        cursor = db.execute(
            """
            INSERT INTO campaigns (product_id, name, match_type, bid_strategy, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                target_product_id,
                campaign.get("name"),
                campaign.get("match_type"),
                campaign.get("bid_strategy"),
                campaign.get("created_at"),
            ),
        )
        campaign_id_map[int(campaign["id"])] = cursor.lastrowid

    search_term_id_map: dict[int, int] = {}
    for search_term in backup_data.get("search_terms", []):
        old_campaign_id = search_term.get("campaign_id")
        new_campaign_id = (
            campaign_id_map.get(int(old_campaign_id))
            if old_campaign_id is not None
            else None
        )
        cursor = db.execute(
            """
            INSERT INTO search_terms (
                campaign_id, term, term_type, impressions, clicks, ctr, spend, cpc,
                orders, sales, acos, roas, conversion_rate, report_date, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_campaign_id,
                search_term.get("term"),
                search_term.get("term_type"),
                search_term.get("impressions", 0),
                search_term.get("clicks", 0),
                search_term.get("ctr", 0.0),
                search_term.get("spend", 0.0),
                search_term.get("cpc", 0.0),
                search_term.get("orders", 0),
                search_term.get("sales", 0.0),
                search_term.get("acos", 0.0),
                search_term.get("roas", 0.0),
                search_term.get("conversion_rate", 0.0),
                search_term.get("report_date"),
                search_term.get("created_at"),
            ),
        )
        search_term_id_map[int(search_term["id"])] = cursor.lastrowid

    analysis_result_id_map: dict[int, int] = {}
    for result in backup_data.get("analysis_results", []):
        old_search_term_id = int(result["search_term_id"])
        cursor = db.execute(
            """
            INSERT INTO analysis_results (
                search_term_id, triggered_rule, suggested_action, action_type,
                confidence, ai_reasoning, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                search_term_id_map[old_search_term_id],
                result.get("triggered_rule"),
                result.get("suggested_action"),
                result.get("action_type"),
                result.get("confidence", 1.0),
                result.get("ai_reasoning"),
                result.get("created_at"),
            ),
        )
        analysis_result_id_map[int(result["id"])] = cursor.lastrowid

    for action_plan in backup_data.get("action_plans", []):
        old_result_id = int(action_plan["analysis_result_id"])
        if old_result_id not in analysis_result_id_map:
            continue
        db.execute(
            """
            INSERT INTO action_plans (
                analysis_result_id, action, status, notes, executed_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_result_id_map[old_result_id],
                action_plan.get("action"),
                action_plan.get("status", "pending"),
                action_plan.get("notes"),
                action_plan.get("executed_at"),
                action_plan.get("created_at"),
            ),
        )

    for review in backup_data.get("manual_reviews", []):
        old_campaign_id = review.get("campaign_id")
        new_campaign_id = (
            campaign_id_map.get(int(old_campaign_id))
            if old_campaign_id not in (None, "")
            else None
        )
        db.execute(
            """
            INSERT INTO manual_reviews (
                product_id, term, term_type, campaign_id, asin_identifier, relevance,
                relevance_notes, scope, competition_level, competition_notes,
                ai_suggestion, ai_confidence, review_source, truth_action_type,
                manual_action, auto_action, negate_keyword, negate_asin,
                action_matrix, conflict_flag, evidence_payload, system_action,
                final_action, reviewed, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                target_product_id,
                review.get("term"),
                review.get("term_type", "keyword"),
                new_campaign_id,
                review.get("asin_identifier"),
                review.get("relevance"),
                review.get("relevance_notes"),
                review.get("scope", "local"),
                review.get("competition_level"),
                review.get("competition_notes"),
                review.get("ai_suggestion"),
                review.get("ai_confidence"),
                review.get("review_source"),
                review.get("truth_action_type"),
                review.get("manual_action"),
                review.get("auto_action"),
                review.get("negate_keyword"),
                review.get("negate_asin"),
                review.get("action_matrix"),
                review.get("conflict_flag", 0),
                review.get("evidence_payload"),
                review.get("system_action"),
                review.get("final_action"),
                review.get("reviewed", 0),
                review.get("notes"),
                review.get("created_at"),
                review.get("updated_at"),
            ),
        )

    for snapshot in backup_data.get("analysis_run_snapshots", []):
        db.execute(
            """
            INSERT INTO analysis_run_snapshots (
                product_id, run_source, summary_json, snapshot_json, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                target_product_id,
                snapshot.get("run_source", "manual"),
                snapshot.get("summary_json"),
                snapshot.get("snapshot_json"),
                snapshot.get("created_at"),
            ),
        )

    for batch in backup_data.get("execution_batches", []):
        # restore_as_new_product 模式下源产品的 batch_code 仍占着 UNIQUE 槽位，
        # 给恢复进来的批次加 -RST<uuid6> 后缀防冲突；保留原 code 便于追溯。
        raw_code = batch.get("batch_code")
        batch_code = (
            f"{raw_code}-RST{uuid4().hex[:6].upper()}"
            if restore_as_new_product and raw_code
            else raw_code
        )
        db.execute(
            """
            INSERT INTO execution_batches (
                product_id, batch_code, batch_type, status, item_count, summary_json,
                draft_note, execution_note, review_note, executed_at, reviewed_at,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                target_product_id,
                batch_code,
                batch.get("batch_type", "general"),
                batch.get("status", "prepared"),
                batch.get("item_count", 0),
                batch.get("summary_json") or json.dumps({}, ensure_ascii=False),
                batch.get("draft_note"),
                batch.get("execution_note"),
                batch.get("review_note"),
                batch.get("executed_at"),
                batch.get("reviewed_at"),
                batch.get("created_at"),
                batch.get("updated_at"),
            ),
        )

    for version in backup_data.get("rule_versions", []):
        db.execute(
            """
            INSERT INTO rule_versions (
                product_id, version, rules_snapshot, description, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                target_product_id,
                version.get("version"),
                version.get("rules_snapshot"),
                version.get("description"),
                version.get("created_at"),
            ),
        )

    for profile in backup_data.get("strategy_profiles", []):
        profile_name = str(profile.get("name") or "").strip()
        if not profile_name:
            continue
        existing = db.get_strategy_profile(name=profile_name)
        if existing is not None:
            profile_name = f"{profile_name}（恢复）"
        db.execute(
            """
            INSERT INTO strategy_profiles (
                name, lifecycle, goal, config_snapshot, notes, source_product_id,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_name,
                profile.get("lifecycle"),
                profile.get("goal"),
                profile.get("config_snapshot"),
                profile.get("notes"),
                target_product_id,
                profile.get("created_at"),
                profile.get("updated_at"),
            ),
        )

    db.commit()
    return target_product_id


def get_default_config() -> dict:
    """获取默认配置"""
    return {
        # 产品阶段
        "is_new_product": False,
        # 原有阈值
        "high_spend_threshold": 10.0,
        "low_ctr_threshold": 0.001,
        "min_clicks_threshold": 10,
        "high_acos_threshold": 0.5,
        "min_orders_for_manual": 2,
        "target_acos": 0.25,
        "min_conversion_rate": 0.05,
        "competitor_high_acos": 0.4,
        # 新增阈值
        "thresholds": {
            "min_clicks_for_analysis": 20,
            "min_clicks_for_asin_neg": 6,
            "high_spend_no_order": 20.0,
            "good_cvr": 0.10,
            "bad_cvr": 0.05,
        },
        # 关键词库
        "keyword_libraries": {
            "irrelevant_keywords": [],
            "weak_category_keywords": [],
            "generic_keywords": [],
            "car_keywords": [],
        },
        # 核心配置
        "core_keywords": [],
        "related_keywords": [],
        "own_asins": [],
        "own_variants": [],
        "competitor_asins": [],
    }


def save_config_version(db, product_id: int, old_config: dict, new_config: dict):
    """保存配置版本"""
    try:
        # 获取下一个版本号
        cursor = db.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM rule_versions WHERE product_id = ?",
            (product_id,),
        )
        next_version = cursor.fetchone()[0]

        # 使用正确的列名（匹配 models.py 中的 schema）
        # rules_snapshot 存储新配置，description 存储变更说明
        db.execute(
            """
            INSERT INTO rule_versions (product_id, version, rules_snapshot, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                product_id,
                next_version,
                json.dumps(new_config),
                f"配置更新 (旧配置: {json.dumps(old_config, ensure_ascii=False)[:200]}...)",
            ),
        )
        db.commit()
    except Exception as e:
        logger.warning(f"保存配置版本失败: {e}")
        # 不阻止主流程
