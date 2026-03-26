"""
文件上传页面
支持上传和解析CSV/Excel文件
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.analysis.truth_replay import (
    inspect_aggregate_truth_workbook,
    inspect_campaign_truth_workbook,
    seed_truth_workbooks,
)
from src.config.logger import get_logger
from src.data.parser import FileParser

logger = get_logger(__name__)

UPLOAD_PAGE_CSS = """
<style>
.upload-flow-shell {
    padding: 1.2rem 1.35rem;
    border-radius: 22px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(248,250,252,0.92) 100%);
    box-shadow: 0 16px 38px rgba(15, 23, 42, 0.05);
    margin-bottom: 1.35rem;
}
.upload-flow-shell h1 {
    margin: 0.85rem 0 0.3rem 0 !important;
}
.upload-flow-shell p {
    margin: 0;
    color: #64748B;
    font-size: 0.96rem;
    line-height: 1.6;
}
.upload-flow-badge {
    display: inline-flex;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
    background: rgba(37, 99, 235, 0.08);
    color: #2563EB;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.upload-flow-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: 1rem;
}
.upload-flow-chip {
    padding: 0.58rem 0.82rem;
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    background: rgba(255,255,255,0.88);
    color: #334155;
    font-size: 0.84rem;
    font-weight: 600;
}
.upload-section-note {
    margin: 0.2rem 0 1rem 0;
    color: #64748B;
    font-size: 0.94rem;
    line-height: 1.55;
}
.upload-status-card {
    padding: 0.9rem 1rem;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: rgba(255,255,255,0.88);
    margin-bottom: 1rem;
}
.upload-status-card strong {
    display: block;
    color: #0F172A;
    font-size: 1rem;
    margin-bottom: 0.25rem;
}
.upload-status-card span {
    color: #64748B;
    font-size: 0.9rem;
    line-height: 1.5;
}
.upload-status-card--warning {
    background: linear-gradient(180deg, rgba(255,251,235,0.92) 0%, rgba(255,247,214,0.95) 100%);
    border-color: rgba(245, 158, 11, 0.18);
}
.upload-status-card--success {
    background: linear-gradient(180deg, rgba(236,253,245,0.92) 0%, rgba(220,252,231,0.95) 100%);
    border-color: rgba(16, 185, 129, 0.18);
}
.upload-summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.85rem;
    margin: 0.75rem 0 1rem 0;
}
.upload-summary-card {
    padding: 1rem 1.05rem;
    border-radius: 18px;
    background: rgba(255,255,255,0.94);
    border: 1px solid rgba(226,232,240,0.9);
    box-shadow: 0 10px 24px rgba(15,23,42,0.04);
}
.upload-summary-card span {
    display: block;
    color: #64748B;
    font-size: 0.84rem;
    font-weight: 600;
    margin-bottom: 0.45rem;
}
.upload-summary-card strong {
    color: #1E3A8A;
    font-size: 1.8rem;
    line-height: 1.05;
}
@media (max-width: 1100px) {
    .upload-summary-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
</style>
"""


def get_upload_product_default_index(products, current_product_id: int | None) -> int:
    """根据当前产品优先选中上传页的产品下拉框。"""
    if not current_product_id:
        return 0

    for index, product in enumerate(products, start=1):
        if product.get("id") == current_product_id:
            return index
    return 0


def _build_truth_import_guidance(
    current_product_id: int | None, campaign_count: int
) -> tuple[str, str]:
    """生成人工判定表导入前的顺序提示。"""
    if not current_product_id:
        return ("warning", "先选择或创建产品，再导入人工判定表。")
    if campaign_count == 0:
        return (
            "warning",
            "建议先导入原始报表，再导入广告组人工判定表，否则广告组名称无法匹配。",
        )
    return (
        "success",
        "当前产品已具备导入条件：先看预检结果，再一键导入人工判定表。",
    )


def _persist_uploaded_file(uploaded_file, target_dir: Path) -> Path:
    """将 Streamlit 上传文件持久化到临时目录，供现有导入逻辑复用。"""
    suffix = Path(uploaded_file.name).suffix or ".xlsx"
    file_name = Path(uploaded_file.name).name or f"uploaded{suffix}"
    target_path = target_dir / file_name

    if hasattr(uploaded_file, "getvalue"):
        file_bytes = uploaded_file.getvalue()
    else:
        current_pos = uploaded_file.tell() if hasattr(uploaded_file, "tell") else None
        file_bytes = uploaded_file.read()
        if current_pos is not None and hasattr(uploaded_file, "seek"):
            uploaded_file.seek(current_pos)

    target_path.write_bytes(file_bytes)
    return target_path


def import_truth_workbooks_from_uploads(
    db,
    product_id: int,
    campaign_upload=None,
    aggregate_upload=None,
) -> dict[str, int]:
    """将 UI 上传的人工判定表落盘后导入 truth replay。"""
    with tempfile.TemporaryDirectory(prefix="amz-truth-upload-") as temp_dir:
        temp_path = Path(temp_dir)
        campaign_path = (
            _persist_uploaded_file(campaign_upload, temp_path)
            if campaign_upload is not None
            else None
        )
        aggregate_path = (
            _persist_uploaded_file(aggregate_upload, temp_path)
            if aggregate_upload is not None
            else None
        )
        return seed_truth_workbooks(
            db=db,
            product_id=product_id,
            campaign_workbook_path=campaign_path,
            aggregate_workbook_path=aggregate_path,
        )


def inspect_truth_workbooks_from_uploads(
    campaign_upload=None,
    aggregate_upload=None,
) -> dict[str, dict]:
    """对 UI 上传的人工判定表做导入前预检。"""
    with tempfile.TemporaryDirectory(prefix="amz-truth-inspect-") as temp_dir:
        temp_path = Path(temp_dir)
        summary: dict[str, dict] = {}
        if campaign_upload is not None:
            campaign_path = _persist_uploaded_file(campaign_upload, temp_path)
            summary["campaign"] = inspect_campaign_truth_workbook(campaign_path)
        if aggregate_upload is not None:
            aggregate_path = _persist_uploaded_file(aggregate_upload, temp_path)
            summary["aggregate"] = inspect_aggregate_truth_workbook(aggregate_path)
        return summary


def _render_truth_mapping_table(title: str, recognized_fields: dict[str, str]) -> None:
    if not recognized_fields:
        st.caption(f"{title}：当前没有识别到字段映射")
        return

    mapping_df = pd.DataFrame(
        [
            {"系统字段": field, "识别到的列": column}
            for field, column in recognized_fields.items()
        ]
    )
    st.caption(title)
    st.dataframe(mapping_df, width="stretch", hide_index=True)


def render_upload():
    """渲染文件上传页面"""
    st.markdown(UPLOAD_PAGE_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="upload-flow-shell">
            <span class="upload-flow-badge">导入流程</span>
            <h1>文件上传</h1>
            <p>把原始报表、广告组人工判定表和最终汇总结论表放在同一条流程里，先预检、再导入、再回到首页看结论。</p>
            <div class="upload-flow-chips">
                <span class="upload-flow-chip">1. 先选产品</span>
                <span class="upload-flow-chip">2. 先导原始报表</span>
                <span class="upload-flow-chip">3. 再导人工判定表</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    db = st.session_state.get("db")
    if not db:
        st.error("数据库未初始化")
        return

    # 产品选择/创建
    st.subheader("1. 选择或创建产品")

    products = db.get_all_products()
    product_options = ["创建新产品"] + [p["name"] for p in products]

    selected_option = st.selectbox("选择产品", product_options, index=get_upload_product_default_index(products, st.session_state.get("current_product_id")))

    if selected_option == "创建新产品":
        col1, col2 = st.columns(2)
        with col1:
            new_product_name = st.text_input("产品名称", placeholder="例如：无线充电器")
        with col2:
            new_product_asin = st.text_input("ASIN", placeholder="例如：B0XXXXXXXX")

        if st.button("创建产品"):
            if new_product_name:
                product_id = db.create_product(
                    name=new_product_name,
                    asin=new_product_asin or None,
                )
                st.session_state.current_product_id = product_id
                st.success(f"产品 '{new_product_name}' 创建成功")
                st.rerun()
            else:
                st.error("请输入产品名称")
    else:
        # 使用现有产品
        product = next((p for p in products if p["name"] == selected_option), None)
        if product:
            st.session_state.current_product_id = product["id"]

    st.divider()

    current_product_id = st.session_state.get("current_product_id")
    st.subheader("2. 导入人工判定表（可选）")

    if not current_product_id:
        st.info("请先选择或创建产品，再导入广告组人工判定表和最终汇总结论表。")
    else:
        current_product_name = next(
            (p["name"] for p in products if p["id"] == current_product_id),
            "当前产品",
        )
        st.caption(
            "如果这批数据已经在 Excel 里人工判定完成，可以直接导入两份表，系统会跳过重复审核并回放你的最终结论。"
        )
        campaign_count = db.execute(
            "SELECT COUNT(*) AS count FROM campaigns WHERE product_id = ?",
            (current_product_id,),
        ).fetchone()["count"]
        guidance_level, guidance_message = _build_truth_import_guidance(
            current_product_id, campaign_count
        )
        st.markdown(
            f"""
            <div class="upload-status-card upload-status-card--{guidance_level}">
                <strong>{current_product_name}</strong>
                <span>{guidance_message}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        campaign_truth_upload = st.file_uploader(
            "广告组人工判定表",
            type=["xlsx", "xls"],
            key="campaign_truth_upload",
            help="例如：广告组级别的否词和搜索词分析.xlsx",
        )
        aggregate_truth_upload = st.file_uploader(
            "最终汇总结论表",
            type=["xlsx", "xls"],
            key="aggregate_truth_upload",
            help="例如：ASIN层面汇总分析_v7.xlsx",
        )
        if campaign_truth_upload is not None and campaign_count == 0:
            st.warning("当前产品还没有原始报表导入后的广告活动。若要导入广告组人工判定表，请先导入原始报表，否则广告组名称无法匹配。")

        if campaign_truth_upload is not None or aggregate_truth_upload is not None:
            inspection = inspect_truth_workbooks_from_uploads(
                campaign_upload=campaign_truth_upload,
                aggregate_upload=aggregate_truth_upload,
            )
            with st.expander("查看人工判定表预检结果", expanded=True):
                if campaign_summary := inspection.get("campaign"):
                    if campaign_summary.get("ready"):
                        st.success(f"广告组人工判定表可识别：有效数据 {campaign_summary['data_rows']} 行")
                    else:
                        st.error("广告组人工判定表缺少关键字段，当前不能可靠导入")
                    if campaign_summary.get("missing_required"):
                        st.caption("缺少关键字段：" + "、".join(campaign_summary["missing_required"]))
                    _render_truth_mapping_table("广告组人工判定表字段映射", campaign_summary.get("recognized_fields", {}))

                if aggregate_summary := inspection.get("aggregate"):
                    if aggregate_summary.get("ready"):
                        st.success("最终汇总结论表可识别：前两个 sheet 均通过预检")
                    else:
                        st.warning("最终汇总结论表存在 sheet 字段缺失或动作信号不足，请先确认格式")
                    sheet_df = pd.DataFrame(
                        [
                            {
                                "sheet": sheet["sheet_name"],
                                "ASIN": sheet["asin_identifier"],
                                "行数": sheet["row_count"],
                                "缺少关键字段": "、".join(sheet["missing_required"]) or "无",
                                "动作信号": "、".join(sheet["action_fields"]) or "无",
                                "状态": "可导入" if sheet["ready"] else "需检查",
                            }
                            for sheet in aggregate_summary.get("analyzed_sheets", [])
                        ]
                    )
                    st.caption("最终汇总结论表 sheet 预检")
                    st.dataframe(sheet_df, width="stretch", hide_index=True)

        if st.button("导入人工判定表", key="import_truth_workbooks"):
            if campaign_truth_upload is None and aggregate_truth_upload is None:
                st.error("请至少上传一份人工判定表")
            else:
                with st.spinner("正在导入人工判定表..."):
                    summary = import_truth_workbooks_from_uploads(
                        db=db,
                        product_id=current_product_id,
                        campaign_upload=campaign_truth_upload,
                        aggregate_upload=aggregate_truth_upload,
                    )

                imported_parts = []
                if summary.get("campaign_rows", 0):
                    imported_parts.append(
                        f"广告组人工判定 {summary['campaign_rows']} 条"
                    )
                if summary.get("aggregate_rows", 0):
                    imported_parts.append(
                        f"最终汇总结论 {summary['aggregate_rows']} 条"
                    )
                if imported_parts:
                    st.success("导入完成：" + "，".join(imported_parts))
                    st.info("现在可以前往首页、搜索词分析和操作清单查看 truth-first 结果。")
                else:
                    st.warning("没有导入到任何有效人工判定数据，请检查表格内容。")

    st.divider()

    # 文件上传（支持批量）
    st.subheader("3. 上传搜索词报告")

    uploaded_files = st.file_uploader(
        "拖拽或点击上传文件（支持批量上传）",
        type=["csv", "xlsx", "xls"],
        help="支持亚马逊后台导出的搜索词报告（CSV或Excel格式），可同时选择多个文件",
        accept_multiple_files=True,
    )

    if uploaded_files:
        # 显示已选择的文件列表
        st.info(f"已选择 {len(uploaded_files)} 个文件")

        # 文件列表预览
        file_info = []
        for f in uploaded_files:
            file_info.append(f"• {f.name} ({f.size / 1024:.1f} KB)")
        st.text("\n".join(file_info))

        # 解析所有文件
        parser = FileParser()
        parsed_files = []
        total_records = 0

        with st.spinner("正在解析文件..."):
            for uploaded_file in uploaded_files:
                try:
                    df = parser.parse(uploaded_file)
                    if df is not None and not df.empty:
                        campaign_name = (
                            uploaded_file.name.replace(".csv", "")
                            .replace(".xlsx", "")
                            .replace(".xls", "")
                        )
                        parsed_files.append(
                            {
                                "name": uploaded_file.name,
                                "campaign_name": campaign_name,
                                "df": df,
                                "records": len(df),
                            }
                        )
                        total_records += len(df)
                except Exception as e:
                    st.warning(f"文件 {uploaded_file.name} 解析失败: {e}")

        if parsed_files:
            st.success(
                f"解析成功：{len(parsed_files)} 个文件，共 {total_records} 条记录"
            )

            # 显示预览
            st.subheader("4. 数据预览")

            # 使用tabs显示每个文件的预览
            if len(parsed_files) > 1:
                tabs = st.tabs(
                    [
                        f["campaign_name"][:20] + "..."
                        if len(f["campaign_name"]) > 20
                        else f["campaign_name"]
                        for f in parsed_files
                    ]
                )
                for i, tab in enumerate(tabs):
                    with tab:
                        df = parsed_files[i]["df"]
                        st.write(
                            f"**{parsed_files[i]['name']}** - {parsed_files[i]['records']} 条记录"
                        )
                        st.dataframe(df.head(5), width="stretch")
            else:
                # 单文件预览
                df = parsed_files[0]["df"]
                st.dataframe(df.head(10), width="stretch")

            # 汇总统计
            st.write("**汇总统计：**")
            all_dfs = [f["df"] for f in parsed_files]
            total_terms = sum(
                df["term"].nunique() if "term" in df.columns else 0
                for df in all_dfs
            )
            total_spend = sum(
                df["spend"].sum() if "spend" in df.columns else 0 for df in all_dfs
            )
            total_orders = sum(
                int(df["orders"].sum()) if "orders" in df.columns else 0
                for df in all_dfs
            )
            total_clicks = sum(
                int(df["clicks"].sum()) if "clicks" in df.columns else 0
                for df in all_dfs
            )
            st.markdown(
                f"""
                <div class="upload-summary-grid">
                    <div class="upload-summary-card"><span>搜索词数</span><strong>{total_terms}</strong></div>
                    <div class="upload-summary-card"><span>总花费</span><strong>${total_spend:.2f}</strong></div>
                    <div class="upload-summary-card"><span>总订单</span><strong>{total_orders}</strong></div>
                    <div class="upload-summary-card"><span>总点击</span><strong>{total_clicks}</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.divider()

            # 导入确认
            st.subheader("5. 确认导入")

            st.write(f"将创建 **{len(parsed_files)}** 个广告活动（每个文件一个）：")
            for f in parsed_files:
                st.text(f"• {f['campaign_name']}")

            auto_analyze = st.checkbox("导入后自动运行规则分析", value=True)

            if st.button("确认批量导入", type="primary"):
                product_id = st.session_state.get("current_product_id")

                if not product_id:
                    st.error("请先选择或创建产品")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    success_count = 0
                    total_imported = 0

                    for i, file_data in enumerate(parsed_files):
                        status_text.text(f"正在导入: {file_data['campaign_name']}...")
                        progress_bar.progress((i + 1) / len(parsed_files))

                        try:
                            # 创建活动
                            campaign_id = db.create_campaign(
                                product_id=product_id,
                                name=file_data["campaign_name"],
                            )

                            # 保存搜索词
                            count = db.save_search_terms(file_data["df"], campaign_id)
                            total_imported += count
                            success_count += 1

                        except Exception as e:
                            st.warning(f"导入 {file_data['campaign_name']} 失败: {e}")

                    progress_bar.progress(1.0)
                    status_text.empty()

                    st.success(
                        f"批量导入完成：{success_count}/{len(parsed_files)} 个文件成功，共 {total_imported} 条记录"
                    )

                    # 自动运行分析
                    if auto_analyze and success_count > 0:
                        with st.spinner("正在运行规则分析..."):
                            run_analysis(db, product_id)
                            st.success("分析完成")

        else:
            st.error("所有文件解析失败")

    # 使用说明
    with st.expander("使用说明"):
        st.markdown("""
        ### 如何导出亚马逊搜索词报告

        1. 登录亚马逊卖家后台
        2. 进入 **广告** → **广告活动管理器**
        3. 选择要分析的广告活动
        4. 点击 **搜索词** 标签
        5. 选择日期范围（建议30天或更长）
        6. 点击 **导出** 按钮，选择CSV或Excel格式

        ### 支持的文件格式

        - CSV文件（.csv）
        - Excel文件（.xlsx, .xls）

        ### 必需的列

        系统会自动识别以下列（支持中英文）：
        - 搜索词 / Customer Search Term
        - 展示 / Impressions
        - 点击 / Clicks
        - 花费 / Spend
        - 订单 / Orders
        - 销售额 / Sales
        """)


def run_analysis(db, product_id: int):
    """运行规则分析"""
    from src.data.aggregator import DataAggregator
    from src.rules.engine import RuleEngine

    # 聚合数据
    aggregator = DataAggregator(db)
    df = aggregator.aggregate_by_term(product_id)

    if df.empty:
        return

    # 规则分析
    engine = RuleEngine(db, product_id)
    results = engine.analyze(df)

    # 保存结果
    for result in results:
        db.save_analysis_result_by_term(
            product_id=product_id,
            term=result.term,
            triggered_rule=result.triggered_rule,
            suggested_action=result.suggested_action,
            action_type=result.action_type,
            confidence=result.confidence,
            ai_reasoning=result.ai_reasoning,
        )

    # v2.0: 为新词创建待审核的manual_reviews记录
    for result in results:
        # 检查是否需要人工审核相关性
        needs_review = getattr(result, "needs_review", False)
        relevance = getattr(result, "relevance", None)

        # 如果需要审核或相关性为pending/None，创建待审核记录
        if needs_review or relevance in (None, "pending"):
            db.upsert_manual_review(
                product_id=product_id,
                term=result.term,
                term_type=result.term_type,
                system_action=result.suggested_action,
                relevance="pending",  # 标记为待审核
                reviewed=False,
            )
