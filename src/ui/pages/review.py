"""
相关性审核页面
v2.0: 支持人工标记搜索词的相关性等级
"""

from html import escape

import streamlit as st

from src.ai.analyzer import AIAnalyzer
from src.config.logger import get_logger
from src.ui.pages.actions import ACTIONS_PAGE_CSS

logger = get_logger(__name__)


REVIEW_PAGE_CSS = """
<style>
.review-hero {
    padding: 1.6rem 1.8rem;
    border-radius: 26px;
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,255,0.96) 100%);
    border: 1px solid rgba(59, 91, 219, 0.10);
    box-shadow: 0 16px 38px rgba(15, 23, 42, 0.06);
    margin-bottom: 1.1rem;
}
</style>
"""


# 相关性等级显示映射
RELEVANCE_DISPLAY = {
    "strong_core": "强相关核心词",
    "strong_longtail": "强相关长尾词",
    "weak": "弱相关",
    "generic": "太泛",
    "irrelevant": "不相关",
    "need_observe": "待观察",
    "pending": "待定",
}


# 相关性选项定义
RELEVANCE_OPTIONS = [
    ("strong_core", "强相关核心词", "产品核心关键词，优先手动精准"),
    ("strong_longtail", "强相关长尾词", "长尾但相关，可考虑手动"),
    ("weak", "弱相关", "关联度低，否定词组"),
    ("generic", "太泛", "泛词不精准，否定精准"),
    ("irrelevant", "不相关", "完全无关，否定词组"),
    ("need_observe", "待观察", "样本不足，继续观察"),
]

# 范围选项定义
SCOPE_OPTIONS = [
    ("local", "Local (仅当前活动)"),
    ("global", "Global (全局同步)"),
]


# ASIN竞争力评估选项（与关键词相关性分离）
COMPETITION_OPTIONS = [
    ("can_compete", "可竞争", "有竞争优势，手动商品定位"),
    ("cannot_compete", "不可竞争", "无竞争力，否定"),
    ("need_observe", "待观察", "样本不足，继续观察"),
]

COMPETITION_DISPLAY = {
    "can_compete": "可竞争",
    "cannot_compete": "不可竞争",
    "need_observe": "待观察",
    "pending": "待评估",
}


def _build_review_dashboard_state(
    pending_count: dict[str, int], review_mode: str
) -> dict[str, str | list[str]]:
    """构建审核页概览文案。"""
    mode_label = "批量模式" if review_mode == "batch" else "单条模式"
    total = pending_count.get("total", 0)
    keywords = pending_count.get("keywords", 0)
    asins = pending_count.get("asins", 0)
    return {
        "eyebrow": "审核面板",
        "title": "相关性审核",
        "description": "把待审核项按词类型和花费收窄后逐条处理，避免在批量模式里误伤本该细看的词。",
        "chips": [
            f"待审核 {total} 项",
            f"关键词 {keywords} 项",
            f"ASIN {asins} 项",
            f"当前模式：{mode_label}",
        ],
    }


def _build_review_empty_state() -> dict[str, str]:
    """构建审核页完成态文案。"""
    return {
        "title": "所有词都已审核完成",
        "description": "这批数据已经完成人工判定，可以直接回到首页看待处理项，或进入操作清单执行。",
        "badge": "审核闭环已完成",
    }


def render_review():
    """渲染相关性审核页面"""
    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    if not db:
        st.error("数据库未初始化")
        return

    if not product_id:
        st.warning("请先选择产品")
        return

    if "review_mode" not in st.session_state:
        st.session_state.review_mode = "single"

    # 获取待审核统计
    pending_count = db.get_pending_reviews_count(product_id)
    state = _build_review_dashboard_state(pending_count, st.session_state.review_mode)
    chips_html = "".join(
        f'<div class="review-hero__chip">{escape(chip)}</div>' for chip in state["chips"]
    )

    st.markdown(ACTIONS_PAGE_CSS + REVIEW_PAGE_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <section class="review-hero">
            <div class="review-hero__eyebrow">{escape(state["eyebrow"])}</div>
            <h1>{escape(state["title"])}</h1>
            <p>{escape(state["description"])}</p>
            <div class="review-hero__chips">{chips_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # 顶部统计卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("待审核总数", pending_count.get("total", 0))
    with col2:
        st.metric("关键词", pending_count.get("keywords", 0))
    with col3:
        st.metric("ASIN", pending_count.get("asins", 0))
    with col4:
        # 模式切换
        mode_label = (
            "批量模式" if st.session_state.review_mode == "single" else "单条模式"
        )
        if st.button(f"切换到{mode_label}", width="stretch"):
            st.session_state.review_mode = (
                "batch" if st.session_state.review_mode == "single" else "single"
            )
            st.session_state.batch_selected = set()  # 清空批量选择
            st.rerun()

    st.divider()

    # 检查是否有待审核项
    if pending_count.get("total", 0) == 0:
        empty_state = _build_review_empty_state()
        st.markdown(
            f"""
            <section class="review-completion">
                <div class="review-completion__badge">{escape(empty_state["badge"])}</div>
                <h3>{escape(empty_state["title"])}</h3>
                <p>{escape(empty_state["description"])}</p>
            </section>
            """,
            unsafe_allow_html=True,
        )
        return

    # 获取待审核列表（移除100条限制，支持分页）
    pending_list = db.get_pending_reviews_list(product_id, limit=500)

    if not pending_list:
        st.info("暂无待审核的词")
        return

    # ========== T51: 筛选搜索功能 ==========
    with st.expander("筛选与搜索", expanded=False):
        st.markdown(
            '<p class="review-section-note">先用词类型和花费范围缩小集合，再用搜索词精准定位，能大幅减少批量审核时误点的概率。</p>',
            unsafe_allow_html=True,
        )
        filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])

        with filter_col1:
            # T51a: 词类型筛选
            term_type_filter = st.selectbox(
                "词类型",
                options=["全部", "关键词", "ASIN"],
                index=0,
                key="review_term_type_filter",
            )

        with filter_col2:
            # T51a: 花费筛选
            spend_filter = st.selectbox(
                "花费范围",
                options=["全部", "高花费(>$10)", "中花费($5-10)", "低花费(<$5)"],
                index=0,
                key="review_spend_filter",
            )

        with filter_col3:
            # T51b: 搜索框
            search_query = st.text_input(
                "搜索词",
                value="",
                placeholder="输入关键词搜索...",
                key="review_search_query",
            )

    # T51c: 应用筛选逻辑
    filtered_list = pending_list.copy()

    # 词类型筛选
    if term_type_filter == "关键词":
        filtered_list = [
            item for item in filtered_list if item.get("term_type") == "keyword"
        ]
    elif term_type_filter == "ASIN":
        filtered_list = [
            item for item in filtered_list if item.get("term_type") == "asin"
        ]

    # 花费筛选
    if spend_filter == "高花费(>$10)":
        filtered_list = [
            item for item in filtered_list if (item.get("total_spend") or 0) > 10
        ]
    elif spend_filter == "中花费($5-10)":
        filtered_list = [
            item for item in filtered_list if 5 <= (item.get("total_spend") or 0) <= 10
        ]
    elif spend_filter == "低花费(<$5)":
        filtered_list = [
            item for item in filtered_list if (item.get("total_spend") or 0) < 5
        ]

    # 搜索筛选
    if search_query:
        search_lower = search_query.lower()
        filtered_list = [
            item
            for item in filtered_list
            if search_lower in item.get("term", "").lower()
        ]

    # T51d: 显示筛选结果
    if len(filtered_list) != len(pending_list):
        st.caption(f"筛选结果: {len(filtered_list)}/{len(pending_list)} 条")

    if not filtered_list:
        st.warning("没有符合筛选条件的词")
        return

    pending_list = filtered_list
    # ========== 筛选搜索功能结束 ==========

    # 初始化session state
    if "review_current_index" not in st.session_state:
        st.session_state.review_current_index = 0
    if "batch_selected" not in st.session_state:
        st.session_state.batch_selected = set()

    # 确保索引有效
    if st.session_state.review_current_index >= len(pending_list):
        st.session_state.review_current_index = 0

    # 根据模式渲染不同界面
    if st.session_state.review_mode == "batch":
        _render_batch_mode(db, product_id, pending_list)
    else:
        _render_single_mode(db, product_id, pending_list)


def _get_page_items(pending_list: list, page_key: str = "review_page"):
    """分页辅助：返回当前页的起止索引和每页大小"""
    if f"{page_key}_size" not in st.session_state:
        st.session_state[f"{page_key}_size"] = 20
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    page_size = st.session_state[f"{page_key}_size"]
    page = st.session_state[page_key]
    total = len(pending_list)
    total_pages = max(1, (total + page_size - 1) // page_size)

    # 防止越界
    if page >= total_pages:
        page = total_pages - 1
        st.session_state[page_key] = page

    start = page * page_size
    end = min(start + page_size, total)
    return start, end, page, total_pages, page_size


def _render_pagination(
    total: int, page: int, total_pages: int, page_key: str = "review_page"
):
    """渲染分页控件"""
    col_prev, col_info, col_next, col_size = st.columns([1, 2, 1, 1])

    with col_prev:
        if st.button("上一页", disabled=page <= 0, key=f"{page_key}_prev"):
            st.session_state[page_key] = page - 1
            st.rerun()
    with col_info:
        st.caption(f"第 {page + 1}/{total_pages} 页 (共 {total} 条)")
    with col_next:
        if st.button(
            "下一页", disabled=page >= total_pages - 1, key=f"{page_key}_next"
        ):
            st.session_state[page_key] = page + 1
            st.rerun()
    with col_size:
        new_size = st.selectbox(
            "每页",
            [10, 20, 50],
            index=[10, 20, 50].index(st.session_state.get(f"{page_key}_size", 20)),
            key=f"{page_key}_size_sel",
            label_visibility="collapsed",
        )
        if new_size != st.session_state.get(f"{page_key}_size", 20):
            st.session_state[f"{page_key}_size"] = new_size
            st.session_state[page_key] = 0
            st.rerun()


def _render_single_mode(db, product_id: int, pending_list: list):
    """渲染单条审核模式"""
    # 左右分栏布局
    col_list, col_form = st.columns([1, 2])

    with col_list:
        st.subheader(f"待审核列表 ({len(pending_list)})")

        start, end, page, total_pages, page_size = _get_page_items(
            pending_list, "single_page"
        )

        # 显示当前页的列表项
        for idx in range(start, end):
            item = pending_list[idx]
            term = item.get("term", "")
            term_type = item.get("term_type", "keyword")
            term_type_label = "[K]" if term_type == "keyword" else "[A]"

            # 高亮当前选中项
            is_selected = idx == st.session_state.review_current_index
            button_type = "primary" if is_selected else "secondary"

            if st.button(
                f"{term_type_label} {term[:30]}{'...' if len(term) > 30 else ''}",
                key=f"term_btn_{idx}",
                width="stretch",
                type=button_type,
            ):
                st.session_state.review_current_index = idx
                st.rerun()

        _render_pagination(len(pending_list), page, total_pages, "single_page")

    with col_form:
        # 当前审核项
        current_item = pending_list[st.session_state.review_current_index]
        _render_review_form(db, product_id, current_item, pending_list)


def _render_batch_mode(db, product_id: int, pending_list: list):
    """渲染批量审核模式（T50a-d）"""
    col_list, col_form = st.columns([1, 2])

    with col_list:
        st.subheader(f"批量选择 ({len(st.session_state.batch_selected)}选中)")

        start, end, page, total_pages, page_size = _get_page_items(
            pending_list, "batch_page"
        )

        # 全选/取消全选（当前页）
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            if st.button("全选本页", width="stretch"):
                st.session_state.batch_selected = st.session_state.batch_selected | set(
                    range(start, end)
                )
                st.rerun()
        with col_sel2:
            if st.button("取消全选", width="stretch"):
                st.session_state.batch_selected = set()
                st.rerun()

        st.divider()

        # 显示当前页的checkbox列表
        for idx in range(start, end):
            item = pending_list[idx]
            term = item.get("term", "")
            term_type = item.get("term_type", "keyword")
            term_type_label = "[K]" if term_type == "keyword" else "[A]"

            is_checked = idx in st.session_state.batch_selected
            if st.checkbox(
                f"{term_type_label} {term[:25]}{'...' if len(term) > 25 else ''}",
                key=f"batch_cb_{idx}",
                value=is_checked,
            ):
                st.session_state.batch_selected.add(idx)
            else:
                st.session_state.batch_selected.discard(idx)

        _render_pagination(len(pending_list), page, total_pages, "batch_page")

        if len(pending_list) > 20:
            st.caption(f"还有 {len(pending_list) - 20} 条未显示...")

    with col_form:
        _render_batch_form(db, product_id, pending_list)


def _render_batch_form(db, product_id: int, pending_list: list):
    """渲染批量审核表单（T50b-d）"""
    selected_count = len(st.session_state.batch_selected)

    st.subheader(f"批量审核 ({selected_count} 项)")

    if selected_count == 0:
        st.info("请先在左侧选择要批量审核的词")
        return

    # 显示选中项预览
    with st.expander(f"已选中 {selected_count} 项", expanded=False):
        for idx in sorted(st.session_state.batch_selected):
            if idx < len(pending_list):
                item = pending_list[idx]
                term = item.get("term", "")
                term_type = "[K]" if item.get("term_type") == "keyword" else "[A]"
                st.text(f"{term_type} {term[:40]}")

    st.divider()

    # 检查选中项的类型分布
    keyword_count = 0
    asin_count = 0
    for idx in st.session_state.batch_selected:
        if idx < len(pending_list):
            item = pending_list[idx]
            if item.get("term_type") == "asin":
                asin_count += 1
            else:
                keyword_count += 1

    # 显示类型分布
    st.caption(f"选中: {keyword_count} 个关键词, {asin_count} 个ASIN")

    # 批量审核表单
    with st.form(key="batch_review_form"):
        # 根据选中类型显示不同选项
        selected_relevance = None
        selected_competition = None

        if keyword_count > 0 and asin_count > 0:
            # 混合选择：显示警告并分别处理
            st.warning("选中了不同类型的项，将分别应用：关键词→相关性，ASIN→竞争力")

            # 关键词相关性
            st.markdown("**关键词相关性标记**")
            relevance_labels = [opt[1] for opt in RELEVANCE_OPTIONS]
            relevance_values = [opt[0] for opt in RELEVANCE_OPTIONS]
            selected_relevance_label = st.radio(
                "选择相关性等级",
                options=relevance_labels,
                index=0,
                horizontal=True,
                key="batch_relevance",
                label_visibility="collapsed",
            )
            selected_relevance = relevance_values[
                relevance_labels.index(selected_relevance_label)
            ]
            st.caption(
                next(
                    (
                        opt[2]
                        for opt in RELEVANCE_OPTIONS
                        if opt[0] == selected_relevance
                    ),
                    "",
                )
            )

            st.divider()

            # ASIN竞争力
            st.markdown("**ASIN竞争力评估**")
            competition_labels = [opt[1] for opt in COMPETITION_OPTIONS]
            competition_values = [opt[0] for opt in COMPETITION_OPTIONS]
            selected_competition_label = st.radio(
                "选择竞争力等级",
                options=competition_labels,
                index=0,
                horizontal=True,
                key="batch_competition",
                label_visibility="collapsed",
            )
            selected_competition = competition_values[
                competition_labels.index(selected_competition_label)
            ]
            st.caption(
                next(
                    (
                        opt[2]
                        for opt in COMPETITION_OPTIONS
                        if opt[0] == selected_competition
                    ),
                    "",
                )
            )

        elif asin_count > 0:
            # 仅ASIN：显示竞争力选项
            st.markdown("**统一竞争力评估** (ASIN)")
            competition_labels = [opt[1] for opt in COMPETITION_OPTIONS]
            competition_values = [opt[0] for opt in COMPETITION_OPTIONS]
            selected_competition_label = st.radio(
                "选择竞争力等级",
                options=competition_labels,
                index=0,
                horizontal=True,
                label_visibility="collapsed",
            )
            selected_competition = competition_values[
                competition_labels.index(selected_competition_label)
            ]
            st.caption(
                next(
                    (
                        opt[2]
                        for opt in COMPETITION_OPTIONS
                        if opt[0] == selected_competition
                    ),
                    "",
                )
            )

        else:
            # 仅关键词：显示相关性选项
            st.markdown("**统一相关性标记**")
            relevance_labels = [opt[1] for opt in RELEVANCE_OPTIONS]
            relevance_values = [opt[0] for opt in RELEVANCE_OPTIONS]
            selected_relevance_label = st.radio(
                "选择相关性等级",
                options=relevance_labels,
                index=0,
                horizontal=True,
                label_visibility="collapsed",
            )
            selected_relevance = relevance_values[
                relevance_labels.index(selected_relevance_label)
            ]
            st.caption(
                next(
                    (
                        opt[2]
                        for opt in RELEVANCE_OPTIONS
                        if opt[0] == selected_relevance
                    ),
                    "",
                )
            )

        st.divider()

        # 范围选择
        st.markdown("**统一应用范围**")
        scope_labels = [opt[1] for opt in SCOPE_OPTIONS]
        scope_values = [opt[0] for opt in SCOPE_OPTIONS]

        selected_scope_label = st.radio(
            "选择范围",
            options=scope_labels,
            index=0,
            horizontal=True,
            label_visibility="collapsed",
        )
        selected_scope = scope_values[scope_labels.index(selected_scope_label)]

        st.divider()

        # 备注
        batch_notes = st.text_area(
            "统一备注（可选）",
            value="",
            placeholder="批量审核备注...",
            height=60,
        )

        # 提交按钮
        submit_clicked = st.form_submit_button(
            f"批量保存 ({selected_count} 项)",
            type="primary",
        )

    # 处理批量提交
    if submit_clicked:
        success_count = 0
        fail_count = 0
        failed_terms = []

        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, idx in enumerate(sorted(st.session_state.batch_selected)):
            if idx < len(pending_list):
                item = pending_list[idx]
                term = item.get("term", "")
                term_type = item.get("term_type", "keyword")

                try:
                    if term_type == "asin":
                        # ASIN: 保存竞争力评估
                        db.upsert_manual_review(
                            product_id=product_id,
                            term=term,
                            term_type=term_type,
                            competition_level=selected_competition,
                            competition_notes=batch_notes if batch_notes else None,
                            scope=selected_scope,
                            reviewed=True,
                        )
                    else:
                        # 关键词: 保存相关性标记
                        db.upsert_manual_review(
                            product_id=product_id,
                            term=term,
                            term_type=term_type,
                            relevance=selected_relevance,
                            relevance_notes=batch_notes if batch_notes else None,
                            scope=selected_scope,
                            reviewed=True,
                        )
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    failed_terms.append(term)
                    logger.error(f"批量审核保存失败 [{term}]: {e}")

                # 更新进度
                progress = (i + 1) / selected_count
                progress_bar.progress(progress)
                status_text.text(f"处理中: {i + 1}/{selected_count}")

        # 显示结果
        progress_bar.empty()
        status_text.empty()

        if success_count > 0:
            st.success(f"成功保存 {success_count} 项")

        if fail_count > 0:
            st.error(f"失败 {fail_count} 项: {', '.join(failed_terms[:5])}")

        # 清空选择并刷新
        st.session_state.batch_selected = set()
        st.rerun()


def _request_ai_suggestion(db, product_id: int, term: str, item: dict):
    """请求AI相关性建议（T53）"""
    try:
        # 获取产品信息
        product = db.get_product(product_id)
        if not product:
            st.error("无法获取产品信息")
            return

        # 构建产品上下文
        product_context = {
            "name": product.get("name", ""),
            "category": product.get("category", ""),
            "core_keywords": db.get_keywords_by_category(product_id, "core") or [],
        }

        # 构建表现数据
        performance_data = {
            "clicks": item.get("total_clicks", 0),
            "spend": item.get("total_spend", 0),
            "orders": item.get("total_orders", 0),
        }

        # 调用AI分析器
        with st.spinner("AI分析中..."):
            analyzer = AIAnalyzer()
            suggestion = analyzer.suggest_relevance(
                term=term,
                product_context=product_context,
                performance_data=performance_data,
            )

        # 保存到session state
        ai_suggestion_key = f"ai_suggestion_{term}"
        st.session_state[ai_suggestion_key] = {
            "relevance": suggestion.suggested_relevance,
            "confidence": suggestion.confidence,
            "reasoning": suggestion.reasoning,
        }

        # 同时保存到数据库（用于后续参考）
        try:
            db.update_manual_review_ai_suggestion(
                product_id=product_id,
                term=term,
                ai_suggestion=suggestion.suggested_relevance,
                ai_confidence=suggestion.confidence,
            )
        except Exception as e:
            logger.warning(f"保存AI建议到数据库失败: {e}")

        st.rerun()

    except Exception as e:
        logger.error(f"获取AI建议失败: {e}")
        st.error(f"获取AI建议失败: {e}")


def _render_review_form(db, product_id: int, item: dict, pending_list: list):
    """渲染单条审核表单"""
    term = item.get("term", "")
    term_type = item.get("term_type", "keyword")

    st.subheader(f"审核: {term}")

    # 数据概览（如果有）
    with st.expander("数据概览", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("花费", f"${item.get('total_spend', 0):.2f}")
        with col2:
            st.metric("点击", item.get("total_clicks", 0))
        with col3:
            st.metric("订单", item.get("total_orders", 0))

    # ========== T53: AI建议功能 ==========
    # 检查session state中是否有AI建议
    ai_suggestion_key = f"ai_suggestion_{term}"
    ai_suggestion = st.session_state.get(ai_suggestion_key)

    # 也检查item中的预存建议
    if not ai_suggestion and item.get("ai_suggestion"):
        ai_suggestion = {
            "relevance": item.get("ai_suggestion"),
            "confidence": item.get("ai_confidence", 0),
            "reasoning": item.get("ai_reasoning", ""),
        }

    # AI建议展示区
    with st.container():
        col_ai_btn, col_ai_result = st.columns([1, 3])

        with col_ai_btn:
            if st.button("获取AI建议", key=f"ai_btn_{term}"):
                _request_ai_suggestion(db, product_id, term, item)

        with col_ai_result:
            if ai_suggestion:
                relevance_label = RELEVANCE_DISPLAY.get(
                    ai_suggestion.get("relevance", "pending"),
                    ai_suggestion.get("relevance", "待定"),
                )
                confidence = ai_suggestion.get("confidence", 0)
                reasoning = ai_suggestion.get("reasoning", "")

                # 根据置信度显示不同颜色
                if confidence >= 0.8:
                    st.success(
                        f"AI建议: **{relevance_label}** (置信度: {confidence:.0%})"
                    )
                elif confidence >= 0.5:
                    st.info(f"AI建议: **{relevance_label}** (置信度: {confidence:.0%})")
                else:
                    st.warning(
                        f"AI建议: **{relevance_label}** (置信度: {confidence:.0%})"
                    )

                if reasoning:
                    st.caption(f"理由: {reasoning}")
            else:
                st.caption("点击按钮获取AI相关性建议")
    # ========== AI建议功能结束 ==========

    st.divider()

    # 审核表单
    with st.form(key=f"review_form_{term}"):
        # 根据类型显示不同的审核选项
        if term_type == "asin":
            # ========== ASIN: 显示竞争力评估 ==========
            st.markdown("**竞争力评估** (ASIN专用)")

            competition_labels = [f"{opt[1]}" for opt in COMPETITION_OPTIONS]
            competition_values = [opt[0] for opt in COMPETITION_OPTIONS]

            # 获取当前值的索引
            current_competition = item.get("competition_level")
            try:
                current_idx = (
                    competition_values.index(current_competition)
                    if current_competition
                    else 0
                )
            except ValueError:
                current_idx = 0

            selected_competition_label = st.radio(
                "选择竞争力等级",
                options=competition_labels,
                index=current_idx,
                horizontal=True,
                label_visibility="collapsed",
            )
            selected_competition = competition_values[
                competition_labels.index(selected_competition_label)
            ]

            # 显示竞争力说明
            competition_desc = next(
                (
                    opt[2]
                    for opt in COMPETITION_OPTIONS
                    if opt[0] == selected_competition
                ),
                "",
            )
            st.caption(f"{competition_desc}")

            # ASIN不需要相关性标记，设置为None
            selected_relevance = None
        else:
            # ========== 关键词: 显示相关性标记 ==========
            st.markdown("**相关性标记**")

            relevance_labels = [f"{opt[1]}" for opt in RELEVANCE_OPTIONS]
            relevance_values = [opt[0] for opt in RELEVANCE_OPTIONS]

            # 获取当前值的索引
            current_relevance = item.get("relevance")
            try:
                current_idx = (
                    relevance_values.index(current_relevance)
                    if current_relevance
                    else 0
                )
            except ValueError:
                current_idx = 0

            selected_relevance_label = st.radio(
                "选择相关性等级",
                options=relevance_labels,
                index=current_idx,
                horizontal=True,
                label_visibility="collapsed",
            )
            selected_relevance = relevance_values[
                relevance_labels.index(selected_relevance_label)
            ]

            # 显示相关性说明
            relevance_desc = next(
                (opt[2] for opt in RELEVANCE_OPTIONS if opt[0] == selected_relevance),
                "",
            )
            st.caption(f"{relevance_desc}")

            # 关键词不需要竞争力评估
            selected_competition = None

        st.divider()

        # 范围选择
        st.markdown("**应用范围**")
        scope_labels = [opt[1] for opt in SCOPE_OPTIONS]
        scope_values = [opt[0] for opt in SCOPE_OPTIONS]

        current_scope = item.get("scope", "local")
        try:
            scope_idx = scope_values.index(current_scope)
        except ValueError:
            scope_idx = 0

        selected_scope_label = st.radio(
            "选择范围",
            options=scope_labels,
            index=scope_idx,
            horizontal=True,
            label_visibility="collapsed",
        )
        selected_scope = scope_values[scope_labels.index(selected_scope_label)]

        st.divider()

        # 备注
        notes = st.text_area(
            "备注（可选）",
            value=item.get("relevance_notes", "") or "",
            placeholder="输入相关性判断理由...",
            height=80,
        )

        # 按钮行
        col_skip, col_save, col_save_next = st.columns(3)

        with col_skip:
            skip_clicked = st.form_submit_button("跳过")

        with col_save:
            save_clicked = st.form_submit_button("保存")

        with col_save_next:
            save_next_clicked = st.form_submit_button(
                "保存并下一个",
                type="primary",
            )

    # 处理表单提交
    if skip_clicked:
        _go_to_next(pending_list)

    if save_clicked or save_next_clicked:
        # 保存到数据库
        try:
            if term_type == "asin":
                # ASIN: 保存竞争力评估
                db.upsert_manual_review(
                    product_id=product_id,
                    term=term,
                    term_type=term_type,
                    competition_level=selected_competition,
                    competition_notes=notes if notes else None,
                    scope=selected_scope,
                    reviewed=True,
                )
                st.success(f"已保存 ASIN '{term}' 的竞争力评估")
            else:
                # 关键词: 保存相关性标记
                db.upsert_manual_review(
                    product_id=product_id,
                    term=term,
                    term_type=term_type,
                    relevance=selected_relevance,
                    relevance_notes=notes if notes else None,
                    scope=selected_scope,
                    reviewed=True,
                )
                st.success(f"已保存 '{term}' 的相关性标记")

            if save_next_clicked:
                _go_to_next(pending_list)
            else:
                st.rerun()

        except Exception as e:
            logger.error(f"保存审核失败: {e}")
            st.error(f"保存失败: {e}")


def _go_to_next(pending_list: list):
    """跳转到下一个待审核项"""
    current_idx = st.session_state.review_current_index
    if current_idx < len(pending_list) - 1:
        st.session_state.review_current_index = current_idx + 1
    else:
        st.session_state.review_current_index = 0
    st.rerun()
