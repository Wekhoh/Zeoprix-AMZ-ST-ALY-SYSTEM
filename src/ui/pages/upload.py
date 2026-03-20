"""
文件上传页面
支持上传和解析CSV/Excel文件
"""

import streamlit as st

from src.config.logger import get_logger
from src.data.parser import FileParser

logger = get_logger(__name__)


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

    selected_option = st.selectbox("选择产品", product_options)

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

    # 文件上传（支持批量）
    st.subheader("2. 上传搜索词报告")

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
            st.subheader("3. 数据预览")

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
                        st.dataframe(df.head(5), use_container_width=True)
            else:
                # 单文件预览
                df = parsed_files[0]["df"]
                st.dataframe(df.head(10), use_container_width=True)

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
            st.subheader("4. 确认导入")

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
