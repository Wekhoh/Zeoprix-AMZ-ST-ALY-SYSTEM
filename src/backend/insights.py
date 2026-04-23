"""Sprint 4 · A3 — Daily AI Insights service layer.

Persists per-product daily insight reports in a ``daily_insights`` SQLite
table and generates fresh reports via :meth:`src.ai.analyzer.AIAnalyzer.generate_insights`.

The schema is created lazily via ``CREATE TABLE IF NOT EXISTS`` so the module
works on both fresh and existing app.db files without a formal migration.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

from src.ai.analyzer import get_ai_analyzer
from src.config.logger import get_logger
from src.data.db import Database
from src.rules.engine import analyze_search_terms_cached

logger = get_logger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS daily_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    date TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_findings TEXT NOT NULL DEFAULT '[]',
    recommendations TEXT NOT NULL DEFAULT '[]',
    statistics TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_daily_insights_product_date
    ON daily_insights(product_id, date DESC)
"""


def ensure_daily_insights_schema(db: Database) -> None:
    """Idempotently create the ``daily_insights`` table + index."""
    cursor = db.conn.cursor()
    cursor.execute(_SCHEMA_SQL)
    cursor.execute(_INDEX_SQL)
    db.conn.commit()


def _today_iso() -> str:
    return dt.date.today().isoformat()


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Normalize a ``daily_insights`` row into a JSON-safe dict."""
    return {
        "id": row["id"],
        "product_id": row["product_id"],
        "date": row["date"],
        "summary": row["summary"],
        "key_findings": json.loads(row["key_findings"] or "[]"),
        "recommendations": json.loads(row["recommendations"] or "[]"),
        "statistics": json.loads(row["statistics"] or "{}"),
        "created_at": row["created_at"],
    }


def get_today_insight(db: Database, product_id: int | None) -> dict[str, Any] | None:
    """Return today's most recent insight for ``product_id`` or ``None``."""
    ensure_daily_insights_schema(db)
    cursor = db.conn.cursor()
    cursor.execute(
        """
        SELECT id, product_id, date, summary, key_findings,
               recommendations, statistics, created_at
          FROM daily_insights
         WHERE date = ?
           AND (product_id IS ? OR product_id = ?)
         ORDER BY created_at DESC
         LIMIT 1
        """,
        (_today_iso(), product_id, product_id),
    )
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def _get_product_context(db: Database, product_id: int | None) -> dict[str, Any]:
    """Fetch minimal product metadata for insight narration."""
    if product_id is None:
        return {"name": "当前产品", "category": "未分类"}
    try:
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT name, category FROM products WHERE id = ? LIMIT 1",
            (product_id,),
        )
        row = cursor.fetchone()
    except Exception:
        row = None
    if row is None:
        return {"name": "当前产品", "category": "未分类"}
    return {
        "name": row["name"] or "当前产品",
        "category": row["category"] or "未分类",
    }


def generate_and_store_insight(db: Database, product_id: int | None) -> dict[str, Any]:
    """Run analyzer.generate_insights, store in daily_insights, return row dict.

    On AI-upstream failure the analyzer returns a fallback report; we still
    persist it so the UI has *something* to show.
    """
    ensure_daily_insights_schema(db)

    try:
        results = analyze_search_terms_cached(db, product_id) if product_id else []
    except Exception as exc:
        logger.warning(
            f"analyze_search_terms_cached failed product={product_id}: {exc}"
        )
        results = []

    product_context = _get_product_context(db, product_id)

    analyzer = get_ai_analyzer()
    try:
        report = analyzer.generate_insights(results, product_context)
    except Exception as exc:  # pragma: no cover - runtime guard
        logger.warning(
            f"generate_insights failed product={product_id}: {exc}; "
            "storing fallback report"
        )
        from src.ai.analyzer import InsightReport

        report = InsightReport(
            summary=f"AI 洞察暂时不可用：{exc}",
            statistics={"total_terms": len(results)},
        )

    now_ts = dt.datetime.now().isoformat(timespec="seconds")
    today = _today_iso()

    cursor = db.conn.cursor()
    cursor.execute(
        """
        INSERT INTO daily_insights
            (product_id, date, summary, key_findings,
             recommendations, statistics, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            today,
            report.summary or "",
            json.dumps(report.key_findings, ensure_ascii=False),
            json.dumps(report.recommendations, ensure_ascii=False),
            json.dumps(report.statistics, ensure_ascii=False),
            now_ts,
        ),
    )
    new_id = cursor.lastrowid
    db.conn.commit()

    logger.info(
        f"Stored daily insight id={new_id} product={product_id} date={today} "
        f"findings={len(report.key_findings)} recs={len(report.recommendations)}"
    )

    return {
        "id": new_id,
        "product_id": product_id,
        "date": today,
        "summary": report.summary or "",
        "key_findings": report.key_findings or [],
        "recommendations": report.recommendations or [],
        "statistics": report.statistics or {},
        "created_at": now_ts,
    }
