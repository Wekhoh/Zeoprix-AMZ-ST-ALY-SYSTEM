from __future__ import annotations

from typing import Any

from src.ai.chat import get_chat_assistant
from src.ai.copilot import build_ai_context_pack, build_chat_response_envelope
from src.backend.workbench_payload import _get_app_database_path
from src.data.db import Database


def _derive_action_links(actions: list[str], page_key: str) -> list[dict[str, str]]:
    links: dict[str, dict[str, str]] = {}
    for action in actions:
        if any(keyword in action for keyword in ["审核", "拍板", "分歧"]) and page_key != "review":
            links.setdefault("review", {"label": "去审核中心", "href": "/review"})
        if any(keyword in action for keyword in ["批次", "执行", "否词", "手动投放", "补量"]) and page_key != "actions":
            links.setdefault("actions", {"label": "去操作清单", "href": "/actions"})
        if any(keyword in action for keyword in ["导入", "上传", "重跑分析", "重新运行分析"]) and page_key != "upload":
            links.setdefault("upload", {"label": "去数据导入", "href": "/upload"})
        if any(keyword in action for keyword in ["备份", "恢复", "清空", "数据管理"]) and page_key != "settings":
            links.setdefault("settings", {"label": "去数据管理", "href": "/settings"})
        if any(keyword in action for keyword in ["筛选", "结构", "分布", "趋势", "搜索词分析"]) and page_key != "analysis":
            links.setdefault("analysis", {"label": "去搜索词分析", "href": "/analysis"})
    return list(links.values())[:3]


def process_frontend_copilot_turn(
    *,
    product_id: int | None,
    page_key: str,
    page_title: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    history = history or []

    with Database(str(db_path)) as db:
        context_pack = build_ai_context_pack(
            db,
            product_id,
            page_key=page_key,
            page_title=page_title,
            page_context={},
        )
        assistant = get_chat_assistant(db=db, product_id=product_id)

        history_lines: list[str] = []
        for item in history[-6:]:
            role = str(item.get("role") or "user")
            content = str(item.get("content") or "").strip()
            if content:
                history_lines.append(f"{role}: {content}")

        prompt = user_message.strip()
        if history_lines:
            prompt = "最近对话：\n" + "\n".join(history_lines) + f"\n\n当前问题：{prompt}"

        try:
            response = assistant.process_message(prompt)
            envelope = build_chat_response_envelope(response, context_pack)
            text_parts = [envelope.headline, *envelope.bullets]
            return {
                "message": "\n".join(part for part in text_parts if part).strip(),
                "followUpPrompts": envelope.follow_up_prompts,
                "recommendedNextActions": envelope.recommended_next_actions,
                "actionLinks": _derive_action_links(envelope.recommended_next_actions, page_key),
                "contextLabel": envelope.context_label,
                "warning": envelope.warning,
            }
        except Exception as exc:  # pragma: no cover - runtime fallback
            fallback_actions = ["继续使用页面内的结构化数据完成当前操作"]
            return {
                "message": f"AI 助手当前不可用：{exc}",
                "followUpPrompts": ["先查看今日最优先 3 个动作", "稍后再试一次"],
                "recommendedNextActions": fallback_actions,
                "actionLinks": _derive_action_links(fallback_actions, page_key),
                "contextLabel": context_pack.context_label,
                "warning": "当前已回退到无会话兜底模式。",
            }
