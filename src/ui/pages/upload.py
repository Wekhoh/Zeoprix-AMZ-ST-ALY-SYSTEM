"""
文件上传页面
支持上传和解析CSV/Excel文件
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.ai.copilot import build_upload_ai_brief
from src.analysis.truth_replay import (
    apply_reviewed_truth,
    build_analysis_run_snapshot_rows,
    build_analysis_run_snapshot_summary,
    inspect_aggregate_truth_workbook,
    inspect_campaign_truth_workbook,
    seed_truth_workbooks,
)
from src.config.logger import get_logger
from src.data.parser import FileParser
from src.ui.pages.analysis import _render_ai_brief_card

logger = get_logger(__name__)

UPLOAD_AI_BRIEF_STATE_KEY = "upload_ai_brief_state"

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


def _resolve_upload_role_context(db, product_id: int | None) -> dict[str, str | int]:
    """解析上传页当前用户与工作区角色上下文。"""
    current_user_id = st.session_state.get("current_user_id")
    current_user = (
        db.get_user(user_id=current_user_id) if current_user_id is not None else None
    )
    if current_user is None:
        current_user = db.get_or_create_local_owner()

    if product_id:
        current_role = db.get_workspace_role(product_id, current_user["id"]) or "viewer"
    elif current_user["email"] == db.DEFAULT_LOCAL_OWNER_EMAIL:
        current_role = "admin"
    else:
        current_role = "viewer"

    return {
        "current_user_name": current_user.get("display_name") or current_user["email"],
        "current_role": current_role,
        "current_user_id": current_user["id"],
    }


def _build_upload_access_meta(current_role: str) -> dict[str, object]:
    """构建上传页角色门控摘要。"""
    can_create_workspace = current_role == "admin"
    can_import = current_role in {"admin", "editor"}
    restricted_sections = []
    if not can_create_workspace:
        restricted_sections.append("创建工作区")
    if not can_import:
        restricted_sections.append("导入原始报表 / 人工校准表")

    return {
        "title": "当前上传权限",
        "description": "把工作区创建和数据导入分开管控：管理员负责开工作区，管理员/编辑者负责导入数据，查看者只能浏览导入说明与当前状态。",
        "chips": [
            f"当前角色：{current_role}",
            "可创建工作区" if can_create_workspace else "不可创建工作区",
            "可导入数据" if can_import else "仅查看导入流程",
        ],
        "restricted_sections": restricted_sections,
        "can_create_workspace": can_create_workspace,
        "can_import": can_import,
        "create_blocked_message": "当前角色不能创建新工作区，请联系管理员先建立产品工作区。",
        "import_blocked_message": "当前角色只能查看导入流程，原始报表和人工校准表的导入需要管理员或编辑者权限。",
    }


def _build_truth_import_guidance(
    current_product_id: int | None, campaign_count: int
) -> tuple[str, str]:
    """生成人工校准导入前的顺序提示。"""
    if not current_product_id:
        return ("warning", "先选择或创建产品工作区，再导入人工校准表。")
    if campaign_count == 0:
        return (
            "warning",
            "建议先导入原始报表，再导入广告组人工校准表，否则广告活动名称无法匹配。",
        )
    return (
        "success",
        "当前工作区已具备导入条件：先看预检结果，再一键导入人工校准表。",
    )


def _build_analysis_run_state(
    status: str,
    message: str,
    *,
    terms_analyzed: int = 0,
    results_saved: int = 0,
    pending_reviews: int = 0,
    can_retry: bool = False,
) -> dict[str, object]:
    """统一分析运行状态，区分上传成功与分析结果是否真正生成。"""
    return {
        "status": status,
        "message": message,
        "terms_analyzed": int(terms_analyzed),
        "results_saved": int(results_saved),
        "pending_reviews": int(pending_reviews),
        "can_retry": can_retry,
    }


def _render_analysis_run_feedback(state: dict[str, object]) -> None:
    """根据分析运行状态展示成功/警告/失败反馈。"""
    message = str(state.get("message") or "分析完成")
    status = str(state.get("status") or "warning")

    metrics = []
    terms_analyzed = int(state.get("terms_analyzed") or 0)
    results_saved = int(state.get("results_saved") or 0)
    pending_reviews = int(state.get("pending_reviews") or 0)

    if terms_analyzed:
        metrics.append(f"分析词数 {terms_analyzed}")
    if results_saved:
        metrics.append(f"建议 {results_saved} 条")
    if pending_reviews:
        metrics.append(f"待审核 {pending_reviews} 条")

    if metrics:
        message = f"{message}（{'，'.join(metrics)}）"

    if status == "success":
        st.success(message)
    elif status == "error":
        st.error(message)
    else:
        st.warning(message)


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
    """将 UI 上传的人工判定表落盘后导入人工校准层。"""
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
    """对 UI 上传的人工判定表做人工校准导入前预检。"""
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
            <p>把原始报表、可选的人工校准表和最终结论导入放在同一条流程里：先跑自动建议，再按需要做人工校准，最后查看结论与执行清单。</p>
            <div class="upload-flow-chips">
                <span class="upload-flow-chip">1. 先选产品工作区</span>
                <span class="upload-flow-chip">2. 先导原始报表</span>
                <span class="upload-flow-chip">3. 按需导入人工校准表</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    db = st.session_state.get("db")
    if not db:
        st.error("数据库未初始化")
        return

    current_product_id = st.session_state.get("current_product_id")
    products = db.get_all_products()
    current_product_name = next(
        (p["name"] for p in products if p["id"] == current_product_id),
        "当前产品",
    )
    access_context = _resolve_upload_role_context(db, current_product_id)
    access_meta = _build_upload_access_meta(access_context["current_role"])
    access_chips_html = "".join(
        f'<span class="upload-flow-chip">{chip}</span>' for chip in access_meta["chips"]
    )
    st.markdown(
        f"""
        <div class="upload-status-card">
            <strong>{access_meta["title"]}</strong>
            <span>{access_meta["description"]}</span>
            <div class="upload-flow-chips" style="margin-top:0.85rem;">{access_chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 产品选择/创建
    st.subheader("1. 选择或创建产品")

    product_options = ["创建新产品"] + [p["name"] for p in products]

    selected_option = st.selectbox("选择产品", product_options, index=get_upload_product_default_index(products, st.session_state.get("current_product_id")))

    if selected_option == "创建新产品":
        if not access_meta["can_create_workspace"]:
            st.info(access_meta["create_blocked_message"])
        else:
            col1, col2 = st.columns(2)
            with col1:
                new_product_name = st.text_input(
                    "产品名称", placeholder="例如：无线充电器"
                )
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
            current_product_id = product["id"]
            current_product_name = product["name"]

    st.divider()

    current_product_id = st.session_state.get("current_product_id")
    st.subheader("2. 导入人工校准表（可选）")

    if not current_product_id:
        st.info("请先选择或创建产品工作区，再按需导入广告组人工判定表和最终汇总结论表。")
    else:
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
        if not access_meta["can_import"]:
            st.info(access_meta["import_blocked_message"])
        else:
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
                st.warning("当前工作区还没有原始报表导入后的广告活动。若要导入广告组人工判定表，请先导入原始报表，否则广告活动名称无法匹配。")

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

            if st.button("导入人工校准表", key="import_truth_workbooks"):
                if campaign_truth_upload is None and aggregate_truth_upload is None:
                    st.error("请至少上传一份人工校准表")
                else:
                    with st.spinner("正在导入人工校准表..."):
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
                        st.info("现在可以前往首页、搜索词分析和操作清单查看自动建议、人工校准和最终结论。")
                    else:
                        st.warning("没有导入到任何有效人工校准数据，请检查表格内容。")

    st.divider()

    # 文件上传（支持批量）
    st.subheader("3. 上传搜索词报告")

    if not access_meta["can_import"]:
        st.info(access_meta["import_blocked_message"])
        return

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

            upload_ai_brief_state = st.session_state.get(UPLOAD_AI_BRIEF_STATE_KEY)
            if (
                not isinstance(upload_ai_brief_state, dict)
                or int(upload_ai_brief_state.get("product_id") or 0) != int(current_product_id or 0)
            ):
                upload_ai_brief_state = {}

            analysis_state_for_brief = upload_ai_brief_state.get("analysis_state")
            parsed_meta = upload_ai_brief_state.get("parsed_meta") or {}
            parsed_files_count = int(parsed_meta.get("parsed_files_count") or len(parsed_files))
            total_terms_for_brief = int(parsed_meta.get("total_terms") or total_terms)
            total_spend_for_brief = float(parsed_meta.get("total_spend") or total_spend)
            total_clicks_for_brief = int(parsed_meta.get("total_clicks") or total_clicks)
            total_orders_for_brief = int(parsed_meta.get("total_orders") or total_orders)

            upload_ai_brief = build_upload_ai_brief(
                product_name=current_product_name,
                parsed_files_count=parsed_files_count,
                total_terms=total_terms_for_brief,
                total_spend=total_spend_for_brief,
                total_clicks=total_clicks_for_brief,
                total_orders=total_orders_for_brief,
                analysis_state=analysis_state_for_brief if isinstance(analysis_state_for_brief, dict) else None,
            )
            _render_ai_brief_card(
                title="AI 导入摘要",
                brief=upload_ai_brief,
                key_prefix="upload_ai_brief",
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
                    analysis_state: dict[str, object] | None = None
                    if auto_analyze and success_count > 0:
                        with st.spinner("正在运行规则分析..."):
                            analysis_state = run_analysis(db, product_id)
                        _render_analysis_run_feedback(analysis_state)

                    st.session_state[UPLOAD_AI_BRIEF_STATE_KEY] = {
                        "product_id": product_id,
                        "parsed_meta": {
                            "parsed_files_count": len(parsed_files),
                            "total_terms": total_terms,
                            "total_spend": total_spend,
                            "total_clicks": total_clicks,
                            "total_orders": total_orders,
                        },
                        "analysis_state": analysis_state,
                    }

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


def run_analysis(db, product_id: int) -> dict[str, object]:
    """运行规则分析，并显式返回分析状态。"""
    from src.data.aggregator import DataAggregator
    from src.rules.engine import RuleEngine

    try:
        aggregator = DataAggregator(db)
        df = aggregator.aggregate_by_term(product_id)

        if df.empty:
            return _build_analysis_run_state(
                "warning",
                "当前导入数据暂时不足以生成搜索词分析结果，请先确认原始报表内容。",
            )

        engine = RuleEngine(db, product_id)
        results = engine.analyze(df)

        if not results:
            return _build_analysis_run_state(
                "warning",
                "规则分析已运行，但当前没有生成可保存的建议。",
                terms_analyzed=len(df),
            )

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

        return _build_analysis_run_state(
            "success",
            "分析完成。",
            terms_analyzed=len(df),
            results_saved=results_saved,
            pending_reviews=pending_reviews,
        )
    except Exception:
        logger.exception("规则分析失败", extra={"product_id": product_id})
        return _build_analysis_run_state(
            "error",
            "规则分析失败，请稍后重试。",
            can_retry=True,
        )
