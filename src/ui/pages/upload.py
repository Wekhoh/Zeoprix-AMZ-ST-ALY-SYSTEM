"""
文件上传页面
支持上传和解析CSV/Excel文件
"""

import tempfile
from pathlib import Path

import streamlit as st

from src.analysis.truth_replay import seed_truth_workbooks
from src.config.logger import get_logger
from src.data.parser import FileParser

logger = get_logger(__name__)


def get_upload_product_default_index(products, current_product_id: int | None) -> int:
    """根据当前产品优先选中上传页的产品下拉框。"""
    if not current_product_id:
        return 0

    for index, product in enumerate(products, start=1):
        if product.get("id") == current_product_id:
            return index
    return 0


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


def render_upload():
    """渲染文件上传页面"""
    st.title("文件上传")

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
        st.caption(
            "如果这批数据已经在 Excel 里人工判定完成，可以直接导入两份表，系统会跳过重复审核并回放你的最终结论。"
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
            col1, col2, col3, col4 = st.columns(4)

            all_dfs = [f["df"] for f in parsed_files]

            with col1:
                total_terms = sum(
                    df["term"].nunique() if "term" in df.columns else 0
                    for df in all_dfs
                )
                st.metric("搜索词数", total_terms)
            with col2:
                total_spend = sum(
                    df["spend"].sum() if "spend" in df.columns else 0 for df in all_dfs
                )
                st.metric("总花费", f"${total_spend:.2f}")
            with col3:
                total_orders = sum(
                    int(df["orders"].sum()) if "orders" in df.columns else 0
                    for df in all_dfs
                )
                st.metric("总订单", total_orders)
            with col4:
                total_clicks = sum(
                    int(df["clicks"].sum()) if "clicks" in df.columns else 0
                    for df in all_dfs
                )
                st.metric("总点击", total_clicks)

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
