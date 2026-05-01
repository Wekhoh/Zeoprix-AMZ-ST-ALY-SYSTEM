"""Workbench I/O mutation 模块 — Step 3 H3b 抽出。

把 analysis trigger + file upload 这 2 个 *_for_frontend 写入函数从
workbench_payload.py 剥离：

  - run_analysis_for_frontend
  - upload_files_for_frontend  (内部会调 run_analysis_for_frontend)

外部调用方（app.py）通过 workbench_payload 末尾的 re-export 不感知。
DataAggregator / RuleEngine / truth_replay 仍走函数内 lazy import，
保持 workbench_payload 的启动开销不增加。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import UploadFile

from src.backend.workbench_payload import _get_app_database_path
from src.data.db import Database
from src.data.parser import FileParser


def run_analysis_for_frontend(*, product_id: int) -> dict[str, Any]:
    from src.analysis.truth_replay import (
        apply_reviewed_truth,
        build_analysis_run_snapshot_rows,
        build_analysis_run_snapshot_summary,
    )
    from src.data.aggregator import DataAggregator
    from src.rules.engine import RuleEngine

    db_path = _get_app_database_path()
    with Database(str(db_path)) as db:
        aggregator = DataAggregator(db)
        df = aggregator.aggregate_by_term(product_id)

        if df.empty:
            return {
                "status": "warning",
                "message": "当前导入数据暂时不足以生成搜索词分析结果。",
                "termsAnalyzed": 0,
                "resultsSaved": 0,
            }

        engine = RuleEngine(db, product_id)
        results = engine.analyze(df)
        if not results:
            return {
                "status": "warning",
                "message": "规则分析已运行，但当前没有生成可保存的建议。",
                "termsAnalyzed": len(df),
                "resultsSaved": 0,
            }

        effective_results = apply_reviewed_truth(db, product_id, results)
        snapshot_rows = build_analysis_run_snapshot_rows(effective_results)
        if snapshot_rows:
            db.save_analysis_run_snapshot(
                product_id,
                snapshot_rows,
                run_source="manual",
                summary=build_analysis_run_snapshot_summary(snapshot_rows),
            )

        results_saved = 0
        pending_reviews = 0
        for result in effective_results:
            db.save_analysis_result_by_term(
                product_id=product_id,
                term=result.term,
                triggered_rule=result.triggered_rule,
                suggested_action=result.suggested_action,
                action_type=result.action_type,
                confidence=result.confidence,
                ai_reasoning=result.ai_reasoning,
            )
            results_saved += 1

        for result in effective_results:
            needs_review = getattr(result, "needs_review", False)
            relevance = getattr(result, "relevance", None)
            if needs_review or relevance in (None, "pending"):
                db.upsert_manual_review(
                    product_id=product_id,
                    term=result.term,
                    term_type=result.term_type,
                    system_action=result.suggested_action,
                    relevance="pending",
                    reviewed=False,
                )
                pending_reviews += 1

        return {
            "status": "success",
            "message": "分析完成。",
            "termsAnalyzed": len(df),
            "resultsSaved": results_saved,
            "pendingReviews": pending_reviews,
        }


def upload_files_for_frontend(
    *,
    product_id: int,
    files: list[UploadFile],
    auto_analyze: bool = True,
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    parser = FileParser()
    imported_files: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    total_rows = 0

    with Database(str(db_path)) as db:
        for upload in files:
            upload_name = upload.filename or "uploaded.csv"
            try:
                upload.file.seek(0)
                df = parser.parse(upload.file, upload_name)
            except Exception as exc:
                failures.append({"fileName": upload_name, "reason": f"解析失败：{exc}"})
                continue

            if df is None or df.empty:
                failures.append(
                    {"fileName": upload_name, "reason": "文件中没有可导入的数据。"}
                )
                continue

            campaign_name = Path(upload_name).stem
            campaign_id = db.create_campaign(
                product_id=product_id,
                name=campaign_name,
            )
            saved_count = db.save_search_terms(df, campaign_id)
            imported_files.append(
                {
                    "fileName": upload_name,
                    "campaignName": campaign_name,
                    "rows": int(saved_count),
                }
            )
            total_rows += int(saved_count)

        analysis_state: dict[str, Any] | None = None
        if auto_analyze and total_rows > 0:
            analysis_state = run_analysis_for_frontend(product_id=product_id)

        status = "success" if imported_files else "warning"
        message = "上传完成。" if imported_files else "没有任何文件成功导入。"
        return {
            "status": status,
            "message": message,
            "importedFiles": imported_files,
            "failedFiles": failures,
            "importedRows": total_rows,
            "campaignsCreated": len(imported_files),
            "analysisState": analysis_state,
        }
