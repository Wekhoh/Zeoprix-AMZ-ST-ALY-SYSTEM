"""Workbench page payload 模块 — Step 3 H3c 抽出。

把 7 个 read-side build_*_page_payload + 4 个 page-only helper 从
workbench_payload.py 剥离：

  - build_upload_page_payload
  - build_term_detail_payload
  - build_review_page_payload
  - build_settings_page_payload
  - build_actions_page_payload
  - build_competitors_payload
  - build_analysis_page_payload

Page-only helper:
  - _cluster_pending_terms          (review 用)
  - _fetch_historical_decisions     (review + term_detail 用)
  - _build_weekly_compare           (actions 用 / Sprint B.3)
  - _snapshot_daily_pacing          (actions 用 / Sprint B.4 写库 helper)

build_workbench_payload (hub) 仍保留在 workbench_payload.py，因为它聚合了
许多内部辅助 helper；page payload 通过 import 调用它形成上层 → 下层的
依赖方向。

外部调用方（app.py / tests）通过 workbench_payload 末尾的 re-export 不感知。
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Any

from src.backend.workbench_payload import (
    _analysis_result_count,
    _campaign_count,
    _format_timestamp,
    _get_app_database_path,
    _get_dashboard_stats,
    _get_pending_stats,
    _manual_review_count,
    _resolve_product,
    build_workbench_payload,
)
from src.config.logger import get_logger
from src.data.db import Database

logger = get_logger(__name__)


def build_upload_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        stats = _get_dashboard_stats(db, product_id)
        snapshots = db.list_analysis_run_snapshots(product_id, limit=5)
        campaigns = [
            dict(row)
            for row in db.execute(
                "SELECT id, name, created_at FROM campaigns WHERE product_id = ? ORDER BY created_at DESC LIMIT 5",
                (product_id,),
            ).fetchall()
        ]
        return {
            **workbench,
            "upload": {
                "latestReportDate": stats.get("latest_report_date") or "暂无导入",
                "searchTerms": stats["term_count"],
                "campaigns": _campaign_count(db, product_id),
                "snapshotCount": len(
                    db.list_analysis_run_snapshots(product_id, limit=200)
                ),
                "recentSnapshots": [
                    {
                        "id": s["id"],
                        "createdAt": _format_timestamp(s["created_at"]),
                        "itemCount": int(
                            (s.get("summary") or {}).get("item_count")
                            or len(s.get("rows") or [])
                        ),
                    }
                    for s in snapshots
                ],
                "recentCampaigns": [
                    {
                        "id": c["id"],
                        "name": c["name"],
                        "createdAt": _format_timestamp(c["created_at"]),
                    }
                    for c in campaigns
                ],
            },
        }


def _cluster_pending_terms(
    items: list[dict[str, Any]], similarity_threshold: float = 0.7
) -> dict[str, int]:
    """Sprint A.1 — 用 SequenceMatcher.ratio() 给待审 terms 做轻量聚类。

    返回 `{term: cluster_id}` 映射；ratio >= threshold 归一类。
    cluster_id 从 0 开始递增；single-item 簇也分配 id 便于前端统一渲染。
    无外部依赖；O(N²) 但 N≤8（pending limit）成本可忽略。
    """
    from difflib import SequenceMatcher

    terms: list[str] = [
        str(it.get("term") or "").strip().lower() for it in items if it.get("term")
    ]
    cluster_of: dict[str, int] = {}
    next_id = 0
    for term in terms:
        if term in cluster_of:
            continue
        cluster_of[term] = next_id
        for other in terms:
            if other in cluster_of or other == term:
                continue
            if SequenceMatcher(None, term, other).ratio() >= similarity_threshold:
                cluster_of[other] = next_id
        next_id += 1
    return cluster_of


def _fetch_historical_decisions(
    db: "Database", product_id: int, term: str, *, limit: int = 5
) -> list[dict[str, Any]]:
    """Sprint A.1 — 按 term 拉历史决策给前端提示"32 天前已否定过"等。

    复用 `db.get_manual_reviews_by_term()`；按 decidedAt desc，最多 limit 条。
    跳过 status=pending 的（仅返回真正已决策的）。
    """
    if not term:
        return []
    rows = db.get_manual_reviews_by_term(product_id, term) or []
    history = []
    for row in rows:
        relevance = row.get("relevance")
        if not relevance or relevance == "pending":
            continue
        history.append(
            {
                "decidedAt": _format_timestamp(
                    row.get("updated_at") or row.get("created_at")
                ),
                "decision": relevance,
                "scope": row.get("scope") or "local",
                "campaignId": row.get("campaign_id"),
                "notes": (row.get("relevance_notes") or row.get("notes") or "")[:140],
            }
        )
    history.sort(key=lambda r: r.get("decidedAt") or "", reverse=True)
    return history[:limit]


def build_term_detail_payload(
    product_id: int | None, term: str, *, days: int = 30
) -> dict[str, Any]:
    """Sprint A.2 — 单 term 30 天详情，给前端详情抽屉用。

    返回：
      - term / termType / firstSeen / lastSeen
      - dailySeries: [{date, spend, clicks, orders, sales}]（最近 N 天）
      - aggregates: 30d 总和（spend/clicks/orders/sales/cvr/acos）
      - appliedRules: 该 term 历次匹配的规则（unique by rule name）
      - historicalDecisions: 复用 _fetch_historical_decisions
      - currentRelevance: 最新一次的 relevance（pending 表示未审）
    """
    if not term:
        raise ValueError("term 不能为空")

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])

        # 1) 拉所有 search_term 行 + analysis_result 关联
        cursor = db.execute(
            """
            SELECT st.term, st.term_type, st.spend, st.clicks, st.orders, st.sales,
                   st.report_date, st.created_at, ar.triggered_rule, ar.action_type,
                   ar.confidence
              FROM search_terms st
              LEFT JOIN analysis_results ar ON ar.search_term_id = st.id
              JOIN campaigns c ON st.campaign_id = c.id
             WHERE c.product_id = ? AND st.term = ?
             ORDER BY COALESCE(st.report_date, st.created_at) DESC
             LIMIT 200
            """,
            (product_id, term),
        )
        rows = [dict(r) for r in cursor.fetchall()]

        if not rows:
            return {
                "term": term,
                "termType": "keyword",
                "found": False,
                "message": "该词在最近数据中未出现",
            }

        # 2) Daily 聚合（按 report_date 分组）
        from collections import defaultdict

        daily: dict[str, dict[str, float]] = defaultdict(
            lambda: {"spend": 0.0, "clicks": 0.0, "orders": 0.0, "sales": 0.0}
        )
        applied_rules: dict[str, int] = {}
        agg_total = {"spend": 0.0, "clicks": 0.0, "orders": 0.0, "sales": 0.0}
        for row in rows:
            day = (row.get("report_date") or row.get("created_at") or "")[:10]
            if not day:
                continue
            for k in ("spend", "clicks", "orders", "sales"):
                v = float(row.get(k) or 0.0)
                daily[day][k] += v
                agg_total[k] += v
            rule = row.get("triggered_rule")
            if rule:
                applied_rules[rule] = applied_rules.get(rule, 0) + 1

        # 截取最近 N 天
        sorted_days = sorted(daily.keys(), reverse=True)[:days]
        daily_series = [
            {"date": d, **{k: round(daily[d][k], 2) for k in daily[d]}}
            for d in sorted(sorted_days)
        ]

        cvr = (
            (agg_total["orders"] / agg_total["clicks"])
            if agg_total["clicks"] > 0
            else 0.0
        )
        acos = (
            (agg_total["spend"] / agg_total["sales"]) if agg_total["sales"] > 0 else 0.0
        )

        # 3) 历史决策（复用 helper）
        history = _fetch_historical_decisions(db, product_id, term, limit=10)
        current_relevance = history[0]["decision"] if history else "pending"

        first_seen = sorted(daily.keys())[0] if daily else None
        last_seen = sorted(daily.keys(), reverse=True)[0] if daily else None

        return {
            "term": term,
            "termType": rows[0].get("term_type") or "keyword",
            "found": True,
            "firstSeen": first_seen,
            "lastSeen": last_seen,
            "currentRelevance": current_relevance,
            "dailySeries": daily_series,
            "aggregates": {
                "spend": round(agg_total["spend"], 2),
                "clicks": int(agg_total["clicks"]),
                "orders": int(agg_total["orders"]),
                "sales": round(agg_total["sales"], 2),
                "cvr": round(cvr, 4),
                "acos": round(acos, 4),
                "rowCount": len(rows),
            },
            "appliedRules": [
                {"rule": k, "hits": v}
                for k, v in sorted(applied_rules.items(), key=lambda kv: -kv[1])
            ],
            "historicalDecisions": history,
        }


def build_review_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        review_stats = db.get_review_stats(product_id)
        pending_items = db.get_pending_reviews_list(product_id, limit=8)
        # Sprint A.1: 加 cluster_id（相似词聚簇）+ historicalDecisions（同 term 历史拍板）
        cluster_map = _cluster_pending_terms(pending_items)
        return {
            **workbench,
            "review": {
                "stats": review_stats,
                "pendingItems": [
                    {
                        "term": item.get("term"),
                        "termType": item.get("term_type", "keyword"),
                        "campaignName": item.get("campaign_name") or "全局",
                        "campaignId": item.get("campaign_id"),
                        "relevance": item.get("relevance") or "pending",
                        "createdAt": _format_timestamp(item.get("created_at")),
                        "clusterId": cluster_map.get(
                            str(item.get("term") or "").strip().lower(), -1
                        ),
                        "historicalDecisions": _fetch_historical_decisions(
                            db, product_id, str(item.get("term") or "")
                        ),
                    }
                    for item in pending_items
                ],
            },
        }


def build_settings_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        product_config = product.get("config") or {}
        keyword_libraries = product_config.get("keyword_libraries") or {}
        backup_summary = {
            "searchTerms": _get_dashboard_stats(db, product_id)["term_count"],
            "analysisResults": _analysis_result_count(db, product_id),
            "manualReviews": _manual_review_count(db, product_id),
            "snapshots": len(db.list_analysis_run_snapshots(product_id, limit=200)),
            "executionBatches": len(db.list_execution_batches(product_id, limit=200)),
        }
        return {
            **workbench,
            "settings": {
                "ruleVersionCount": len(db.get_rule_versions(product_id)),
                "strategyProfileCount": len(db.list_strategy_profiles()),
                "keywordLibraryCounts": {
                    "irrelevant": len(keyword_libraries.get("irrelevant_keywords", [])),
                    "weak": len(keyword_libraries.get("weak_category_keywords", [])),
                    "generic": len(keyword_libraries.get("generic_keywords", [])),
                    "car": len(keyword_libraries.get("car_keywords", [])),
                    "variants": len(product_config.get("own_variants", [])),
                },
                "backupSummary": backup_summary,
                "configEditor": {
                    "coreKeywords": product_config.get("core_keywords", []),
                    "relatedKeywords": product_config.get("related_keywords", []),
                    "competitorAsins": product_config.get("competitor_asins", []),
                    "ownVariants": product_config.get("own_variants", []),
                },
                "recentRuleVersions": [
                    {
                        "version": int(item.get("version") or 0),
                        "createdAt": _format_timestamp(item.get("created_at")),
                        "description": str(item.get("description") or "配置更新")[:160],
                    }
                    for item in db.get_rule_versions(product_id)[:5]
                ],
            },
        }


def _build_weekly_compare(db: Database, product_id: int) -> dict[str, Any]:
    """Sprint B.3 — 最近 14 天日序列 + 本周 vs 上周对比。

    返回 4 字段：dailySeries / thisWeek / lastWeek / delta。
    delta 是比例（-0.12 = -12%），无上周数据时返回 1.0（增长）或 0.0（持平）。

    复用现有 search_terms.report_date 字段，无需 schema migration。
    """
    rows = db.execute(
        """
        SELECT
            COALESCE(st.report_date, date(st.created_at)) AS bucket_date,
            COALESCE(SUM(st.spend), 0) AS spend,
            COALESCE(SUM(st.orders), 0) AS orders,
            COALESCE(SUM(st.sales), 0) AS sales
        FROM search_terms st
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ?
          AND COALESCE(st.report_date, date(st.created_at)) >= date('now', '-14 days')
        GROUP BY bucket_date
        ORDER BY bucket_date ASC
        """,
        (product_id,),
    ).fetchall()

    daily = [
        {
            "date": str(r["bucket_date"] or ""),
            "spend": float(r["spend"] or 0.0),
            "orders": int(r["orders"] or 0),
            "sales": float(r["sales"] or 0.0),
        }
        for r in rows
    ]

    # 本周 = 最近 7 天日期范围（calendar），上周 = 之前 7 天日期范围
    today = dt.date.today()
    this_week_start = today - dt.timedelta(days=6)  # 含今天共 7 天
    last_week_start = today - dt.timedelta(days=13)
    last_week_end = today - dt.timedelta(days=7)

    def _in_range(item: dict, start: dt.date, end: dt.date) -> bool:
        try:
            d = dt.date.fromisoformat(item["date"])
        except (ValueError, TypeError):
            return False
        return start <= d <= end

    this_week_data = [i for i in daily if _in_range(i, this_week_start, today)]
    last_week_data = [i for i in daily if _in_range(i, last_week_start, last_week_end)]

    def _sum(items: list[dict]) -> dict[str, float]:
        return {
            "spend": float(sum(i["spend"] for i in items)),
            "orders": int(sum(i["orders"] for i in items)),
            "sales": float(sum(i["sales"] for i in items)),
        }

    this_week = _sum(this_week_data)
    last_week = _sum(last_week_data)

    def _delta(a: float, b: float) -> float:
        if b == 0:
            return 1.0 if a > 0 else 0.0
        return (a - b) / b

    return {
        "dailySeries": daily,
        "thisWeek": this_week,
        "lastWeek": last_week,
        "delta": {
            "spend": _delta(this_week["spend"], last_week["spend"]),
            "orders": _delta(this_week["orders"], last_week["orders"]),
            "sales": _delta(this_week["sales"], last_week["sales"]),
        },
    }


def _snapshot_daily_pacing(db: Database, product_id: int) -> int:
    """Sprint B.4 — 每日 pacing 静默写入。

    每次访问 actions 页面时调用，按 campaign 维度聚合"今日"数据写入 daily_pacing。
    UNIQUE(product_id, snapshot_date, campaign_id) + INSERT OR REPLACE 保证幂等；
    NULL campaign_id 行（product 级聚合）通过显式 DELETE 防止 SQLite NULL!=NULL 重复。

    失败时静默吞（schema 未创建等），不阻断 actions 页面渲染。
    Returns: 写入的行数（含 campaign 级 + 1 个 product 级 NULL row）
    """
    today_iso = dt.date.today().isoformat()
    try:
        rows = db.execute(
            """
            SELECT
                st.campaign_id,
                COALESCE(SUM(st.impressions), 0) AS impressions,
                COALESCE(SUM(st.clicks), 0) AS clicks,
                COALESCE(SUM(st.spend), 0) AS spend,
                COALESCE(SUM(st.orders), 0) AS orders,
                COALESCE(SUM(st.sales), 0) AS sales
            FROM search_terms st
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ?
              AND COALESCE(st.report_date, date(st.created_at)) = ?
            GROUP BY st.campaign_id
            """,
            (product_id, today_iso),
        ).fetchall()

        written = 0
        for r in rows:
            db.execute(
                """
                INSERT OR REPLACE INTO daily_pacing
                  (product_id, snapshot_date, campaign_id, impressions, clicks, spend, orders, sales)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    today_iso,
                    int(r["campaign_id"]) if r["campaign_id"] is not None else None,
                    int(r["impressions"] or 0),
                    int(r["clicks"] or 0),
                    float(r["spend"] or 0.0),
                    int(r["orders"] or 0),
                    float(r["sales"] or 0.0),
                ),
            )
            written += 1

        if rows:
            db.execute(
                "DELETE FROM daily_pacing WHERE product_id = ? AND snapshot_date = ? AND campaign_id IS NULL",
                (product_id, today_iso),
            )
            db.execute(
                """
                INSERT INTO daily_pacing
                  (product_id, snapshot_date, campaign_id, impressions, clicks, spend, orders, sales)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    today_iso,
                    int(sum(int(r["impressions"] or 0) for r in rows)),
                    int(sum(int(r["clicks"] or 0) for r in rows)),
                    float(sum(float(r["spend"] or 0.0) for r in rows)),
                    int(sum(int(r["orders"] or 0) for r in rows)),
                    float(sum(float(r["sales"] or 0.0) for r in rows)),
                ),
            )
            written += 1

        db.commit()
        return written
    except sqlite3.Error as exc:
        # 写到一半失败时回滚，避免 campaign 行已写而 product 聚合行未写的脏数据
        try:
            db.conn.rollback()
        except Exception:
            pass
        logger.warning("daily_pacing snapshot 失败，已回滚: %s", exc)
        return 0


def build_actions_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        pending_stats = _get_pending_stats(db, product_id)
        weekly_compare = _build_weekly_compare(db, product_id)
        _snapshot_daily_pacing(db, product_id)  # Sprint B.4 静默写入
        return {
            **workbench,
            "actions": {
                "negativeCount": int(pending_stats.get("negative_count") or 0),
                "manualCount": int(pending_stats.get("manual_count") or 0),
                "conflictCount": int(pending_stats.get("conflict_count") or 0),
                "latestBatchCode": (workbench.get("executionBatches") or [{}])[0].get(
                    "code"
                ),
            },
            "weeklyCompare": weekly_compare,
        }


def build_competitors_payload(product_id: int | None = None) -> dict[str, Any]:
    """Sprint C.1 — 内部竞品 ASIN 监控（复用现有 asin_rules 模块）。

    数据通路：
    - 读 products.config.competitor_asins（已配置的竞品列表）
    - 读 search_terms df（本产品所有搜索词，含作为 term 的对手 ASIN）
    - 调 src.rules.asin_rules.classify_asins → 4 类（own/competitor/negative/watch）
    - 调 get_competitor_insights → top/worst performers + 总览
    - 序列化为前端友好 JSON

    不需要 schema migration（实时计算，类似 B.1/B.2 聚合视图）。
    """
    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        if not product:
            return {"source": "empty"}
        resolved_pid = int(product["id"])
        product_config = product.get("config") or {}
        configured = product_config.get("competitor_asins") or []
        configured_upper = {str(s).upper() for s in configured}

        df = db.get_search_terms({"product_id": resolved_pid})
        if df.empty:
            return {
                "source": "empty",
                "productId": resolved_pid,
                "productName": str(product.get("name") or ""),
                "configuredCompetitorAsins": list(configured),
                "discoveredCompetitors": [],
                "negativeAsinsCount": 0,
                "watchAsinsCount": 0,
                "insights": {
                    "totalCount": 0,
                    "totalSpend": 0.0,
                    "totalOrders": 0,
                    "avgAcos": 0.0,
                    "topPerformers": [],
                    "worstPerformers": [],
                },
            }

        from src.rules.asin_rules import classify_asins, get_competitor_insights

        classified = classify_asins(df, product_config)
        competitor_list = classified.get("competitor_asins", [])
        insights = get_competitor_insights(competitor_list)

        def _perf_brief(a):
            p = a.performance
            return {
                "asin": a.asin,
                "spend": float(p.get("spend") or 0.0),
                "orders": int(p.get("orders") or 0),
                "acos": float(p.get("acos") or 0.0),
            }

        return {
            "source": "live",
            "productId": resolved_pid,
            "productName": str(product.get("name") or ""),
            "configuredCompetitorAsins": list(configured),
            "discoveredCompetitors": [
                {
                    "asin": a.asin,
                    "isConfigured": a.asin in configured_upper,
                    "suggestedAction": a.suggested_action,
                    "impressions": int(a.performance.get("impressions") or 0),
                    "clicks": int(a.performance.get("clicks") or 0),
                    "spend": float(a.performance.get("spend") or 0.0),
                    "orders": int(a.performance.get("orders") or 0),
                    "sales": float(a.performance.get("sales") or 0.0),
                    "acos": float(a.performance.get("acos") or 0.0),
                }
                for a in competitor_list
            ],
            "negativeAsinsCount": len(classified.get("negative_asins", [])),
            "watchAsinsCount": len(classified.get("watch_asins", [])),
            "insights": {
                "totalCount": int(insights.get("total_count") or 0),
                "totalSpend": float(insights.get("total_spend") or 0.0),
                "totalOrders": int(insights.get("total_orders") or 0),
                "avgAcos": float(insights.get("avg_acos") or 0.0),
                "topPerformers": [
                    _perf_brief(a) for a in insights.get("top_performers", [])
                ],
                "worstPerformers": [
                    _perf_brief(a) for a in insights.get("worst_performers", [])
                ],
            },
        }


def build_analysis_page_payload(product_id: int | None = None) -> dict[str, Any]:
    workbench = build_workbench_payload(product_id)
    if workbench.get("source") != "live":
        return {"source": workbench.get("source", "empty")}

    rows = workbench.get("analysisRows") or []
    type_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    for row in rows:
        type_counts[row.get("type") or "unknown"] = (
            type_counts.get(row.get("type") or "unknown", 0) + 1
        )
        action_counts[row.get("action") or "unknown"] = (
            action_counts.get(row.get("action") or "unknown", 0) + 1
        )

    # Sprint B.1 / B.2 — Campaign + ASIN 聚合视图
    campaign_rows: list[dict[str, Any]] = []
    asin_rows: list[dict[str, Any]] = []
    resolved_pid = workbench.get("productId")
    if resolved_pid is not None:
        from src.data.aggregator import DataAggregator

        db_path = _get_app_database_path()
        with Database(str(db_path)) as db:
            agg = DataAggregator(db)
            try:
                campaign_df = agg.aggregate_by_campaign(product_id=int(resolved_pid))
                if not campaign_df.empty:
                    campaign_rows = [
                        {
                            "campaignName": str(r.get("campaign_name") or ""),
                            "matchType": str(r.get("match_type") or ""),
                            "asin": str(r.get("product_asin") or ""),
                            "productName": str(r.get("product_name") or ""),
                            "impressions": int(r.get("total_impressions") or 0),
                            "clicks": int(r.get("total_clicks") or 0),
                            "spend": float(r.get("total_spend") or 0.0),
                            "orders": int(r.get("total_orders") or 0),
                            "sales": float(r.get("total_sales") or 0.0),
                            "termCount": int(r.get("term_count") or 0),
                            "ctr": float(r.get("ctr") or 0.0),
                            "cpc": float(r.get("cpc") or 0.0),
                            "acos": float(r.get("acos") or 0.0),
                            "roas": float(r.get("roas") or 0.0),
                            "cvr": float(r.get("conversion_rate") or 0.0),
                        }
                        for r in campaign_df.to_dict(orient="records")
                    ]
            except Exception as exc:  # noqa: BLE001 — 聚合失败不影响主 payload
                logger.warning("campaign 聚合失败，返回空列表: %s", exc, exc_info=True)
                campaign_rows = []
            try:
                asin_df = agg.aggregate_by_asin(product_id=int(resolved_pid))
                if not asin_df.empty:
                    asin_rows = [
                        {
                            "asin": str(r.get("product_asin") or ""),
                            "productName": str(r.get("product_name") or ""),
                            "impressions": int(r.get("total_impressions") or 0),
                            "clicks": int(r.get("total_clicks") or 0),
                            "spend": float(r.get("total_spend") or 0.0),
                            "orders": int(r.get("total_orders") or 0),
                            "sales": float(r.get("total_sales") or 0.0),
                            "termCount": int(r.get("term_count") or 0),
                            "campaignCount": int(r.get("campaign_count") or 0),
                            "ctr": float(r.get("ctr") or 0.0),
                            "cpc": float(r.get("cpc") or 0.0),
                            "acos": float(r.get("acos") or 0.0),
                            "roas": float(r.get("roas") or 0.0),
                            "cvr": float(r.get("conversion_rate") or 0.0),
                        }
                        for r in asin_df.to_dict(orient="records")
                    ]
            except Exception as exc:  # noqa: BLE001
                logger.warning("asin 聚合失败，返回空列表: %s", exc, exc_info=True)
                asin_rows = []

    return {
        **workbench,
        "analysis": {
            "rowCount": len(rows),
            "typeCounts": type_counts,
            "actionCounts": action_counts,
        },
        "campaignRows": campaign_rows,
        "asinRows": asin_rows,
    }
