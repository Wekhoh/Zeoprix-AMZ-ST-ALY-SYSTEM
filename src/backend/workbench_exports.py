"""Workbench 导出模块 — Sprint D.2 抽出。

把 CSV/XLSX 导出逻辑从 workbench_payload.py 剥离，便于独立维护和测试。
helper（_get_app_database_path / _resolve_product）仍 reused from
workbench_payload 以避免重复（两个 helper 体量小，单独抽 helpers 模块是
后续 sprint 的事）。
"""

from __future__ import annotations

from src.backend.workbench_payload import _get_app_database_path, _resolve_product
from src.data.db import Database


def build_amazon_bulk_csv_export(
    product_id: int | None,
) -> tuple[bytes, str] | None:
    """Sprint D.2 — 当前产品所有 negative 推荐 → Amazon Bulk Operations CSV bytes。

    返回 (csv_bytes, file_name) 或 None（无 negative 时）。
    Endpoint 直接 Response(content=bytes, media_type="text/csv") 让浏览器下载。
    """
    from src.export.exporter import ReportExporter
    from src.rules.engine import AnalysisResult

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        product = _resolve_product(db, product_id)
        product_id = int(product["id"])
        df = db.get_analysis_results({"product_id": product_id})
        if df.empty:
            return None

        # DataFrame → list[AnalysisResult]
        # campaign_name 不是 dataclass 字段，按 exporter 测试 fixture 的做法
        # 在实例化之后用动态属性赋值（dataclass 默认无 slots，允许扩展属性）。
        results: list[AnalysisResult] = []
        for _, row in df.iterrows():
            ar = AnalysisResult(
                term=str(row.get("term") or ""),
                term_type=str(row.get("term_type") or "keyword"),
                triggered_rule=str(row.get("triggered_rule") or ""),
                suggested_action=str(row.get("suggested_action") or ""),
                action_type=str(row.get("action_type") or ""),
                confidence=float(row.get("confidence") or 0.0),
                data={},
            )
            ar.campaign_name = str(row.get("campaign_name") or "")
            results.append(ar)

        exporter = ReportExporter()
        return exporter.export_amazon_bulk_csv_bytes(
            results, product_name=str(product.get("name") or "")
        )
