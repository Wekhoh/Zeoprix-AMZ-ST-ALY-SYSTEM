"""
系统设置 - 规则配置与管理
从 settings.py 拆分
"""


import streamlit as st

from src.config.logger import get_logger
from src.rules.engine import RuleEngine
from src.ui.pages.settings_data import (
    get_default_config,
    render_config_history,
    save_config_version,
)
from src.ui.utils import safe_error

logger = get_logger(__name__)


def _build_rule_settings_summary(
    config: dict | None,
    thresholds: dict | None,
) -> dict[str, str | list[str]]:
    """构建规则配置页的人话摘要。"""
    config = config or {}
    thresholds = thresholds or {}
    stage_label = "新品期" if config.get("is_new_product", False) else "常规期"
    analysis_clicks = int(thresholds.get("min_clicks_for_analysis", 20))
    asin_clicks = int(thresholds.get("min_clicks_for_asin_neg", 6))
    asin_spend = float(thresholds.get("high_spend_no_order", 20.0))
    good_cvr = float(thresholds.get("good_cvr", 0.10))
    return {
        "title": "规则阈值配置",
        "description": "先确定产品阶段和样本量门槛，再微调 CVR、否词、手动投放和竞品 ASIN 规则，避免把整页输入框当 Excel 填。",
        "chips": [
            f"当前阶段：{stage_label}",
            f"可靠分析点击门槛 {analysis_clicks}",
            f"ASIN 否定门槛 {asin_clicks} 点击 / ${asin_spend:.0f}",
            f"好转化率 {good_cvr:.0%}",
        ],
    }


def reapply_rules_to_data(db, product_id: int) -> int:
    """重新应用规则到现有数据

    Args:
        db: 数据库实例
        product_id: 产品ID

    Returns:
        处理的数据条数
    """
    df = db.get_search_terms({"product_id": product_id})
    if df is None or df.empty:
        return 0

    column_mapping = {
        "impressions": "total_impressions",
        "clicks": "total_clicks",
        "spend": "total_spend",
        "sales": "total_sales",
        "orders": "total_orders",
    }
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns and new_col not in df.columns:
            df[new_col] = df[old_col]

    if "ctr" not in df.columns:
        df["ctr"] = df.apply(
            lambda r: r["total_clicks"] / r["total_impressions"]
            if r.get("total_impressions", 0) > 0
            else 0,
            axis=1,
        )
    if "cpc" not in df.columns:
        df["cpc"] = df.apply(
            lambda r: r["total_spend"] / r["total_clicks"]
            if r.get("total_clicks", 0) > 0
            else 0,
            axis=1,
        )
    if "cvr" not in df.columns:
        df["cvr"] = df.apply(
            lambda r: r["total_orders"] / r["total_clicks"]
            if r.get("total_clicks", 0) > 0
            else 0,
            axis=1,
        )
    if "roas" not in df.columns:
        df["roas"] = df.apply(
            lambda r: r["total_sales"] / r["total_spend"]
            if r.get("total_spend", 0) > 0
            else 0,
            axis=1,
        )

    engine = RuleEngine(db, product_id)
    results = engine.analyze(df)

    count = 0
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
        count += 1

    return count


def render_rule_settings(db, product_id: int):
    """渲染规则配置"""
    if not product_id:
        st.warning("请先选择产品")
        return

    # 获取产品配置
    product = db.get_product(product_id)
    config = product.get("config", {}) if product else {}
    thresholds = config.get("thresholds", {})
    summary = _build_rule_settings_summary(config, thresholds)
    st.write(f"### {summary['title']}")
    st.caption(summary["description"])
    chip_cols = st.columns(len(summary["chips"]))
    for col, chip in zip(chip_cols, summary["chips"], strict=False):
        with col:
            st.info(chip)

    # 新品期设置
    st.write("#### 产品阶段")

    is_new_product = st.checkbox(
        "新品期模式",
        value=config.get("is_new_product", False),
        help="新品期主要看样本量，不侧重ACOS",
    )

    if is_new_product:
        st.info("新品期模式：分析更注重点击样本量，ACOS阈值会放宽")

    st.divider()

    # 样本量阈值（新增）
    st.write("#### 样本量阈值")

    col1, col2 = st.columns(2)

    with col1:
        min_clicks_for_analysis = st.number_input(
            "可靠分析最小点击数",
            min_value=1,
            max_value=100,
            value=int(thresholds.get("min_clicks_for_analysis", 20)),
            step=1,
            help="点击数达到此值才进行可靠分析（建议20+）",
        )

        min_clicks_for_asin_neg = st.number_input(
            "ASIN否定最小点击数",
            min_value=1,
            max_value=50,
            value=int(thresholds.get("min_clicks_for_asin_neg", 6)),
            step=1,
            help="ASIN点击数达到此值才考虑否定",
        )

    with col2:
        high_spend_no_order = st.number_input(
            "高花费无订单阈值 ($)",
            min_value=0.0,
            max_value=200.0,
            value=float(thresholds.get("high_spend_no_order", 20.0)),
            step=1.0,
            help="ASIN花费超过此值且零订单则否定",
        )

    st.divider()

    # 转化率阈值（新增）
    st.write("#### 转化率阈值 (CVR)")

    col1, col2 = st.columns(2)

    with col1:
        good_cvr = st.number_input(
            "好转化率 (CVR)",
            min_value=0.0,
            max_value=1.0,
            value=float(thresholds.get("good_cvr", 0.10)),
            step=0.01,
            format="%.2f",
            help="CVR高于此值视为表现好（建议10%）",
        )

    with col2:
        bad_cvr = st.number_input(
            "差转化率 (CVR)",
            min_value=0.0,
            max_value=1.0,
            value=float(thresholds.get("bad_cvr", 0.05)),
            step=0.01,
            format="%.2f",
            help="CVR低于此值视为表现差（建议5%）",
        )

    st.divider()

    # 否词规则（原有）
    st.write("#### 否词规则")

    col1, col2 = st.columns(2)

    with col1:
        high_spend_threshold = st.number_input(
            "关键词高花费阈值 ($)",
            min_value=0.0,
            max_value=1000.0,
            value=float(config.get("high_spend_threshold", 10.0)),
            step=1.0,
            help="关键词花费超过此值且零转化则建议否定",
        )

        low_ctr_threshold = st.number_input(
            "低点击率阈值",
            min_value=0.0,
            max_value=1.0,
            value=float(config.get("low_ctr_threshold", 0.001)),
            step=0.001,
            format="%.3f",
            help="点击率低于此值建议否定",
        )

    with col2:
        min_clicks_threshold = st.number_input(
            "最小点击数（统计有效性）",
            min_value=1,
            max_value=100,
            value=int(config.get("min_clicks_threshold", 10)),
            step=1,
            help="点击数需达到此值才进行分析",
        )

        high_acos_threshold = st.number_input(
            "高ACOS阈值",
            min_value=0.0,
            max_value=5.0,
            value=float(config.get("high_acos_threshold", 0.5)),
            step=0.05,
            format="%.2f",
            help="ACOS超过此值建议否定或降低出价",
        )

    st.divider()

    # 手动投放规则
    st.write("#### 手动投放规则")

    col1, col2 = st.columns(2)

    with col1:
        min_orders_for_manual = st.number_input(
            "最小订单数",
            min_value=1,
            max_value=50,
            value=int(config.get("min_orders_for_manual", 2)),
            step=1,
            help="订单数达到此值才建议手动投放",
        )

        target_acos = st.number_input(
            "目标ACOS",
            min_value=0.0,
            max_value=1.0,
            value=float(config.get("target_acos", 0.25)),
            step=0.05,
            format="%.2f",
            help="低于此ACOS值视为表现良好",
        )

    with col2:
        min_conversion_rate = st.number_input(
            "最小转化率",
            min_value=0.0,
            max_value=1.0,
            value=float(config.get("min_conversion_rate", 0.05)),
            step=0.01,
            format="%.2f",
            help="转化率需达到此值才建议手动投放",
        )

    st.divider()

    # 竞品规则
    st.write("#### 竞品ASIN规则")

    competitor_high_acos = st.number_input(
        "竞品高ACOS阈值",
        min_value=0.0,
        max_value=5.0,
        value=float(config.get("competitor_high_acos", 0.4)),
        step=0.05,
        format="%.2f",
        help="竞品ASIN的ACOS超过此值建议停止投放",
    )

    st.divider()

    # 保存按钮
    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "保存配置", type="primary", width="stretch", key="save_rule_config"
        ):
            # 合并新阈值配置
            new_thresholds = {
                "min_clicks_for_analysis": min_clicks_for_analysis,
                "min_clicks_for_asin_neg": min_clicks_for_asin_neg,
                "high_spend_no_order": high_spend_no_order,
                "good_cvr": good_cvr,
                "bad_cvr": bad_cvr,
            }

            new_config = {
                **config,  # 保留其他配置
                "is_new_product": is_new_product,
                "high_spend_threshold": high_spend_threshold,
                "low_ctr_threshold": low_ctr_threshold,
                "min_clicks_threshold": min_clicks_threshold,
                "high_acos_threshold": high_acos_threshold,
                "min_orders_for_manual": min_orders_for_manual,
                "target_acos": target_acos,
                "min_conversion_rate": min_conversion_rate,
                "competitor_high_acos": competitor_high_acos,
                "thresholds": new_thresholds,
            }

            try:
                # 保存版本历史
                save_config_version(db, product_id, config, new_config)

                # 更新产品配置
                db.update_product_config(product_id, new_config)
                st.success("配置已保存")
                st.rerun()
            except Exception as e:
                safe_error("配置保存", e)

    with col2:
        if st.button("恢复默认", width="stretch", key="reset_rule_config"):
            try:
                default_config = get_default_config()
                db.update_product_config(product_id, default_config)
                st.success("已恢复默认配置")
                st.rerun()
            except Exception as e:
                safe_error("配置恢复", e)

    # 版本历史
    st.divider()
    with st.expander("配置版本历史"):
        render_config_history(db, product_id)


def render_rule_management(db, product_id: int):
    """渲染规则管理界面 - 支持增删改查自定义规则"""
    st.write("### 规则管理")
    st.caption("这里处理的是规则本身：优先级、启用状态和重新应用。要改阈值，请回到“规则配置”；要改词库，请去“关键词库”。")

    st.info("""
    **规则说明**
    - 规则按优先级数值从小到大执行（数值越小优先级越高）
    - 使用 first-match-wins 策略：第一个匹配的规则生效
    - 全局规则（产品ID为空）适用于所有产品
    """)

    # 获取所有规则（包括禁用的）
    rules = db.get_all_rules(include_disabled=True)

    # 操作按钮行
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    with col1:
        if st.button("添加新规则", type="primary", key="add_rule_btn"):
            st.session_state.show_add_rule_form = True

    with col2:
        if st.button("重置为默认规则", key="reset_rules_btn"):
            st.session_state.confirm_reset_rules = True

    with col3:
        if st.button(
            "重新应用规则",
            key="reapply_rules_btn",
            help="将当前规则重新应用到所有现有数据",
        ):
            st.session_state.confirm_reapply_rules = True

    with col4:
        # 显示规则统计
        enabled_count = len([r for r in rules if r.get("enabled", 1)])
        st.metric("启用的规则", f"{enabled_count}/{len(rules)}")

    # 确认重置对话框
    if st.session_state.get("confirm_reset_rules"):
        st.warning("确定要重置所有规则为默认值吗？这将删除所有自定义规则！")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("确认重置", type="primary", key="confirm_reset"):
                try:
                    count = db.reset_rules_to_default(product_id=None)
                    st.success(f"已重置为 {count} 条默认规则")
                    st.session_state.confirm_reset_rules = False
                    st.rerun()
                except Exception as e:
                    safe_error("规则重置", e)
        with col2:
            if st.button("取消", key="cancel_reset"):
                st.session_state.confirm_reset_rules = False
                st.rerun()

    # 确认重新应用规则对话框
    if st.session_state.get("confirm_reapply_rules"):
        st.warning("确定要将当前规则重新应用到所有现有数据吗？这将覆盖之前的分析结果！")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("确认应用", type="primary", key="confirm_reapply"):
                try:
                    count = reapply_rules_to_data(db, product_id)
                    st.success(f"已重新应用规则到 {count} 条数据")
                    st.session_state.confirm_reapply_rules = False
                    st.rerun()
                except Exception as e:
                    safe_error("规则应用", e)
        with col2:
            if st.button("取消", key="cancel_reapply"):
                st.session_state.confirm_reapply_rules = False
                st.rerun()

    st.divider()

    # 添加新规则表单
    if st.session_state.get("show_add_rule_form"):
        render_add_rule_form(db, product_id)
        st.divider()

    # 编辑规则表单
    if st.session_state.get("editing_rule_id"):
        rule_to_edit = next(
            (r for r in rules if r["id"] == st.session_state.editing_rule_id), None
        )
        if rule_to_edit:
            render_edit_rule_form(db, rule_to_edit)
            st.divider()

    # 规则列表
    st.write("#### 当前规则列表")

    if not rules:
        st.info("暂无规则，请添加或重置为默认规则")
        return

    # 按规则类型分组显示
    keyword_rules = [r for r in rules if r.get("rule_type") == "keyword"]
    asin_rules = [r for r in rules if r.get("rule_type") == "asin"]
    other_rules = [r for r in rules if r.get("rule_type") not in ["keyword", "asin"]]

    # 关键词规则
    if keyword_rules:
        st.write("##### 关键词规则")
        render_rules_table(db, keyword_rules)

    # ASIN规则
    if asin_rules:
        st.write("##### ASIN规则")
        render_rules_table(db, asin_rules)

    # 其他规则
    if other_rules:
        st.write("##### 其他规则")
        render_rules_table(db, other_rules)


def render_rules_table(db, rules: list):
    """渲染规则表格"""
    for rule in sorted(rules, key=lambda x: x.get("priority", 100)):
        rule_id = rule["id"]
        is_enabled = rule.get("enabled", 1)

        # 使用容器显示每条规则
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([0.5, 2, 1.5, 1.5, 1.5])

            with col1:
                st.write(f"**P{rule.get('priority', 100)}**")

            with col2:
                rule_name = rule.get("name", "未命名")
                if not is_enabled:
                    rule_name = f"~~{rule_name}~~ (禁用)"
                st.write(rule_name)

            with col3:
                # 显示条件摘要
                conditions = rule.get("conditions", {})
                cond_summary = format_conditions_summary(conditions)
                st.caption(
                    cond_summary[:50] + "..."
                    if len(cond_summary) > 50
                    else cond_summary
                )

            with col4:
                st.write(rule.get("action", ""))

            with col5:
                # 操作按钮
                btn_col1, btn_col2, btn_col3 = st.columns(3)

                with btn_col1:
                    # 启用/禁用切换
                    toggle_label = "禁用" if is_enabled else "启用"
                    if st.button(
                        toggle_label, key=f"toggle_{rule_id}", width="stretch"
                    ):
                        try:
                            db.toggle_rule(rule_id, not is_enabled)
                            st.rerun()
                        except Exception as e:
                            safe_error("规则切换", e)

                with btn_col2:
                    if st.button("编辑", key=f"edit_{rule_id}", width="stretch"):
                        st.session_state.editing_rule_id = rule_id
                        st.session_state.show_add_rule_form = False
                        st.rerun()

                with btn_col3:
                    if st.button("删除", key=f"delete_{rule_id}", width="stretch"):
                        st.session_state[f"confirm_delete_{rule_id}"] = True
                        st.rerun()

        # 确认删除
        if st.session_state.get(f"confirm_delete_{rule_id}"):
            st.warning(f"确定要删除规则 '{rule.get('name')}' 吗？")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("确认删除", key=f"confirm_del_{rule_id}", type="primary"):
                    try:
                        db.delete_rule(rule_id)
                        del st.session_state[f"confirm_delete_{rule_id}"]
                        st.success("规则已删除")
                        st.rerun()
                    except Exception as e:
                        safe_error("规则删除", e)
            with col2:
                if st.button("取消", key=f"cancel_del_{rule_id}"):
                    del st.session_state[f"confirm_delete_{rule_id}"]
                    st.rerun()

        st.divider()


def render_add_rule_form(db, product_id: int):
    """渲染添加规则表单"""
    st.write("#### 添加新规则")

    with st.form("add_rule_form"):
        col1, col2 = st.columns(2)

        with col1:
            rule_name = st.text_input(
                "规则名称 *",
                placeholder="例如：高花费零转化",
                help="给规则起一个容易识别的名称",
            )

            rule_type = st.selectbox(
                "规则类型 *",
                options=["keyword", "asin", "all"],
                format_func=lambda x: {
                    "keyword": "关键词规则",
                    "asin": "ASIN规则",
                    "all": "通用规则",
                }.get(x, x),
                help="规则适用于哪种类型的搜索词",
            )

            priority = st.number_input(
                "优先级 *",
                min_value=1,
                max_value=1000,
                value=50,
                step=1,
                help="数值越小优先级越高（建议1-100）",
            )

        with col2:
            action = st.text_input(
                "建议动作 *",
                placeholder="例如：否定精准、手动投放",
                help="匹配此规则时的建议操作",
            )

            is_global = st.checkbox(
                "全局规则",
                value=True,
                help="全局规则适用于所有产品",
            )

            enabled = st.checkbox(
                "立即启用",
                value=True,
            )

        st.write("**条件配置**")
        st.caption("设为0或留空表示不限制该条件，-1表示不设上限")

        # 第一行：基础指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.write("花费条件")
            spend_min = st.number_input(
                "最小花费 ($)", min_value=0.0, value=0.0, step=1.0, key="add_spend_min"
            )
            spend_max = st.number_input(
                "最大花费 ($)", min_value=0.0, value=0.0, step=1.0, key="add_spend_max"
            )

        with col2:
            st.write("订单条件")
            orders_min = st.number_input(
                "最小订单", min_value=0, value=0, step=1, key="add_orders_min"
            )
            orders_max = st.number_input(
                "最大订单",
                min_value=-1,
                value=-1,
                step=1,
                key="add_orders_max",
                help="-1表示不限制",
            )

        with col3:
            st.write("点击条件")
            clicks_min = st.number_input(
                "最小点击", min_value=0, value=0, step=1, key="add_clicks_min"
            )
            clicks_max = st.number_input(
                "最大点击",
                min_value=-1,
                value=-1,
                step=1,
                key="add_clicks_max",
                help="-1表示不限制",
            )

        with col4:
            st.write("曝光条件")
            impressions_min = st.number_input(
                "最小曝光", min_value=0, value=0, step=100, key="add_impressions_min"
            )
            impressions_max = st.number_input(
                "最大曝光",
                min_value=-1,
                value=-1,
                step=100,
                key="add_impressions_max",
                help="-1表示不限制",
            )

        # 第二行：效率指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.write("ACOS条件")
            acos_min = st.number_input(
                "最小ACOS",
                min_value=0.0,
                value=0.0,
                step=0.05,
                format="%.2f",
                key="add_acos_min",
            )
            acos_max = st.number_input(
                "最大ACOS",
                min_value=0.0,
                value=0.0,
                step=0.05,
                format="%.2f",
                key="add_acos_max",
            )

        with col2:
            st.write("CVR条件 (转化率)")
            cvr_min = st.number_input(
                "最小CVR",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.3f",
                key="add_cvr_min",
            )
            cvr_max = st.number_input(
                "最大CVR",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.3f",
                key="add_cvr_max",
            )

        with col3:
            st.write("CTR条件 (点击率)")
            ctr_min = st.number_input(
                "最小CTR",
                min_value=0.0,
                value=0.0,
                step=0.001,
                format="%.4f",
                key="add_ctr_min",
            )
            ctr_max = st.number_input(
                "最大CTR",
                min_value=0.0,
                value=0.0,
                step=0.001,
                format="%.4f",
                key="add_ctr_max",
            )

        with col4:
            st.write("CPC条件 ($)")
            cpc_min = st.number_input(
                "最小CPC",
                min_value=0.0,
                value=0.0,
                step=0.1,
                format="%.2f",
                key="add_cpc_min",
            )
            cpc_max = st.number_input(
                "最大CPC",
                min_value=0.0,
                value=0.0,
                step=0.1,
                format="%.2f",
                key="add_cpc_max",
            )

        # 第三行：销售和特殊条件
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.write("销售额条件 ($)")
            sales_min = st.number_input(
                "最小销售额", min_value=0.0, value=0.0, step=10.0, key="add_sales_min"
            )
            sales_max = st.number_input(
                "最大销售额", min_value=0.0, value=0.0, step=10.0, key="add_sales_max"
            )

        with col2:
            st.write("ROAS条件")
            roas_min = st.number_input(
                "最小ROAS",
                min_value=0.0,
                value=0.0,
                step=0.5,
                format="%.2f",
                key="add_roas_min",
            )
            roas_max = st.number_input(
                "最大ROAS",
                min_value=0.0,
                value=0.0,
                step=0.5,
                format="%.2f",
                key="add_roas_max",
            )

        with col3:
            st.write("相关性条件")
            relevance = st.selectbox(
                "相关性等级",
                options=["", "strong", "weak", "irrelevant", "generic", "car"],
                format_func=lambda x: {
                    "": "不限制",
                    "strong": "强相关",
                    "weak": "弱相关",
                    "irrelevant": "不相关",
                    "generic": "太泛",
                    "car": "汽车相关",
                }.get(x, x),
                key="add_relevance",
            )

        with col4:
            st.write("特殊条件")
            is_own_variant = st.checkbox("自家变体ASIN", key="add_is_own_variant")
            is_competitor = st.checkbox("竞品ASIN", key="add_is_competitor")
            need_ai = st.checkbox("需要AI判断", key="add_need_ai")

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("保存规则", type="primary")
        with col2:
            cancelled = st.form_submit_button("取消")

        if cancelled:
            st.session_state.show_add_rule_form = False
            st.rerun()

        if submitted:
            if not rule_name or not action:
                st.error("请填写规则名称和建议动作")
            else:
                # 构建条件字典
                conditions = {}

                # 基础指标
                if spend_min > 0:
                    conditions["spend_min"] = spend_min
                if spend_max > 0:
                    conditions["spend_max"] = spend_max
                if orders_min > 0:
                    conditions["orders_min"] = orders_min
                if orders_max >= 0:
                    conditions["orders_max"] = orders_max
                if clicks_min > 0:
                    conditions["clicks_min"] = clicks_min
                if clicks_max >= 0:
                    conditions["clicks_max"] = clicks_max
                if impressions_min > 0:
                    conditions["impressions_min"] = impressions_min
                if impressions_max >= 0:
                    conditions["impressions_max"] = impressions_max

                # 效率指标
                if acos_min > 0:
                    conditions["acos_min"] = acos_min
                if acos_max > 0:
                    conditions["acos_max"] = acos_max
                if cvr_min > 0:
                    conditions["cvr_min"] = cvr_min
                if cvr_max > 0:
                    conditions["cvr_max"] = cvr_max
                if ctr_min > 0:
                    conditions["ctr_min"] = ctr_min
                if ctr_max > 0:
                    conditions["ctr_max"] = ctr_max
                if cpc_min > 0:
                    conditions["cpc_min"] = cpc_min
                if cpc_max > 0:
                    conditions["cpc_max"] = cpc_max

                # 销售指标
                if sales_min > 0:
                    conditions["sales_min"] = sales_min
                if sales_max > 0:
                    conditions["sales_max"] = sales_max
                if roas_min > 0:
                    conditions["roas_min"] = roas_min
                if roas_max > 0:
                    conditions["roas_max"] = roas_max

                # 其他条件
                if relevance:
                    conditions["relevance"] = relevance
                if is_own_variant:
                    conditions["is_own_variant"] = True
                if is_competitor:
                    conditions["is_competitor"] = True
                if need_ai:
                    conditions["need_ai_judgment"] = True

                if not conditions:
                    st.error("请至少设置一个条件")
                else:
                    try:
                        rule_product_id = None if is_global else product_id
                        new_id = db.create_rule(
                            name=rule_name,
                            conditions=conditions,
                            action=action,
                            rule_type=rule_type,
                            priority=priority,
                            product_id=rule_product_id,
                            enabled=enabled,
                        )
                        st.success(f"规则 '{rule_name}' 已创建 (ID: {new_id})")
                        st.session_state.show_add_rule_form = False
                        st.rerun()
                    except Exception as e:
                        safe_error("规则创建", e)


def render_edit_rule_form(db, rule: dict):
    """渲染编辑规则表单"""
    st.write(f"#### 编辑规则: {rule.get('name')}")

    rule_id = rule["id"]
    conditions = rule.get("conditions", {})

    with st.form(f"edit_rule_form_{rule_id}"):
        col1, col2 = st.columns(2)

        with col1:
            rule_name = st.text_input(
                "规则名称 *",
                value=rule.get("name", ""),
            )

            rule_type = st.selectbox(
                "规则类型 *",
                options=["keyword", "asin", "all"],
                index=["keyword", "asin", "all"].index(
                    rule.get("rule_type", "keyword")
                ),
                format_func=lambda x: {
                    "keyword": "关键词规则",
                    "asin": "ASIN规则",
                    "all": "通用规则",
                }.get(x, x),
            )

            priority = st.number_input(
                "优先级 *",
                min_value=1,
                max_value=1000,
                value=rule.get("priority", 50),
                step=1,
            )

        with col2:
            action = st.text_input(
                "建议动作 *",
                value=rule.get("action", ""),
            )

            enabled = st.checkbox(
                "启用",
                value=bool(rule.get("enabled", 1)),
            )

        st.write("**条件配置**")
        st.caption("设为0或留空表示不限制该条件，-1表示不设上限")

        # 第一行：基础指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.write("花费条件")
            spend_min = st.number_input(
                "最小花费 ($)",
                min_value=0.0,
                value=float(conditions.get("spend_min", 0)),
                step=1.0,
                key=f"edit_spend_min_{rule_id}",
            )
            spend_max = st.number_input(
                "最大花费 ($)",
                min_value=0.0,
                value=float(conditions.get("spend_max", 0)),
                step=1.0,
                key=f"edit_spend_max_{rule_id}",
            )

        with col2:
            st.write("订单条件")
            orders_min = st.number_input(
                "最小订单",
                min_value=0,
                value=int(conditions.get("orders_min", 0)),
                step=1,
                key=f"edit_orders_min_{rule_id}",
            )
            orders_max_val = conditions.get("orders_max", -1)
            if orders_max_val is None:
                orders_max_val = -1
            orders_max = st.number_input(
                "最大订单",
                min_value=-1,
                value=int(orders_max_val),
                step=1,
                key=f"edit_orders_max_{rule_id}",
                help="-1表示不限制",
            )

        with col3:
            st.write("点击条件")
            clicks_min = st.number_input(
                "最小点击",
                min_value=0,
                value=int(conditions.get("clicks_min", 0)),
                step=1,
                key=f"edit_clicks_min_{rule_id}",
            )
            clicks_max_val = conditions.get("clicks_max", -1)
            if clicks_max_val is None:
                clicks_max_val = -1
            clicks_max = st.number_input(
                "最大点击",
                min_value=-1,
                value=int(clicks_max_val),
                step=1,
                key=f"edit_clicks_max_{rule_id}",
                help="-1表示不限制",
            )

        with col4:
            st.write("曝光条件")
            impressions_min = st.number_input(
                "最小曝光",
                min_value=0,
                value=int(conditions.get("impressions_min", 0)),
                step=100,
                key=f"edit_impressions_min_{rule_id}",
            )
            impressions_max_val = conditions.get("impressions_max", -1)
            if impressions_max_val is None:
                impressions_max_val = -1
            impressions_max = st.number_input(
                "最大曝光",
                min_value=-1,
                value=int(impressions_max_val),
                step=100,
                key=f"edit_impressions_max_{rule_id}",
                help="-1表示不限制",
            )

        # 第二行：效率指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.write("ACOS条件")
            acos_min = st.number_input(
                "最小ACOS",
                min_value=0.0,
                value=float(conditions.get("acos_min", 0)),
                step=0.05,
                format="%.2f",
                key=f"edit_acos_min_{rule_id}",
            )
            acos_max = st.number_input(
                "最大ACOS",
                min_value=0.0,
                value=float(conditions.get("acos_max", 0)),
                step=0.05,
                format="%.2f",
                key=f"edit_acos_max_{rule_id}",
            )

        with col2:
            st.write("CVR条件 (转化率)")
            cvr_min = st.number_input(
                "最小CVR",
                min_value=0.0,
                value=float(conditions.get("cvr_min", 0)),
                step=0.01,
                format="%.3f",
                key=f"edit_cvr_min_{rule_id}",
            )
            cvr_max = st.number_input(
                "最大CVR",
                min_value=0.0,
                value=float(conditions.get("cvr_max", 0)),
                step=0.01,
                format="%.3f",
                key=f"edit_cvr_max_{rule_id}",
            )

        with col3:
            st.write("CTR条件 (点击率)")
            ctr_min = st.number_input(
                "最小CTR",
                min_value=0.0,
                value=float(conditions.get("ctr_min", 0)),
                step=0.001,
                format="%.4f",
                key=f"edit_ctr_min_{rule_id}",
            )
            ctr_max = st.number_input(
                "最大CTR",
                min_value=0.0,
                value=float(conditions.get("ctr_max", 0)),
                step=0.001,
                format="%.4f",
                key=f"edit_ctr_max_{rule_id}",
            )

        with col4:
            st.write("CPC条件 ($)")
            cpc_min = st.number_input(
                "最小CPC",
                min_value=0.0,
                value=float(conditions.get("cpc_min", 0)),
                step=0.1,
                format="%.2f",
                key=f"edit_cpc_min_{rule_id}",
            )
            cpc_max = st.number_input(
                "最大CPC",
                min_value=0.0,
                value=float(conditions.get("cpc_max", 0)),
                step=0.1,
                format="%.2f",
                key=f"edit_cpc_max_{rule_id}",
            )

        # 第三行：销售和特殊条件
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.write("销售额条件 ($)")
            sales_min = st.number_input(
                "最小销售额",
                min_value=0.0,
                value=float(conditions.get("sales_min", 0)),
                step=10.0,
                key=f"edit_sales_min_{rule_id}",
            )
            sales_max = st.number_input(
                "最大销售额",
                min_value=0.0,
                value=float(conditions.get("sales_max", 0)),
                step=10.0,
                key=f"edit_sales_max_{rule_id}",
            )

        with col2:
            st.write("ROAS条件")
            roas_min = st.number_input(
                "最小ROAS",
                min_value=0.0,
                value=float(conditions.get("roas_min", 0)),
                step=0.5,
                format="%.2f",
                key=f"edit_roas_min_{rule_id}",
            )
            roas_max = st.number_input(
                "最大ROAS",
                min_value=0.0,
                value=float(conditions.get("roas_max", 0)),
                step=0.5,
                format="%.2f",
                key=f"edit_roas_max_{rule_id}",
            )

        with col3:
            st.write("相关性条件")
            relevance_options = ["", "strong", "weak", "irrelevant", "generic", "car"]
            current_relevance = conditions.get("relevance", "")
            relevance_index = (
                relevance_options.index(current_relevance)
                if current_relevance in relevance_options
                else 0
            )
            relevance = st.selectbox(
                "相关性等级",
                options=relevance_options,
                index=relevance_index,
                format_func=lambda x: {
                    "": "不限制",
                    "strong": "强相关",
                    "weak": "弱相关",
                    "irrelevant": "不相关",
                    "generic": "太泛",
                    "car": "汽车相关",
                }.get(x, x),
                key=f"edit_relevance_{rule_id}",
            )

        with col4:
            st.write("特殊条件")
            is_own_variant = st.checkbox(
                "自家变体ASIN",
                value=conditions.get("is_own_variant", False),
                key=f"edit_is_own_variant_{rule_id}",
            )
            is_competitor = st.checkbox(
                "竞品ASIN",
                value=conditions.get("is_competitor", False),
                key=f"edit_is_competitor_{rule_id}",
            )
            need_ai = st.checkbox(
                "需要AI判断",
                value=conditions.get("need_ai_judgment", False),
                key=f"edit_need_ai_{rule_id}",
            )

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("保存修改", type="primary")
        with col2:
            cancelled = st.form_submit_button("取消")

        if cancelled:
            st.session_state.editing_rule_id = None
            st.rerun()

        if submitted:
            if not rule_name or not action:
                st.error("请填写规则名称和建议动作")
            else:
                # 构建新条件字典
                new_conditions = {}

                # 基础指标
                if spend_min > 0:
                    new_conditions["spend_min"] = spend_min
                if spend_max > 0:
                    new_conditions["spend_max"] = spend_max
                if orders_min > 0:
                    new_conditions["orders_min"] = orders_min
                if orders_max >= 0:
                    new_conditions["orders_max"] = orders_max
                if clicks_min > 0:
                    new_conditions["clicks_min"] = clicks_min
                if clicks_max >= 0:
                    new_conditions["clicks_max"] = clicks_max
                if impressions_min > 0:
                    new_conditions["impressions_min"] = impressions_min
                if impressions_max >= 0:
                    new_conditions["impressions_max"] = impressions_max

                # 效率指标
                if acos_min > 0:
                    new_conditions["acos_min"] = acos_min
                if acos_max > 0:
                    new_conditions["acos_max"] = acos_max
                if cvr_min > 0:
                    new_conditions["cvr_min"] = cvr_min
                if cvr_max > 0:
                    new_conditions["cvr_max"] = cvr_max
                if ctr_min > 0:
                    new_conditions["ctr_min"] = ctr_min
                if ctr_max > 0:
                    new_conditions["ctr_max"] = ctr_max
                if cpc_min > 0:
                    new_conditions["cpc_min"] = cpc_min
                if cpc_max > 0:
                    new_conditions["cpc_max"] = cpc_max

                # 销售指标
                if sales_min > 0:
                    new_conditions["sales_min"] = sales_min
                if sales_max > 0:
                    new_conditions["sales_max"] = sales_max
                if roas_min > 0:
                    new_conditions["roas_min"] = roas_min
                if roas_max > 0:
                    new_conditions["roas_max"] = roas_max

                # 其他条件
                if relevance:
                    new_conditions["relevance"] = relevance
                if is_own_variant:
                    new_conditions["is_own_variant"] = True
                if is_competitor:
                    new_conditions["is_competitor"] = True
                if need_ai:
                    new_conditions["need_ai_judgment"] = True

                if not new_conditions:
                    st.error("请至少设置一个条件")
                else:
                    try:
                        db.update_rule(
                            rule_id,
                            name=rule_name,
                            rule_type=rule_type,
                            conditions=new_conditions,
                            action=action,
                            priority=priority,
                            enabled=1 if enabled else 0,
                        )
                        st.success(f"规则 '{rule_name}' 已更新")
                        st.session_state.editing_rule_id = None
                        st.rerun()
                    except Exception as e:
                        safe_error("规则更新", e)


def format_conditions_summary(conditions: dict) -> str:
    """格式化条件摘要"""
    if not conditions:
        return "无条件"

    parts = []

    # 基础指标
    if "spend_min" in conditions:
        parts.append(f"花费>=${conditions['spend_min']}")
    if "spend_max" in conditions:
        parts.append(f"花费<=${conditions['spend_max']}")
    if "orders_min" in conditions:
        parts.append(f"订单>={conditions['orders_min']}")
    if "orders_max" in conditions:
        parts.append(f"订单<={conditions['orders_max']}")
    if "clicks_min" in conditions:
        parts.append(f"点击>={conditions['clicks_min']}")
    if "clicks_max" in conditions:
        parts.append(f"点击<={conditions['clicks_max']}")
    if "impressions_min" in conditions:
        parts.append(f"曝光>={conditions['impressions_min']}")
    if "impressions_max" in conditions:
        parts.append(f"曝光<={conditions['impressions_max']}")

    # 效率指标
    if "acos_min" in conditions:
        parts.append(f"ACOS>={conditions['acos_min']}")
    if "acos_max" in conditions:
        parts.append(f"ACOS<={conditions['acos_max']}")
    if "cvr_min" in conditions:
        parts.append(f"CVR>={conditions['cvr_min']}")
    if "cvr_max" in conditions:
        parts.append(f"CVR<={conditions['cvr_max']}")
    if "ctr_min" in conditions:
        parts.append(f"CTR>={conditions['ctr_min']}")
    if "ctr_max" in conditions:
        parts.append(f"CTR<={conditions['ctr_max']}")
    if "cpc_min" in conditions:
        parts.append(f"CPC>=${conditions['cpc_min']}")
    if "cpc_max" in conditions:
        parts.append(f"CPC<=${conditions['cpc_max']}")

    # 销售指标
    if "sales_min" in conditions:
        parts.append(f"销售>=${conditions['sales_min']}")
    if "sales_max" in conditions:
        parts.append(f"销售<=${conditions['sales_max']}")
    if "roas_min" in conditions:
        parts.append(f"ROAS>={conditions['roas_min']}")
    if "roas_max" in conditions:
        parts.append(f"ROAS<={conditions['roas_max']}")

    # 相关性
    if "relevance" in conditions:
        relevance_map = {
            "strong": "强相关",
            "weak": "弱相关",
            "irrelevant": "不相关",
            "generic": "太泛",
            "car": "汽车相关",
        }
        parts.append(
            f"相关性={relevance_map.get(conditions['relevance'], conditions['relevance'])}"
        )

    # 特殊条件
    if conditions.get("is_own_variant"):
        parts.append("自家变体")
    if conditions.get("is_competitor"):
        parts.append("竞品")
    if conditions.get("need_ai_judgment"):
        parts.append("需AI判断")

    return ", ".join(parts) if parts else "无条件"
