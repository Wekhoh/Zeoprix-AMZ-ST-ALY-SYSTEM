"""
系统设置 - 关键词库与数据管理
从 settings.py 拆分
"""

import json

import streamlit as st

from src.config.logger import get_logger
from src.ui.utils import safe_error

logger = get_logger(__name__)


def _fetch_rows(db, sql: str, params: tuple = ()) -> list[dict]:
    """以 dict 列表形式读取查询结果。"""
    cursor = db.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]


def clear_product_runtime_data(db, product_id: int) -> None:
    """清空产品运行数据，保留产品配置与规则配置。"""
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
    db.execute("DELETE FROM campaigns WHERE product_id = ?", (product_id,))
    db.commit()


def _delete_product_backup_records(db, product_id: int) -> None:
    """删除产品级备份/版本数据，供完整恢复覆盖当前产品时使用。"""
    db.execute("DELETE FROM rule_versions WHERE product_id = ?", (product_id,))
    db.execute("DELETE FROM strategy_profiles WHERE source_product_id = ?", (product_id,))
    db.commit()


def _build_keyword_library_summary(config: dict | None) -> dict[str, str | list[str]]:
    """构建关键词库页的摘要信息。"""
    config = config or {}
    keyword_libraries = config.get("keyword_libraries", {})
    irrelevant_keywords = keyword_libraries.get("irrelevant_keywords", [])
    weak_category_keywords = keyword_libraries.get("weak_category_keywords", [])
    generic_keywords = keyword_libraries.get("generic_keywords", [])
    car_keywords = keyword_libraries.get("car_keywords", [])
    own_variants = config.get("own_variants", [])

    total_keywords = (
        len(irrelevant_keywords)
        + len(weak_category_keywords)
        + len(generic_keywords)
        + len(car_keywords)
    )

    return {
        "title": "关键词库配置",
        "description": "把搜索词识别里最稳定的人工经验沉淀成词库：先分相关性，再补自家变体，减少每次都从头判断。",
        "chips": [
            f"词库总词数 {total_keywords}",
            f"不相关词 {len(irrelevant_keywords)}",
            f"弱相关词 {len(weak_category_keywords)}",
            f"自家变体 {len(own_variants)}",
        ],
    }


def _build_data_management_summary(
    term_count: int,
    result_count: int,
    campaign_count: int,
) -> dict[str, str | list[str]]:
    """构建数据管理页的摘要信息。"""
    return {
        "title": "数据管理",
        "description": "这里处理的是重跑、清空、导入导出和备份。先看数据规模，再决定是重算、导出还是危险操作。",
        "chips": [
            f"搜索词 {term_count}",
            f"分析结果 {result_count}",
            f"广告活动 {campaign_count}",
        ],
    }


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
    import datetime

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
        },
    }


def restore_full_backup(
    db,
    backup_data: dict,
    *,
    current_product_id: int | None = None,
    restore_as_new_product: bool = False,
) -> int:
    """从完整备份恢复产品数据，支持覆盖当前产品或恢复为新产品副本。"""
    if backup_data.get("export_type") != "full_backup":
        raise ValueError("当前文件不是完整数据备份。")

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
        new_campaign_id = campaign_id_map.get(int(old_campaign_id)) if old_campaign_id is not None else None
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


def render_keyword_library_settings(db, product_id: int):
    """渲染关键词库配置"""
    if not product_id:
        st.warning("请先选择产品")
        return

    # 获取产品配置
    product = db.get_product(product_id)
    config = product.get("config", {}) if product else {}
    keyword_libraries = config.get("keyword_libraries", {})
    summary = _build_keyword_library_summary(config)

    st.write(f"### {summary['title']}")
    st.caption(summary["description"])
    chip_cols = st.columns(len(summary["chips"]))
    for col, chip in zip(chip_cols, summary["chips"], strict=False):
        with col:
            st.info(chip)

    # 不相关词库
    irrelevant_keywords = keyword_libraries.get("irrelevant_keywords", [])
    with st.container(border=True):
        st.write("#### 不相关词库")
        st.caption("这类词会被判成明显不相关，适合沉淀那些你已经拍过板的硬否词经验。")
        irrelevant_text = st.text_area(
            "明显不相关的词（每行一个）",
            value="\n".join(irrelevant_keywords) if irrelevant_keywords else "",
            height=100,
            placeholder="massage\nbrace\nheating pad",
            key="irrelevant_keywords",
            help="包含这些词的搜索词会被判定为不相关，建议否定精准",
        )

    # 弱相关类目词库
    weak_category_keywords = keyword_libraries.get("weak_category_keywords", [])
    with st.container(border=True):
        st.write("#### 弱相关类目词库")
        st.caption("这些词和类目沾边，但通常会带来不够精准的流量，适合按词组层面控制。")
        weak_text = st.text_area(
            "弱相关的类目词（每行一个）",
            value="\n".join(weak_category_keywords) if weak_category_keywords else "",
            height=100,
            placeholder="massager\nblanket\nstuffable",
            key="weak_category_keywords",
            help="包含这些词的搜索词会被判定为弱相关，建议否定词组",
        )

    # 太泛的词库
    generic_keywords = keyword_libraries.get("generic_keywords", [])
    with st.container(border=True):
        st.write("#### 太泛的词库")
        st.caption("这里收的是过于宽泛、容易误伤预算的核心泛词，建议保持为完全匹配视角。")
        generic_text = st.text_area(
            "太泛泛的词（每行一个，完全匹配）",
            value="\n".join(generic_keywords) if generic_keywords else "",
            height=100,
            placeholder="pillow\npillows\nneck\nhome",
            key="generic_keywords",
            help="完全匹配这些词会被判定为太泛，建议否定精准（避免误伤长尾词）",
        )

    # 汽车相关词库
    car_keywords = keyword_libraries.get("car_keywords", [])
    with st.container(border=True):
        st.write("#### 汽车相关词库")
        st.caption("这是特殊处理区，适合放那些你明确不想让靠“车载/汽车”方向跑偏的词。")
        car_text = st.text_area(
            "汽车相关词（每行一个）",
            value="\n".join(car_keywords) if car_keywords else "",
            height=80,
            placeholder="car\nvehicle\nautomotive",
            key="car_keywords",
            help="包含这些词的搜索词会被判定为汽车相关，建议否定精准",
        )

    # 自家变体ASIN
    own_variants = config.get("own_variants", [])
    with st.container(border=True):
        st.write("#### 自家变体ASIN")
        st.caption("把自家变体沉淀在这里，系统才知道哪些 ASIN 值得互相防守，而不是误判成普通竞品。")
        variants_text = st.text_area(
            "自家变体ASIN列表（每行一个）",
            value="\n".join(own_variants) if own_variants else "",
            height=80,
            placeholder="B0XXXXXXXX\nB0YYYYYYYY",
            key="own_variants",
            help="自家变体ASIN会被推荐手动商品定位（互相防御）",
        )

    st.divider()

    # 保存按钮
    if st.button(
        "保存关键词库", type="primary", width="stretch", key="save_keyword_lib"
    ):
        try:
            # 解析输入
            new_irrelevant = [
                k.strip() for k in irrelevant_text.split("\n") if k.strip()
            ]
            new_weak = [k.strip() for k in weak_text.split("\n") if k.strip()]
            new_generic = [k.strip() for k in generic_text.split("\n") if k.strip()]
            new_car = [k.strip() for k in car_text.split("\n") if k.strip()]
            new_variants = [
                a.strip().upper() for a in variants_text.split("\n") if a.strip()
            ]

            # 更新配置
            new_keyword_libraries = {
                "irrelevant_keywords": new_irrelevant,
                "weak_category_keywords": new_weak,
                "generic_keywords": new_generic,
                "car_keywords": new_car,
            }

            updated_config = {
                **config,
                "keyword_libraries": new_keyword_libraries,
                "own_variants": new_variants,
            }

            # 保存版本历史
            save_config_version(db, product_id, config, updated_config)

            # 更新产品配置
            db.update_product_config(product_id, updated_config)
            st.success(
                f"关键词库已保存！共 {len(new_irrelevant) + len(new_weak) + len(new_generic) + len(new_car)} 个词，{len(new_variants)} 个变体ASIN"
            )
            st.rerun()
        except Exception as e:
            safe_error("关键词库保存", e)

    # 统计信息
    st.write("#### 当前配置统计")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("不相关词", len(irrelevant_keywords))
    with col2:
        st.metric("弱相关词", len(weak_category_keywords))
    with col3:
        st.metric("太泛的词", len(generic_keywords))
    with col4:
        st.metric("汽车相关", len(car_keywords))


def render_data_management(db, product_id: int):
    """渲染数据管理"""
    if not product_id:
        st.warning("请先选择产品")
        return

    try:
        # 搜索词数量 - search_terms 没有 product_id，需要通过 campaigns 关联
        cursor = db.execute(
            """
            SELECT COUNT(*) as count FROM search_terms st
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ?
            """,
            (product_id,),
        )
        term_count = cursor.fetchone()["count"]

        # 分析结果数量 - analysis_results 没有 product_id，需要通过 search_terms→campaigns 关联
        cursor = db.execute(
            """
            SELECT COUNT(*) as count FROM analysis_results ar
            JOIN search_terms st ON ar.search_term_id = st.id
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ?
            """,
            (product_id,),
        )
        result_count = cursor.fetchone()["count"]

        # 广告活动数量
        cursor = db.execute(
            "SELECT COUNT(*) as count FROM campaigns WHERE product_id = ?",
            (product_id,),
        )
        campaign_count = cursor.fetchone()["count"]
        summary = _build_data_management_summary(term_count, result_count, campaign_count)

        st.write(f"### {summary['title']}")
        st.caption(summary["description"])
        chip_cols = st.columns(len(summary["chips"]))
        for col, chip in zip(chip_cols, summary["chips"], strict=False):
            with col:
                st.info(chip)

        # 数据统计
        with st.container(border=True):
            st.write("#### 数据统计")
            st.caption("先确认当前产品的数据规模，再决定是重跑、导出还是清空。")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("搜索词记录", term_count)

            with col2:
                st.metric("分析结果", result_count)

            with col3:
                st.metric("广告活动", campaign_count)

    except Exception as e:
        logger.error(f"获取数据统计失败: {e}")
        st.error("无法获取数据统计")
        return

    st.divider()

    # 数据操作
    with st.container(border=True):
        st.write("#### 数据操作")
        st.caption("这一区处理的是“重算”与“清结果”，适合在你更新规则或刚导入新判定表之后使用。")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("重新运行分析", width="stretch"):
                with st.spinner("正在分析..."):
                    try:
                        from src.ui.pages.upload import (
                            _render_analysis_run_feedback,
                            run_analysis,
                        )

                        # 清除旧结果 - 通过 search_term_id 关联删除
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
                        db.commit()

                        analysis_state = run_analysis(db, product_id)
                        _render_analysis_run_feedback(analysis_state)
                    except Exception as e:
                        safe_error("数据分析", e)

        with col2:
            if st.button("清除分析结果", width="stretch"):
                try:
                    # 通过 search_term_id 关联删除，同时移除运行快照，避免页面继续读取旧分析残留
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
                    db.commit()
                    st.success("分析结果与最近一次分析快照已清除")
                except Exception as e:
                    safe_error("分析结果清除", e)

    st.divider()

    # 清空所有数据（保留产品配置）
    with st.container(border=True):
        st.write("#### 清空数据（保留产品）")
        st.caption("适合切换类目或重新开始一轮分析时使用：删掉运行数据，但保留产品配置。")
        st.info(
            "清空该产品的所有搜索词和分析数据，但保留产品配置。适合上传新类目数据时使用。"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("清空所有搜索词数据", width="stretch", type="secondary"):
                try:
                    clear_product_runtime_data(db, product_id)
                    st.success(
                        "所有搜索词、分析结果、审核记录与分析快照已清空，产品配置已保留。您现在可以上传新数据。"
                    )
                    st.rerun()
                except Exception as e:
                    safe_error("数据清空", e)

        with col2:
            st.caption(
                "此操作会删除：搜索词记录、广告活动、分析结果、操作计划、相关性审核记录、分析快照"
            )
            st.caption("保留：产品名称、ASIN、规则配置")

    st.divider()

    # 数据导出
    with st.container(border=True):
        st.write("#### 数据导出与规则导入")
        st.caption("先导出当前配置和备份，再导入历史规则，避免一边回滚一边心里没底。")

        col1, col2 = st.columns(2)

        with col1:
            try:
                rule_payload = build_rule_config_export_payload(db, product_id)
                if rule_payload:
                    st.download_button(
                        "导出规则配置",
                        data=rule_payload["data"],
                        file_name=rule_payload["file_name"],
                        mime=rule_payload["mime"],
                        width="stretch",
                    )
                else:
                    st.button("导出规则配置", disabled=True, width="stretch")
            except Exception as e:
                safe_error("规则导出", e)

        with col2:
            try:
                backup_payload = build_full_backup_export_payload(db, product_id)
                if backup_payload:
                    st.download_button(
                        "导出完整数据备份",
                        data=backup_payload["data"],
                        file_name=backup_payload["file_name"],
                        mime=backup_payload["mime"],
                        width="stretch",
                    )
                    st.caption(
                        f"备份内容：{backup_payload['summary']['search_terms_count']} 条搜索词，"
                        f"{backup_payload['summary']['analysis_results_count']} 条分析结果，"
                        f"{backup_payload['summary']['manual_reviews_count']} 条审核记录，"
                        f"{backup_payload['summary']['snapshots_count']} 个分析快照"
                    )
                else:
                    st.button("导出完整数据备份", disabled=True, width="stretch")
            except Exception as e:
                safe_error("数据备份", e)

        # 规则导入
        uploaded_config = st.file_uploader(
            "导入规则配置",
            type=["json"],
            help="上传之前导出的规则配置JSON文件",
            key="import_rules",
        )

        if uploaded_config:
            try:
                import_data = json.load(uploaded_config)
                if import_data.get("export_type") == "rule_config":
                    config_to_import = import_data.get("config", {})
                    st.json(config_to_import)

                    if st.button("确认导入此规则配置", type="primary"):
                        db.update_product_config(product_id, config_to_import)
                        st.success("规则配置已导入")
                        st.rerun()
                else:
                    st.warning("文件格式不正确，请选择规则配置文件")
            except Exception as e:
                safe_error("规则导入", e)

        uploaded_backup = st.file_uploader(
            "导入完整数据备份",
            type=["json"],
            help="上传之前导出的完整备份 JSON，可覆盖当前产品或恢复为新产品副本。",
            key="import_full_backup",
        )

        if uploaded_backup:
            try:
                backup_data = json.load(uploaded_backup)
                if backup_data.get("export_type") == "full_backup":
                    restore_as_new = st.checkbox(
                        "恢复为新产品副本（推荐保留当前产品时使用）",
                        value=False,
                        key="restore_full_backup_as_new",
                    )
                    backup_product = backup_data.get("product") or {}
                    summary = {
                        "search_terms_count": len(backup_data.get("search_terms", [])),
                        "analysis_results_count": len(backup_data.get("analysis_results", [])),
                        "manual_reviews_count": len(backup_data.get("manual_reviews", [])),
                        "snapshots_count": len(backup_data.get("analysis_run_snapshots", [])),
                    }
                    st.caption(
                        f"备份产品：{backup_product.get('name', '未命名产品')} ｜ "
                        f"搜索词 {summary['search_terms_count']} 条 ｜ "
                        f"分析结果 {summary['analysis_results_count']} 条 ｜ "
                        f"审核记录 {summary['manual_reviews_count']} 条 ｜ "
                        f"分析快照 {summary['snapshots_count']} 个"
                    )
                    if st.button("确认恢复完整备份", type="primary", key="confirm_restore_full_backup"):
                        restored_product_id = restore_full_backup(
                            db,
                            backup_data,
                            current_product_id=product_id,
                            restore_as_new_product=restore_as_new,
                        )
                        if restore_as_new:
                            st.session_state.current_product_id = restored_product_id
                            st.success("完整备份已恢复为新的产品副本。")
                        else:
                            st.success("完整备份已覆盖恢复到当前产品。")
                        st.rerun()
                else:
                    st.warning("文件格式不正确，请选择完整数据备份 JSON。")
            except Exception as e:
                safe_error("完整备份恢复", e)

    st.divider()

    # 危险操作
    st.write("#### 危险操作")

    with st.expander("删除产品数据", expanded=False):
        st.warning(
            "此操作将删除该产品的所有数据，包括搜索词、分析结果等。此操作不可恢复！"
        )

        confirm_text = st.text_input(
            "输入产品名称确认删除",
            placeholder="输入产品名称...",
        )

        product = db.get_product(product_id)
        product_name = product.get("name", "") if product else ""

        if st.button("永久删除", type="secondary"):
            if confirm_text == product_name:
                try:
                    # 删除相关数据 - 注意顺序：先删子表，再删父表
                    # 1. 先删 analysis_results（通过 search_term_id 关联）
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
                    # 2. 删 search_terms（通过 campaign_id 关联）
                    db.execute(
                        """
                        DELETE FROM search_terms
                        WHERE campaign_id IN (
                            SELECT id FROM campaigns WHERE product_id = ?
                        )
                        """,
                        (product_id,),
                    )
                    # 3. 删 action_plans（通过 analysis_results -> search_terms -> campaigns 关联）
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
                    # 4. 删 campaigns（有 product_id）
                    db.execute(
                        "DELETE FROM campaigns WHERE product_id = ?", (product_id,)
                    )
                    # 5. 最后删 products
                    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
                    db.commit()

                    st.session_state.current_product_id = None
                    st.success("产品已删除")
                    st.rerun()
                except Exception as e:
                    safe_error("产品删除", e)
            else:
                st.error("产品名称不匹配，请重新输入")


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


def render_config_history(db, product_id: int):
    """渲染配置历史"""
    try:
        cursor = db.execute(
            """
            SELECT id, version, rules_snapshot, description, created_at
            FROM rule_versions
            WHERE product_id = ?
            ORDER BY version DESC
            LIMIT 10
            """,
            (product_id,),
        )
        versions = cursor.fetchall()

        if not versions:
            st.info("暂无版本历史")
            return

        for version in versions:
            with st.container():
                st.write(f"**版本 {version['version']}** - {version['created_at']}")

                # 显示配置快照
                st.write("配置内容:")
                config_data = (
                    json.loads(version["rules_snapshot"])
                    if version["rules_snapshot"]
                    else {}
                )
                st.json(config_data)

                # 显示变更说明
                if version["description"]:
                    st.caption(f"说明: {version['description']}")

                if st.button("回滚到此版本", key=f"rollback_{version['id']}"):
                    try:
                        config_to_restore = (
                            json.loads(version["rules_snapshot"])
                            if version["rules_snapshot"]
                            else {}
                        )
                        db.update_product_config(product_id, config_to_restore)
                        st.success("已回滚")
                        st.rerun()
                    except Exception as e:
                        safe_error("配置回滚", e)

                st.divider()

    except Exception as e:
        logger.error(f"获取配置历史失败: {e}")
        st.info("暂无版本历史")


def export_full_backup(db, product_id: int):
    """导出产品完整数据备份"""
    payload = build_full_backup_export_payload(db, product_id)
    if not payload:
        st.error("产品不存在")
        return

    st.download_button(
        "下载完整备份JSON",
        data=payload["data"],
        file_name=payload["file_name"],
        mime=payload["mime"],
    )
    st.success(
        f"备份已准备就绪：{payload['summary']['search_terms_count']} 条搜索词，"
        f"{payload['summary']['analysis_results_count']} 条分析结果"
    )
