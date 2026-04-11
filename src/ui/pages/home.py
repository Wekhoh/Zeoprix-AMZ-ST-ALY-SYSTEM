"""
首页/仪表盘
展示关键指标和快速入口
"""

from html import escape

import streamlit as st

from src.analysis.truth_replay import (
    get_truth_first_overview_distribution,
    get_truth_first_pending_stats,
)
from src.config.logger import get_logger
from src.rules.engine import analyze_search_terms

logger = get_logger(__name__)


# 缓存时间（秒）
CACHE_TTL = 60

HOME_PAGE_CSS = """
<style>
.dashboard-hero {
    padding: 1.35rem 1.5rem;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 22px;
    background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(239,246,255,0.92) 100%);
    box-shadow: 0 16px 40px rgba(15, 23, 42, 0.05);
    margin-bottom: 1.35rem;
}
.dashboard-hero__eyebrow {
    display: inline-flex;
    padding: 0.32rem 0.68rem;
    border-radius: 999px;
    background: rgba(37, 99, 235, 0.08);
    color: #2563EB;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.dashboard-hero h1 {
    margin: 0.85rem 0 0.35rem 0 !important;
}
.dashboard-hero p {
    margin: 0;
    color: #64748B;
    font-size: 0.98rem;
    line-height: 1.6;
}
.dashboard-hero__chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: 1rem;
}
.dashboard-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.56rem 0.8rem;
    border-radius: 999px;
    font-size: 0.84rem;
    font-weight: 600;
    border: 1px solid transparent;
}
.dashboard-chip--neutral {
    background: rgba(15, 23, 42, 0.04);
    color: #334155;
    border-color: rgba(148, 163, 184, 0.18);
}
.dashboard-chip--warning {
    background: rgba(245, 158, 11, 0.12);
    color: #B45309;
    border-color: rgba(245, 158, 11, 0.18);
}
.dashboard-chip--success {
    background: rgba(16, 185, 129, 0.12);
    color: #047857;
    border-color: rgba(16, 185, 129, 0.16);
}
.dashboard-section-shell {
    padding: 1.15rem 1.2rem;
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 14px 36px rgba(15, 23, 42, 0.04);
}
.dashboard-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1rem;
    margin-bottom: 1.4rem;
}
.dashboard-kpi-card {
    padding: 1.2rem 1.25rem;
    border-radius: 20px;
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.95) 100%);
    border: 1px solid rgba(226, 232, 240, 0.9);
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
}
.dashboard-kpi-card span {
    display: block;
    color: #64748B;
    font-size: 0.88rem;
    font-weight: 600;
    margin-bottom: 0.55rem;
}
.dashboard-kpi-card strong {
    color: #1E3A8A;
    font-size: 2.05rem;
    line-height: 1.05;
    letter-spacing: -0.03em;
}
.pending-notice-stack {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}
.pending-notice-card {
    border-radius: 18px;
    padding: 0.95rem 1rem;
    border: 1px solid rgba(226, 232, 240, 0.9);
    background: rgba(248, 250, 252, 0.9);
}
.pending-notice-card small {
    display: block;
    color: #94A3B8;
    font-size: 0.73rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.35rem;
}
.pending-notice-card strong {
    display: block;
    color: #0F172A;
    font-size: 1rem;
    line-height: 1.45;
}
.pending-notice-card--warning {
    background: linear-gradient(180deg, rgba(255,251,235,0.92) 0%, rgba(255,247,214,0.95) 100%);
    border-color: rgba(245, 158, 11, 0.18);
}
.pending-notice-card--success {
    background: linear-gradient(180deg, rgba(236,253,245,0.92) 0%, rgba(220,252,231,0.95) 100%);
    border-color: rgba(16, 185, 129, 0.18);
}
.pending-notice-card--info {
    background: linear-gradient(180deg, rgba(239,246,255,0.92) 0%, rgba(219,234,254,0.95) 100%);
    border-color: rgba(59, 130, 246, 0.18);
}
.quick-action-caption {
    margin: 0 0 1rem 0;
    color: #64748B;
    font-size: 0.92rem;
    line-height: 1.55;
}
.workspace-summary-shell {
    padding: 1rem 1.05rem;
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
    margin-bottom: 1.15rem;
}
.workspace-summary-shell h3 {
    margin: 0 0 0.35rem 0 !important;
    font-size: 1rem;
}
.workspace-summary-shell p {
    margin: 0 0 0.85rem 0;
    color: #64748B;
    font-size: 0.9rem;
    line-height: 1.55;
}
.workbench-status-shell {
    padding: 1.05rem 1.1rem;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
    margin-bottom: 1.2rem;
}
.workbench-status-shell h3 {
    margin: 0 0 0.35rem 0 !important;
    font-size: 1rem;
}
.workbench-status-shell p {
    margin: 0 0 0.9rem 0;
    color: #64748B;
    font-size: 0.9rem;
    line-height: 1.55;
}
.workbench-status-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.8rem;
}
.workbench-status-card {
    padding: 0.95rem 1rem;
    border-radius: 18px;
    border: 1px solid rgba(226, 232, 240, 0.9);
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.96) 100%);
}
.workbench-status-card small {
    display: block;
    color: #94A3B8;
    font-size: 0.73rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.45rem;
}
.workbench-status-card strong {
    display: block;
    color: #0F172A;
    font-size: 1.02rem;
    line-height: 1.35;
    margin-bottom: 0.28rem;
}
.workbench-status-card span {
    color: #64748B;
    font-size: 0.85rem;
    line-height: 1.55;
}
.workbench-next-actions {
    margin-top: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
}
.workbench-next-action {
    border-radius: 16px;
    padding: 0.8rem 0.95rem;
    background: rgba(248,250,252,0.92);
    border: 1px solid rgba(226,232,240,0.88);
}
.workbench-next-action strong {
    display: block;
    color: #0F172A;
    font-size: 0.93rem;
    margin-bottom: 0.25rem;
}
.workbench-next-action span {
    color: #64748B;
    font-size: 0.84rem;
    line-height: 1.5;
}
@media (max-width: 1100px) {
    .dashboard-kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .workbench-status-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
</style>
"""


def _build_overview_chart_rows(chart_data: dict[str, int]) -> list[dict[str, float | int | str]]:
    """将首页概览图数据整理为稳定排序的渲染行。"""
    sorted_items = sorted(chart_data.items(), key=lambda item: item[1], reverse=True)
    max_value = max((value for _, value in sorted_items), default=1)

    rows: list[dict[str, float | int | str]] = []
    for label, value in sorted_items:
        ratio = (value / max_value * 100) if max_value else 0
        rows.append(
            {
                "label": label,
                "value": value,
                "ratio": ratio,
            }
        )
    return rows



def _render_overview_chart(chart_data: dict[str, int]) -> None:
    """使用轻量 HTML 渲染概览分布，避免 Vega/Altair 控制台 warning。"""
    rows = _build_overview_chart_rows(chart_data)
    if not rows:
        return

    chart_rows = "".join(
        f"""
        <div style="display:flex;align-items:center;gap:0.85rem;margin:0 0 0.95rem 0;">
            <div style="flex:0 0 180px;font-size:0.94rem;font-weight:600;color:#1E293B;line-height:1.35;">{escape(str(row['label']))}</div>
            <div style="flex:1;min-width:180px;background:#E2E8F0;border-radius:999px;height:14px;overflow:hidden;">
                <div style="height:14px;border-radius:999px;background:linear-gradient(90deg,#2563EB 0%,#60A5FA 100%);width:{row['ratio']:.2f}%;"></div>
            </div>
            <div style="flex:0 0 54px;text-align:right;font-size:0.93rem;font-weight:700;color:#2563EB;">{row['value']}</div>
        </div>
        """
        for row in rows
    )

    st.markdown(
        f"""
        <div style="padding:1.1rem 1.1rem 0.35rem 1.1rem;border:1px solid rgba(37,99,235,0.08);border-radius:18px;background:linear-gradient(180deg,#FFFFFF 0%,#F8FBFF 100%);box-shadow:0 10px 30px rgba(15,23,42,0.05);">
            {chart_rows}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_dashboard_metric_cards(stats: dict) -> list[dict[str, str]]:
    """统一首页 KPI 卡片的数据结构，保证顺序与展示文案稳定。"""
    acos_value = f"{stats['acos']:.2%}" if stats["acos"] > 0 else "N/A"
    return [
        {"label": "总花费", "value": f"${stats['total_spend']:.2f}"},
        {"label": "总订单", "value": str(stats["total_orders"])},
        {"label": "整体ACOS", "value": acos_value},
        {"label": "搜索词数", "value": str(stats["term_count"])},
    ]


def _build_workspace_summary_meta(
    product_name: str,
    member_count: int,
    current_role: str,
) -> dict[str, str | list[str]]:
    """统一首页工作区摘要文案。"""
    return {
        "title": "当前工作区",
        "description": "把产品分析、规则调整和人工校准都收在同一个工作区里，后续多人协作时可以继续沿用这套成员与角色模型。",
        "chips": [
            f"工作区：{product_name}",
            f"成员 {member_count} 人",
            f"当前角色：{current_role}",
        ],
    }


def _render_dashboard_metric_grid(stats: dict) -> None:
    cards_html = "".join(
        (
            f'<div class="dashboard-kpi-card">'
            f"<span>{escape(card['label'])}</span>"
            f"<strong>{escape(card['value'])}</strong>"
            "</div>"
        )
        for card in _build_dashboard_metric_cards(stats)
    )
    st.markdown(
        f'<div class="dashboard-kpi-grid">{cards_html}</div>',
        unsafe_allow_html=True,
    )


def _render_workspace_summary(meta: dict[str, str | list[str]]) -> None:
    chips_html = "".join(
        f'<span class="dashboard-chip dashboard-chip--neutral">{escape(str(chip))}</span>'
        for chip in meta["chips"]
    )
    st.markdown(
        f"""
        <div class="workspace-summary-shell">
            <h3>{escape(str(meta['title']))}</h3>
            <p>{escape(str(meta['description']))}</p>
            <div class="dashboard-hero__chips">{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_product_runtime_state_impl(
    db,
    product_id: int | None,
    *,
    stats: dict | None = None,
    pending_stats: dict | None = None,
) -> dict[str, object]:
    """构建工作台状态中心所需的产品运行态摘要。"""
    if not product_id:
        return {
            "stage_key": "select_product",
            "stage_title": "先选择工作区",
            "stage_description": "当前还没有绑定产品工作区，请先选择产品或创建新产品。",
            "latest_snapshot_at": None,
            "snapshot_count": 0,
            "campaign_count": 0,
            "search_term_count": 0,
            "analysis_result_count": 0,
            "manual_review_count": 0,
            "next_actions": [
                ("去文件上传", "先创建/选择产品工作区，再导入原始报表。"),
                ("确认产品配置", "把类目、ASIN 和关键词库先整理好，避免后续判断漂移。"),
            ],
        }

    stats = stats or _get_dashboard_stats_impl(db, product_id)
    pending_stats = pending_stats or _get_pending_stats_impl(db, product_id)

    campaign_count = db.execute(
        "SELECT COUNT(*) AS count FROM campaigns WHERE product_id = ?",
        (product_id,),
    ).fetchone()["count"]
    analysis_result_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM analysis_results ar
        JOIN search_terms st ON ar.search_term_id = st.id
        JOIN campaigns c ON st.campaign_id = c.id
        WHERE c.product_id = ?
        """,
        (product_id,),
    ).fetchone()["count"]
    manual_review_count = db.execute(
        "SELECT COUNT(*) AS count FROM manual_reviews WHERE product_id = ?",
        (product_id,),
    ).fetchone()["count"]
    snapshots = db.list_analysis_run_snapshots(product_id, limit=1)
    latest_snapshot_at = snapshots[0]["created_at"] if snapshots else None
    snapshot_count = len(db.list_analysis_run_snapshots(product_id, limit=200))
    search_term_count = int(stats.get("term_count") or 0)
    review_pending = int(pending_stats.get("review_pending_count") or 0)
    negative_pending = int(pending_stats.get("negative_count") or 0)
    manual_pending = int(pending_stats.get("manual_count") or 0)
    conflict_pending = int(pending_stats.get("conflict_count") or 0)

    if search_term_count == 0:
        stage_key = "ready_for_import"
        stage_title = "待导入原始数据"
        stage_description = "当前工作区还没有搜索词数据，先导入原始报表再开始本轮分析。"
        next_actions = [
            ("去文件上传", "上传原始搜索词报表，建立当前分析轮次。"),
            ("检查产品信息", "确认产品类目、ASIN 和关键词库，避免分析建立在旧配置上。"),
        ]
    elif analysis_result_count == 0 and snapshot_count == 0:
        stage_key = "ready_for_analysis"
        stage_title = "待运行分析"
        stage_description = "已有原始报表，但还没有形成任何分析结果或快照，适合立即重新运行分析。"
        next_actions = [
            ("重新运行分析", "进入数据管理或上传页，生成本轮最新结论。"),
            ("确认是否清空旧数据", "如果这是新类目或新批次，先清理旧运行数据再分析。"),
        ]
    elif review_pending > 0:
        stage_key = "needs_review"
        stage_title = "待人工审核"
        stage_description = f"当前有 {review_pending} 个词待人工拍板，建议先完成审核，再决定执行清单。"
        next_actions = [
            ("进入相关性审核", "先处理 AI 低置信度与分歧词，稳定最终结论。"),
            ("查看 AI 审核建议", "优先处理高风险、高花费的待审词。"),
        ]
    elif negative_pending > 0 or manual_pending > 0 or conflict_pending > 0:
        stage_key = "ready_for_execution"
        stage_title = "待执行优化动作"
        stage_description = (
            f"当前有 {negative_pending} 个否词、{manual_pending} 个手动机会"
            + (f"、{conflict_pending} 个分歧词" if conflict_pending > 0 else "")
            + "，建议先止损再补量。"
        )
        next_actions = [
            ("进入操作清单", "按优先级导出否词、手动投放和分歧处理建议。"),
            ("生成执行备注", "把本轮动作整理给自己或同事，减少执行偏差。"),
        ]
    else:
        stage_key = "ready_for_reviewback"
        stage_title = "可复盘 / 可开始新一轮"
        stage_description = "当前没有明显待处理项，适合回看最近一次分析，或开始下一轮导入与复盘。"
        next_actions = [
            ("查看最近一次分析", "确认本轮结论是否稳定，是否需要复跑。"),
            ("导出完整备份", "在开始下一轮前先留一个恢复点。"),
        ]

    return {
        "stage_key": stage_key,
        "stage_title": stage_title,
        "stage_description": stage_description,
        "latest_snapshot_at": latest_snapshot_at,
        "snapshot_count": snapshot_count,
        "campaign_count": campaign_count,
        "search_term_count": search_term_count,
        "analysis_result_count": analysis_result_count,
        "manual_review_count": manual_review_count,
        "next_actions": next_actions,
    }


def _build_workbench_status_cards(runtime_state: dict[str, object]) -> list[dict[str, str]]:
    """构建首页工作状态卡片。"""
    latest_snapshot_at = runtime_state.get("latest_snapshot_at")
    latest_snapshot_label = (
        str(latest_snapshot_at).replace("T", " ")[:16]
        if latest_snapshot_at
        else "还没有分析快照"
    )
    snapshot_count = int(runtime_state.get("snapshot_count") or 0)
    return [
        {
            "label": "当前阶段",
            "value": str(runtime_state.get("stage_title") or "待确认"),
            "description": str(runtime_state.get("stage_description") or ""),
        },
        {
            "label": "最近一次分析",
            "value": latest_snapshot_label,
            "description": "latest snapshot 优先驱动各结果页；没有时会回退到实时结果。",
        },
        {
            "label": "历史沉淀",
            "value": f"{snapshot_count} 个分析快照",
            "description": f"已保存 {runtime_state.get('manual_review_count', 0)} 条人工审核记录，可供回看与恢复。",
        },
        {
            "label": "数据规模",
            "value": f"{runtime_state.get('search_term_count', 0)} 条搜索词 / {runtime_state.get('campaign_count', 0)} 个活动",
            "description": f"当前已形成 {runtime_state.get('analysis_result_count', 0)} 条分析结果。",
        },
    ]


def _render_workbench_status(runtime_state: dict[str, object]) -> None:
    cards_html = "".join(
        f"""
        <div class="workbench-status-card">
            <small>{escape(card['label'])}</small>
            <strong>{escape(card['value'])}</strong>
            <span>{escape(card['description'])}</span>
        </div>
        """
        for card in _build_workbench_status_cards(runtime_state)
    )
    next_actions_html = "".join(
        f"""
        <div class="workbench-next-action">
            <strong>{escape(title)}</strong>
            <span>{escape(description)}</span>
        </div>
        """
        for title, description in runtime_state.get("next_actions", [])
    )
    st.markdown(
        f"""
        <div class="workbench-status-shell">
            <h3>当前工作状态</h3>
            <p>先确认这轮数据处在什么阶段，再决定是导入、分析、审核、执行还是直接做备份。</p>
            <div class="workbench-status-grid">{cards_html}</div>
            <div class="workbench-next-actions">{next_actions_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_pending_notices(pending_stats: dict[str, int]) -> list[tuple[str, str]]:
    """将首页待处理项整理为稳定、可测试的提示列表。"""
    notices: list[tuple[str, str]] = []

    if pending_stats.get("negative_count", 0) > 0:
        notices.append(("warning", f"{pending_stats['negative_count']} 个词需要否定"))

    if pending_stats.get("manual_count", 0) > 0:
        notices.append(("success", f"{pending_stats['manual_count']} 个高转化词待投放"))

    if pending_stats.get("conflict_count", 0) > 0:
        notices.append(("warning", f"{pending_stats['conflict_count']} 个词存在跨ASIN分歧，需人工拍板"))

    if pending_stats.get("ai_pending_count", 0) > 0:
        notices.append(("info", f"{pending_stats['ai_pending_count']} 个词待AI确认"))

    if pending_stats.get("review_pending_count", 0) > 0:
        notices.append(("info", f"{pending_stats['review_pending_count']} 个词待审核相关性"))

    if not notices:
        notices.append(("success", "暂无待处理项"))

    return notices


def _render_pending_notice_cards(notices: list[tuple[str, str]]) -> None:
    cards_html = "".join(
        (
            f'<div class="pending-notice-card pending-notice-card--{escape(level)}">'
            f"<small>{'待处理' if level != 'success' else '可执行机会'}</small>"
            f"<strong>{escape(message)}</strong>"
            "</div>"
        )
        for level, message in notices
    )
    st.markdown(
        f'<div class="pending-notice-stack">{cards_html}</div>',
        unsafe_allow_html=True,
    )


def _navigate_to(page: str) -> None:
    """切换到目标页面。"""
    st.session_state.nav_page = page


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_all_dashboard_data(_db, product_id: int = None) -> dict:
    """
    批量获取仪表盘所有统计数据（减少数据库往返次数）

    Args:
        _db: 数据库连接（前缀_表示不参与缓存key计算）
        product_id: 产品ID

    Returns:
        包含 dashboard_stats, pending_stats, rule_stats 的字典
    """
    dashboard_stats = _get_dashboard_stats_impl(_db, product_id)
    pending_stats = _get_pending_stats_impl(_db, product_id)
    overview_chart = (
        _get_overview_chart_impl(_db, product_id)
        if dashboard_stats["term_count"] > 0
        else {"x_label": "规则", "title": "数据概览", "data": {}}
    )

    return {
        "dashboard_stats": dashboard_stats,
        "pending_stats": pending_stats,
        "overview_chart": overview_chart,
    }


def render_home():
    """渲染首页"""
    st.markdown(HOME_PAGE_CSS, unsafe_allow_html=True)

    db = st.session_state.get("db")
    product_id = st.session_state.get("current_product_id")

    product_name = None
    if db and product_id:
        row = db.execute(
            "SELECT name FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        if row:
            product_name = row["name"]

    st.markdown(
        f"""
        <div class="dashboard-hero">
            <span class="dashboard-hero__eyebrow">运营总览</span>
            <h1>搜索词运营工作台</h1>
            <p>{escape(product_name or "当前产品未选择")} · 先看结论、再看动作、最后看明细，避免在一堆表格里来回捞针。</p>
            <div class="dashboard-hero__chips">
                <span class="dashboard-chip dashboard-chip--neutral">自动建议 / 人工校准 / 最终结论</span>
                <span class="dashboard-chip dashboard-chip--warning">优先处理待否定与跨ASIN分歧</span>
                <span class="dashboard-chip dashboard-chip--success">一键进入上传 / 分析 / 执行</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if product_id and product_name:
        workspace_summary = db.get_workspace_summary(product_id)
        _render_workspace_summary(
            _build_workspace_summary_meta(
                product_name=product_name,
                member_count=workspace_summary["member_count"],
                current_role=workspace_summary["current_role"],
            )
        )

    if not db:
        st.error("数据库未初始化")
        return

    # 批量获取所有统计数据（单次缓存调用替代3次独立查询）
    all_data = get_all_dashboard_data(db, product_id)
    stats = all_data["dashboard_stats"]
    runtime_state = _get_product_runtime_state_impl(
        db,
        product_id,
        stats=stats,
        pending_stats=all_data["pending_stats"],
    )

    _render_workbench_status(runtime_state)

    _render_dashboard_metric_grid(stats)

    # 待处理项
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("待处理项")
        st.caption("按执行优先级整理，只把真正需要你立刻处理的事项放在上面。")

        pending_stats = all_data["pending_stats"]
        notices = _build_pending_notices(pending_stats)
        _render_pending_notice_cards(notices)

    with col_right:
        st.subheader("快速操作")
        st.markdown(
            '<p class="quick-action-caption">把最常用的动作压缩在一屏里：先上传，再分析，再去执行清单，不用在左侧来回点菜单。</p>',
            unsafe_allow_html=True,
        )

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            st.button(
                "上传新数据",
                width="stretch",
                on_click=_navigate_to,
                args=("文件上传",),
            )

            st.button(
                "查看操作清单",
                width="stretch",
                on_click=_navigate_to,
                args=("操作清单",),
            )

            # v2.0: 相关性审核入口
            st.button(
                "相关性审核",
                width="stretch",
                on_click=_navigate_to,
                args=("相关性审核",),
            )

        with col_btn2:
            st.button(
                "分析搜索词",
                width="stretch",
                on_click=_navigate_to,
                args=("搜索词分析",),
            )

            st.button(
                "系统设置",
                width="stretch",
                on_click=_navigate_to,
                args=("系统设置",),
            )

            st.button(
                "数据清理与备份",
                width="stretch",
                on_click=_navigate_to,
                args=("系统设置",),
                help="进入系统设置 > 数据管理，执行清空、备份与恢复。",
            )

    st.divider()

    overview_chart = all_data["overview_chart"]
    st.subheader(overview_chart.get("title", "数据概览"))

    if stats["term_count"] > 0:
        chart_data = {
            key: value
            for key, value in overview_chart.get("data", {}).items()
            if value > 0
        }

        if chart_data:
            _render_overview_chart(chart_data)
    else:
        st.info("暂无数据，请先上传搜索词报告")


def _get_dashboard_stats_impl(db, product_id: int = None) -> dict:
    """获取仪表盘统计数据（内部实现）"""
    try:
        # search_terms 表没有 product_id，需要通过 campaigns 关联
        if product_id:
            query = """
                SELECT
                    COUNT(DISTINCT st.term) as term_count,
                    COALESCE(SUM(st.spend), 0) as total_spend,
                    COALESCE(SUM(st.orders), 0) as total_orders,
                    COALESCE(SUM(st.sales), 0) as total_sales
                FROM search_terms st
                JOIN campaigns c ON st.campaign_id = c.id
                WHERE c.product_id = ?
            """
            params = (product_id,)
        else:
            query = """
                SELECT
                    COUNT(DISTINCT term) as term_count,
                    COALESCE(SUM(spend), 0) as total_spend,
                    COALESCE(SUM(orders), 0) as total_orders,
                    COALESCE(SUM(sales), 0) as total_sales
                FROM search_terms
            """
            params = ()

        cursor = db.execute(query, params)
        row = cursor.fetchone()

        if not row:
            return {
                "term_count": 0,
                "total_spend": 0,
                "total_orders": 0,
                "total_sales": 0,
                "acos": 0,
            }

        total_spend = row["total_spend"] or 0
        total_sales = row["total_sales"] or 0

        return {
            "term_count": row["term_count"] or 0,
            "total_spend": total_spend,
            "total_orders": row["total_orders"] or 0,
            "total_sales": total_sales,
            "acos": total_spend / total_sales if total_sales > 0 else 0,
        }
    except Exception as e:
        logger.error(f"获取仪表盘统计失败: {e}")
        return {
            "term_count": 0,
            "total_spend": 0,
            "total_orders": 0,
            "total_sales": 0,
            "acos": 0,
        }


def _get_pending_stats_impl(db, product_id: int = None) -> dict:
    """获取待处理项统计（使用实时分析结果）"""
    try:
        truth_stats = get_truth_first_pending_stats(db, product_id)
        if truth_stats is not None:
            return truth_stats

        # 使用规则引擎实时分析，与搜索词分析页面保持一致
        results = analyze_search_terms(db, product_id)

        stats = {
            "negative_count": 0,
            "manual_count": 0,
            "ai_pending_count": 0,
            "review_pending_count": 0,  # v2.0: 待审核相关性词数
        }

        for result in results:
            # action_type 可能是 negative_exact, negative_phrase, manual_exact 等
            action = result.action_type or ""
            if action.startswith("negative"):
                stats["negative_count"] += 1
            elif action.startswith("manual"):
                stats["manual_count"] += 1
            # 用 confidence < 1.0 判断是否需要AI确认
            if result.confidence < 1.0:
                stats["ai_pending_count"] += 1
            # v2.0: 统计需要审核相关性的词
            if getattr(result, "needs_review", False):
                stats["review_pending_count"] += 1

        return stats
    except Exception as e:
        logger.error(f"获取待处理统计失败: {e}")
        return {
            "negative_count": 0,
            "manual_count": 0,
            "ai_pending_count": 0,
            "review_pending_count": 0,  # v2.0: 待审核相关性词数
        }


def _get_overview_chart_impl(db, product_id: int = None) -> dict:
    """获取首页数据概览图表数据。"""
    try:
        truth_distribution = get_truth_first_overview_distribution(db, product_id)
        if truth_distribution is not None:
            return {
                "x_label": "分类",
                "title": "数据概览（最终结论）",
                "data": truth_distribution,
            }

        # 使用规则引擎实时分析，与搜索词分析页面保持一致
        results = analyze_search_terms(db, product_id)

        rule_counts = {}
        for result in results:
            rule = result.triggered_rule
            rule_counts[rule] = rule_counts.get(rule, 0) + 1

        # 按数量降序排列，取前10
        sorted_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]
        return {
            "x_label": "规则",
            "title": "数据概览",
            "data": dict(sorted_rules),
        }
    except Exception as e:
        logger.error(f"获取规则统计失败: {e}")
        return {"x_label": "规则", "title": "数据概览", "data": {}}


# 公开API（向后兼容）
def get_dashboard_stats(db, product_id: int = None) -> dict:
    """获取仪表盘统计数据（公开API，用于测试）"""
    return _get_dashboard_stats_impl(db, product_id)


def get_pending_stats(db, product_id: int = None) -> dict:
    """获取待处理项统计（公开API，用于测试）"""
    return _get_pending_stats_impl(db, product_id)


def get_rule_stats(db, product_id: int = None) -> dict:
    """获取首页数据概览图表分布（公开API，用于测试）"""
    return _get_overview_chart_impl(db, product_id)["data"]
