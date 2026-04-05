"""AI Copilot shared context and response shaping helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.ai.chat import ChatResponse


@dataclass(slots=True)
class AIContextPack:
    """统一的 AI 工作流上下文。"""

    page_key: str
    page_title: str
    product_id: int | None = None
    product_name: str = "当前产品"
    context_source: str = "product_only"
    context_label: str = "当前产品：当前产品 · 上下文：仅产品基础信息"
    snapshot_id: int | None = None
    snapshot_created_at: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    page_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AIResponseEnvelope:
    """统一的 AI 输出载荷，供聊天窗和页面 AI 卡片复用。"""

    mode: str
    headline: str
    bullets: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: str = "medium"
    recommended_next_actions: list[str] = field(default_factory=list)
    follow_up_prompts: list[str] = field(default_factory=list)
    warning: str | None = None
    context_label: str = ""
    raw_message: str = ""

    def to_message_fields(self) -> dict[str, Any]:
        """转成聊天消息需要的结构化字段。"""
        return asdict(self)


def _clean_text_list(values: list[Any] | None) -> list[str]:
    return [str(item).strip() for item in values or [] if str(item).strip()]


def _normalize_evidence_items(rows: list[dict[str, Any]] | None, limit: int = 3) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in (rows or [])[:limit]:
        normalized.append(
            {
                "term": str(row.get("term") or "").strip(),
                "triggered_rule": str(row.get("triggered_rule") or "").strip(),
                "action_type": str(row.get("action_type") or "").strip(),
                "suggested_action": str(row.get("suggested_action") or "").strip(),
                "clicks": int(row.get("clicks") or 0),
                "orders": int(row.get("orders") or 0),
                "spend": float(row.get("spend") or 0),
                "sales": float(row.get("sales") or 0),
            }
        )
    return normalized


def _build_metrics(summary: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "negative_count": int(summary.get("negative", 0) or 0),
        "manual_count": int(summary.get("manual", 0) or 0),
        "conflict_count": int(summary.get("conflict", 0) or 0),
        "term_count": len(rows or []),
    }


def build_ai_context_pack(
    db,
    product_id: int | None,
    *,
    page_key: str,
    page_title: str,
    page_context: dict[str, Any] | None = None,
) -> AIContextPack:
    """构建统一 AI 上下文；有 snapshot 时优先绑定最近一次有效分析结果。"""
    page_context = page_context or {}
    product_name = str(page_context.get("product_name") or "当前产品").strip() or "当前产品"

    latest_snapshot = None
    summary: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    snapshot_id: int | None = None
    snapshot_created_at: str | None = None
    context_source = "product_only"

    if db is not None and product_id is not None:
        product = db.get_product(product_id)
        if product and product.get("name"):
            product_name = str(product.get("name")).strip() or product_name

        snapshots = db.list_analysis_run_snapshots(product_id, limit=1)
        if snapshots:
            latest_snapshot = snapshots[0]
            summary = latest_snapshot.get("summary") or {}
            rows = latest_snapshot.get("rows") or []
            snapshot_id = latest_snapshot.get("id")
            snapshot_created_at = latest_snapshot.get("created_at")
            context_source = "latest_snapshot"

    source_label = "最近一次分析结果" if context_source == "latest_snapshot" else "仅产品基础信息"
    context_label = f"当前产品：{product_name} · 上下文：{source_label}"

    return AIContextPack(
        page_key=page_key,
        page_title=page_title,
        product_id=product_id,
        product_name=product_name,
        context_source=context_source,
        context_label=context_label,
        snapshot_id=snapshot_id,
        snapshot_created_at=snapshot_created_at,
        summary=summary,
        metrics=_build_metrics(summary, rows),
        evidence=_normalize_evidence_items(rows),
        filters={k: v for k, v in page_context.items() if k != "product_name"},
        page_context=page_context,
    )


def _split_response_text(message: str) -> tuple[str, list[str]]:
    lines = [line.strip("•- ").strip() for line in str(message or "").splitlines() if line.strip()]
    if not lines:
        return "AI 已完成分析。", []
    headline = lines[0]
    bullets = lines[1:]
    return headline, bullets


def _default_next_actions(page_key: str) -> list[str]:
    mapping = {
        "summary": ["先确认最浪费的词", "再整理手动投放机会", "最后回到审核页确认边界词"],
        "actions": ["先执行否词清单", "再处理手动投放草稿", "最后整理汇报摘要给团队"],
        "upload": ["先确认导入质量", "再运行规则分析", "最后进入汇总页查看机会与风险"],
        "campaign": ["先收紧高浪费活动", "再对高转化活动补量", "最后核对活动级边界词"],
        "asin": ["先确认问题集中在哪个变体", "再排查页面承接与词意图", "最后回到审核页校准边界词"],
        "review": ["先确认 AI 判断是否合理", "再保存人工最终决定", "最后回到操作清单查看影响"],
    }
    return mapping.get(page_key, ["继续追问具体问题", "切到相关页面继续处理"])


def build_chat_response_envelope(
    response: ChatResponse,
    context_pack: AIContextPack,
) -> AIResponseEnvelope:
    """把聊天响应包装成结构化前端 envelope。"""
    headline, bullets = _split_response_text(response.message)
    confidence = "medium" if context_pack.context_source == "latest_snapshot" else "low"
    warning = None
    if context_pack.context_source != "latest_snapshot":
        warning = "当前回答主要基于产品基础信息，尚未找到最近一次有效分析结果。"

    return AIResponseEnvelope(
        mode="answer",
        headline=headline,
        bullets=bullets,
        evidence=context_pack.evidence[:3],
        confidence=confidence,
        recommended_next_actions=_default_next_actions(context_pack.page_key),
        follow_up_prompts=[option.label.strip() for option in response.options if option.label.strip()],
        warning=warning,
        context_label=context_pack.context_label,
        raw_message=response.message,
    )


def build_summary_ai_brief(db, product_id: int) -> dict[str, Any]:
    """为汇总页生成轻量 AI 简报。"""
    context_pack = build_ai_context_pack(
        db,
        product_id,
        page_key="summary",
        page_title="汇总分析",
    )
    metrics = context_pack.metrics
    evidence = context_pack.evidence[:2]

    if context_pack.context_source == "latest_snapshot":
        headline = (
            f"{context_pack.product_name} 当前最值得优先处理的是控制高浪费词，并同步放大已识别的高价值机会。"
        )
        bullets = [
            f"最近一次分析识别出 {metrics['negative_count']} 个可直接否定词、{metrics['manual_count']} 个手动投放机会，另有 {metrics['conflict_count']} 个分歧点待人工确认。",
        ]
        if evidence:
            first = evidence[0]
            bullets.append(
                f"当前最突出的证据词是 {first['term']}，触发规则为“{first['triggered_rule'] or '规则分析'}”，已累计花费 ${first['spend']:.2f}。"
            )
    else:
        headline = f"{context_pack.product_name} 还缺少最近一次有效分析结果，建议先完成上传和规则分析，再让 AI 解释趋势。"
        bullets = [
            "当前只能基于产品基础信息给出概括性建议，无法引用最近一次分析快照里的具体词、花费和动作分布。",
        ]

    return {
        "headline": headline,
        "bullets": bullets,
        "evidence": evidence,
        "recommended_next_actions": _default_next_actions("summary"),
        "follow_up_prompts": ["为什么 ACOS 高？", "哪些词最浪费？", "先做哪 3 个动作？"],
        "context_label": context_pack.context_label,
        "warning": (
            "当前没有最近一次有效分析结果，建议先重新运行分析。"
            if context_pack.context_source != "latest_snapshot"
            else None
        ),
    }


def build_actions_ai_brief(action_context: dict[str, Any]) -> dict[str, Any]:
    """为操作清单页生成执行说明卡。"""
    counts = action_context.get("counts") or {}
    product_name = str(action_context.get("product_name") or "当前产品").strip() or "当前产品"
    context_label = str(
        action_context.get("context_label")
        or f"当前产品：{product_name} · 上下文：最近一次分析结果"
    )

    headline = (
        f"{product_name} 当前已经具备一批可直接执行的动作，建议先处理最确定的预算浪费点，再推进增量机会。"
    )
    bullets = [
        f"当前清单里有 {int(counts.get('negative', 0) or 0)} 个可直接否定项、{int(counts.get('manual', 0) or 0)} 个手动投放机会，另有 {int(counts.get('conflict', 0) or 0)} 个分歧项需要人工拍板。",
        "否词与手动投放草稿都应先人工确认后再执行，避免把边界词直接带到广告后台。",
    ]

    evidence: list[dict[str, Any]] = []
    buckets = action_context.get("buckets") or {}
    for bucket_key in (
        "negative_keyword_exact",
        "manual_keywords",
        "cross_asin_conflicts",
    ):
        items = buckets.get(bucket_key) or []
        if items:
            evidence.append(items[0])

    return {
        "headline": headline,
        "bullets": bullets,
        "evidence": evidence[:3],
        "recommended_next_actions": _default_next_actions("actions"),
        "follow_up_prompts": ["先执行哪些动作？", "给我老板汇报摘要", "哪些词还需要人工判断？"],
        "context_label": context_label,
        "warning": None,
    }


def build_campaign_ai_brief(
    results_data: list[dict[str, Any]],
    *,
    product_name: str,
    context_label: str,
) -> dict[str, Any]:
    """为按活动页生成 AI 解释卡。"""
    rows = list(results_data or [])
    if not rows:
        return {
            "headline": f"{product_name} 当前没有可解释的活动分析结果。",
            "bullets": ["请先调整筛选条件，或先完成一次成功分析后再查看活动级解释。"],
            "evidence": [],
            "recommended_next_actions": _default_next_actions("campaign"),
            "follow_up_prompts": ["为什么当前活动没有结果？"],
            "context_label": context_label,
            "warning": "当前筛选条件下没有可用于 AI 解释的活动结果。",
        }

    top_spend = max(rows, key=lambda row: float(row.get("spend") or 0.0))
    campaign_count = len({str(row.get("campaign_id") or "").strip() for row in rows if str(row.get("campaign_id") or "").strip()})
    negative_count = sum(1 for row in rows if "negative" in str(row.get("action_type") or ""))
    manual_count = sum(1 for row in rows if "manual" in str(row.get("action_type") or ""))

    bullets = [
        f"当前共覆盖 {campaign_count} 个活动，其中 {negative_count} 条结果倾向先控浪费，另有 {manual_count} 条结果提示值得补量。",
        f"最值得优先盯住的活动是 {top_spend.get('campaign_name') or '未命名活动'}，其代表词 {top_spend.get('term') or '-'} 已累计花费 ${float(top_spend.get('spend') or 0):.2f}。",
    ]
    if top_spend.get("triggered_rule"):
        bullets.append(
            f"该活动当前最关键的判断依据是“{top_spend.get('triggered_rule')}”，建议先确认这类词是否真的不值得继续放量。"
        )

    return {
        "headline": f"{product_name} 当前最需要优先解释的是高花费活动里的词意图与预算浪费点。",
        "bullets": bullets,
        "evidence": _normalize_evidence_items(rows, limit=3),
        "recommended_next_actions": _default_next_actions("campaign"),
        "follow_up_prompts": ["为什么这个活动最差？", "哪些活动该先减预算？", "哪些活动值得补量？"],
        "context_label": context_label,
        "warning": None,
    }


def build_asin_ai_brief(
    results_data: list[dict[str, Any]],
    *,
    product_name: str,
    context_label: str,
) -> dict[str, Any]:
    """为按 ASIN 页生成 AI 归因卡。"""
    rows = list(results_data or [])
    if not rows:
        return {
            "headline": f"{product_name} 当前没有可解释的 ASIN 分析结果。",
            "bullets": ["请先调整筛选条件，或先完成一次成功分析后再查看变体归因。"],
            "evidence": [],
            "recommended_next_actions": _default_next_actions("asin"),
            "follow_up_prompts": ["为什么当前 ASIN 没有结果？"],
            "context_label": context_label,
            "warning": "当前筛选条件下没有可用于 AI 归因的 ASIN 结果。",
        }

    top_spend = max(rows, key=lambda row: float(row.get("spend") or 0.0))
    asin_count = len({str(row.get("asin_identifier") or "").strip() for row in rows if str(row.get("asin_identifier") or "").strip()})
    bullets = [
        f"当前共覆盖 {asin_count} 个变体，最值得先排查的是 {top_spend.get('asin_identifier') or '未知 ASIN'} 对应的高花费词流量。",
        f"代表词 {top_spend.get('term') or '-'} 已累计花费 ${float(top_spend.get('spend') or 0):.2f}，当前建议动作是 {top_spend.get('suggested_action') or top_spend.get('action_type') or '继续观察'}。",
    ]
    if top_spend.get("triggered_rule"):
        bullets.append(
            f"当前更像是“{top_spend.get('triggered_rule')}”导致的变体承接问题，建议先核对词意图与页面承接是否匹配。"
        )

    return {
        "headline": f"{product_name} 当前最需要聚焦的是把高花费词与具体变体表现对应起来，再决定是否继续投放。",
        "bullets": bullets,
        "evidence": _normalize_evidence_items(rows, limit=3),
        "recommended_next_actions": _default_next_actions("asin"),
        "follow_up_prompts": ["哪个 ASIN 最拖后腿？", "这是词不准还是页面问题？", "哪些变体值得继续放量？"],
        "context_label": context_label,
        "warning": None,
    }


def build_review_ai_brief(
    *,
    term: str,
    term_type: str,
    item: dict[str, Any],
    ai_suggestion: dict[str, Any] | None,
    context_label: str,
) -> dict[str, Any]:
    """为审核页生成 AI 建议卡。"""
    term_label = str(term or "当前词").strip() or "当前词"
    clicks = int(float(item.get("total_clicks") or item.get("clicks") or 0))
    orders = int(float(item.get("total_orders") or item.get("orders") or 0))
    spend = float(item.get("total_spend") or item.get("spend") or 0.0)
    current_manual = item.get("competition_level") if term_type == "asin" else item.get("relevance")

    if ai_suggestion:
        ai_label = str(ai_suggestion.get("relevance") or "pending").strip() or "pending"
        ai_confidence = float(ai_suggestion.get("confidence") or 0.0)
        reasoning = str(ai_suggestion.get("reasoning") or "").strip()
        suggested_action = str(ai_suggestion.get("suggested_action") or "").strip()
        bullets = [
            f"AI 当前建议：{ai_label}（置信度 {ai_confidence:.0%}）。",
            f"人工当前标记：{current_manual or '尚未定稿'}。",
        ]
        if reasoning:
            bullets.append(f"AI 主要理由：{reasoning}")
        if suggested_action:
            bullets.append(f"建议动作：{suggested_action}")
        warning = str(ai_suggestion.get('status_message') or "").strip() or None
        headline = f"{term_label} 当前已有 AI 审核建议，下一步重点是确认这条判断是否适合作为最终人工结论。"
    else:
        bullets = [
            f"人工当前标记：{current_manual or '尚未定稿'}。",
            "当前还没有 AI 审核建议，建议先获取建议，再判断是否采纳。",
        ]
        warning = "当前尚未获取 AI 建议。"
        headline = f"{term_label} 当前还没有 AI 审核建议，建议先生成建议再决定最终标记。"

    return {
        "headline": headline,
        "bullets": bullets,
        "evidence": [
            {
                "term": term_label,
                "triggered_rule": str(item.get("triggered_rule") or "").strip(),
                "action_type": str(item.get("action_type") or "").strip(),
                "suggested_action": str(item.get("suggested_action") or "").strip(),
                "clicks": clicks,
                "orders": orders,
                "spend": spend,
                "sales": float(item.get("sales") or 0.0),
            }
        ],
        "recommended_next_actions": _default_next_actions("review"),
        "follow_up_prompts": ["为什么这么判断？", "如果不采纳会怎样？", "给我一个更保守的建议"],
        "context_label": context_label,
        "warning": warning,
    }


def format_ai_context_hint(context_pack: AIContextPack) -> str:
    """把统一上下文转成发送给模型的辅助提示。"""
    lines = [
        f"当前页面：{context_pack.page_title}",
        f"当前产品：{context_pack.product_name}",
        f"上下文来源：{'最近一次分析结果' if context_pack.context_source == 'latest_snapshot' else '仅产品基础信息'}",
    ]
    if context_pack.context_source == "latest_snapshot":
        lines.append(
            "最近一次分析摘要："
            f"否定 {context_pack.metrics.get('negative_count', 0)} 个，"
            f"手动投放 {context_pack.metrics.get('manual_count', 0)} 个，"
            f"冲突 {context_pack.metrics.get('conflict_count', 0)} 个。"
        )
        if context_pack.evidence:
            lines.append("关键证据：")
            for item in context_pack.evidence[:3]:
                lines.append(
                    f"- {item.get('term')}: 规则={item.get('triggered_rule') or '规则分析'}，"
                    f"动作={item.get('suggested_action') or item.get('action_type') or '观察'}，"
                    f"花费=${float(item.get('spend') or 0):.2f}"
                )
    else:
        lines.append("当前没有最近一次有效分析结果，请明确说明结论基于有限上下文。")

    return "\n".join(lines)
