"""
文件上传页面
支持上传和解析CSV/Excel文件
"""

import streamlit as st

from src.config.logger import get_logger
from src.data.parser import FileParser
from src.ui.utils import safe_error

logger = get_logger(__name__)


def render_upload():
    """渲染文件上传页面"""
    st.title("📤 文件上传")

    db = st.session_state.get("db")
    if not db:
        st.error("数据库未初始化")
        return

    # 产品选择/创建
    st.subheader("1️⃣ 选择或创建产品")

    products = db.get_all_products()
    product_options = ["➕ 创建新产品"] + [p["name"] for p in products]

    selected_option = st.selectbox("选择产品", product_options)

    if selected_option == "➕ 创建新产品":
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
                st.success(f"✅ 产品 '{new_product_name}' 创建成功！")
                st.rerun()
            else:
                st.error("请输入产品名称")
    else:
        # 使用现有产品
        product = next((p for p in products if p["name"] == selected_option), None)
        if product:
            st.session_state.current_product_id = product["id"]

    st.divider()

    # 文件上传
    st.subheader("2️⃣ 上传搜索词报告")

    uploaded_file = st.file_uploader(
        "拖拽或点击上传文件",
        type=["csv", "xlsx", "xls"],
        help="支持亚马逊后台导出的搜索词报告（CSV或Excel格式）",
    )

    if uploaded_file:
        st.info(f"已选择文件: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

        # 解析预览
        with st.spinner("正在解析文件..."):
            try:
                parser = FileParser()
                df = parser.parse(uploaded_file)

                if df is not None and not df.empty:
                    st.success(f"✅ 解析成功！共 {len(df)} 条记录")

                    # 显示预览
                    st.subheader("3️⃣ 数据预览")

                    # 列映射检查
                    st.write("**识别到的列：**")
                    col_mapping = []
                    for col in df.columns:
                        col_mapping.append(f"• {col}")
                    st.text("\n".join(col_mapping[:10]))

                    if len(col_mapping) > 10:
                        st.text(f"... 还有 {len(col_mapping) - 10} 列")

                    # 数据预览表格
                    st.dataframe(df.head(10), use_container_width=True)

                    # 统计信息
                    st.write("**统计信息：**")
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        if "term" in df.columns:
                            st.metric("搜索词数", df["term"].nunique())

                    with col2:
                        if "spend" in df.columns:
                            st.metric("总花费", f"${df['spend'].sum():.2f}")

                    with col3:
                        if "orders" in df.columns:
                            st.metric("总订单", int(df["orders"].sum()))

                    with col4:
                        if "clicks" in df.columns:
                            st.metric("总点击", int(df["clicks"].sum()))

                    st.divider()

                    # 导入确认
                    st.subheader("4️⃣ 确认导入")

                    # 活动名称
                    campaign_name = st.text_input(
                        "广告活动名称",
                        value=uploaded_file.name.replace(".csv", "").replace(".xlsx", ""),
                    )

                    if st.button("确认导入", type="primary"):
                        product_id = st.session_state.get("current_product_id")

                        if not product_id:
                            st.error("请先选择或创建产品")
                        else:
                            with st.spinner("正在导入数据..."):
                                try:
                                    # 创建活动
                                    campaign_id = db.create_campaign(
                                        product_id=product_id,
                                        name=campaign_name,
                                    )

                                    # 保存搜索词
                                    count = db.save_search_terms(df, campaign_id)

                                    st.success(f"✅ 导入成功！共导入 {count} 条搜索词记录")

                                    # 自动运行分析
                                    if st.checkbox("自动运行规则分析", value=True):
                                        with st.spinner("正在分析..."):
                                            run_analysis(db, product_id)
                                            st.success("✅ 分析完成！")

                                except Exception as e:
                                    safe_error("数据导入", e)

                else:
                    st.error("文件解析失败或为空")

            except Exception as e:
                safe_error("文件解析", e)

    # 使用说明
    with st.expander("📖 使用说明"):
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
