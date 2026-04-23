from __future__ import annotations

import json
from typing import Any

from src.ai.chat import get_chat_assistant
from src.ai.copilot import build_ai_context_pack, build_chat_response_envelope
from src.backend.workbench_payload import _get_app_database_path
from src.data.db import Database


def _derive_action_links(actions: list[str], page_key: str) -> list[dict[str, str]]:
    links: dict[str, dict[str, str]] = {}
    for action in actions:
        if (
            any(keyword in action for keyword in ["审核", "拍板", "分歧"])
            and page_key != "review"
        ):
            links.setdefault("review", {"label": "去审核中心", "href": "/review"})
        if (
            any(
                keyword in action
                for keyword in ["批次", "执行", "否词", "手动投放", "补量"]
            )
            and page_key != "actions"
        ):
            links.setdefault("actions", {"label": "去操作清单", "href": "/actions"})
        if (
            any(
                keyword in action
                for keyword in ["导入", "上传", "重跑分析", "重新运行分析"]
            )
            and page_key != "upload"
        ):
            links.setdefault("upload", {"label": "去数据导入", "href": "/upload"})
        if (
            any(keyword in action for keyword in ["备份", "恢复", "清空", "数据管理"])
            and page_key != "settings"
        ):
            links.setdefault("settings", {"label": "去数据管理", "href": "/settings"})
        if (
            any(
                keyword in action
                for keyword in ["筛选", "结构", "分布", "趋势", "搜索词分析"]
            )
            and page_key != "analysis"
        ):
            links.setdefault("analysis", {"label": "去搜索词分析", "href": "/analysis"})
    return list(links.values())[:3]


def _build_page_context_summary(page_context: dict[str, Any] | None) -> str:
    if not isinstance(page_context, dict):
        return ""
    summary = str(page_context.get("summary") or "").strip()
    if summary:
        return summary
    pieces: list[str] = []
    for key, value in page_context.items():
        if key == "product_name" or value in (None, "", [], {}):
            continue
        pieces.append(f"{key}: {value}")
    return "；".join(pieces[:4])


def process_frontend_copilot_turn(
    *,
    product_id: int | None,
    page_key: str,
    page_title: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
    page_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    db_path = _get_app_database_path()
    history = history or []
    page_context = page_context or {}

    with Database(str(db_path)) as db:
        context_pack = build_ai_context_pack(
            db,
            product_id,
            page_key=page_key,
            page_title=page_title,
            page_context=page_context,
        )
        assistant = get_chat_assistant(db=db, product_id=product_id)

        history_lines: list[str] = []
        for item in history[-6:]:
            role = str(item.get("role") or "user")
            content = str(item.get("content") or "").strip()
            if content:
                history_lines.append(f"{role}: {content}")

        prompt_sections: list[str] = []
        page_summary = _build_page_context_summary(page_context)
        if page_summary:
            prompt_sections.append(f"当前页面状态：{page_summary}")
        if history_lines:
            prompt_sections.append("最近对话：\n" + "\n".join(history_lines))
        prompt_sections.append(f"当前问题：{user_message.strip()}")
        prompt = "\n\n".join(section for section in prompt_sections if section.strip())

        try:
            response = assistant.process_message(prompt)
            envelope = build_chat_response_envelope(response, context_pack)
            text_parts = [envelope.headline, *envelope.bullets]
            return {
                "message": "\n".join(part for part in text_parts if part).strip(),
                "followUpPrompts": envelope.follow_up_prompts,
                "recommendedNextActions": envelope.recommended_next_actions,
                "actionLinks": _derive_action_links(
                    envelope.recommended_next_actions, page_key
                ),
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


async def process_frontend_copilot_turn_stream(
    *,
    product_id: int | None,
    page_key: str,
    page_title: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
    page_context: dict[str, Any] | None = None,
):
    """
    Async generator yielding SSE-formatted bytes 'data: {json}\\n\\n'.

    Frames: context → N×delta → envelope → done (or error → done on failure).
    Applies 45s cap on each pump step; logs start/completed/cancelled/error.
    """
    import asyncio
    import time
    from src.config.logger import get_logger

    logger = get_logger(__name__)
    db_path = _get_app_database_path()
    history = history or []
    page_context = page_context or {}

    logger.info(
        f"SSE started product={product_id} page={page_key} msg_len={len(user_message)}"
    )
    start = time.perf_counter()
    chunks_count = 0
    total_chars = 0

    def _frame(obj: dict[str, Any]) -> bytes:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")

    try:
        with Database(str(db_path)) as db:
            context_pack = build_ai_context_pack(
                db,
                product_id,
                page_key=page_key,
                page_title=page_title,
                page_context=page_context,
            )
            assistant = get_chat_assistant(db=db, product_id=product_id)

            history_lines: list[str] = []
            for item in history[-6:]:
                role = str(item.get("role") or "user")
                content = str(item.get("content") or "").strip()
                if content:
                    history_lines.append(f"{role}: {content}")

            prompt_sections: list[str] = []
            page_summary = _build_page_context_summary(page_context)
            if page_summary:
                prompt_sections.append(f"当前页面状态：{page_summary}")
            if history_lines:
                prompt_sections.append("最近对话：\n" + "\n".join(history_lines))
            prompt_sections.append(f"当前问题：{user_message.strip()}")
            prompt = "\n\n".join(s for s in prompt_sections if s.strip())

            stream = assistant.process_message_stream(
                prompt, context_label=context_pack.context_label
            )

            async def _pump():
                nonlocal chunks_count, total_chars
                async for frame_type, payload in stream:
                    if frame_type == "context":
                        yield _frame({"type": "context", "contextLabel": payload})
                    elif frame_type == "delta":
                        chunks_count += 1
                        total_chars += len(payload)
                        yield _frame({"type": "delta", "text": payload})
                    elif frame_type == "envelope":
                        action_links = _derive_action_links(
                            payload.get("recommendedNextActions", []), page_key
                        )
                        yield _frame(
                            {
                                "type": "envelope",
                                "followUpPrompts": payload.get("followUpPrompts", []),
                                "recommendedNextActions": payload.get(
                                    "recommendedNextActions", []
                                ),
                                "actionLinks": action_links,
                                "warning": payload.get("warning"),
                            }
                        )
                    elif frame_type == "error":
                        yield _frame(
                            {"type": "error", "message": payload.get("message", "")}
                        )

            pump = _pump()
            try:
                while True:
                    piece = await asyncio.wait_for(pump.__anext__(), timeout=45)
                    yield piece
            except StopAsyncIteration:
                pass
            except asyncio.TimeoutError:
                yield _frame({"type": "error", "message": "响应超时，请简化问题重试"})
                logger.warning(
                    f"SSE timeout product={product_id} page={page_key} "
                    f"chunks_so_far={chunks_count}"
                )

            yield _frame({"type": "done"})

    except asyncio.CancelledError:
        logger.info(
            f"SSE cancelled product={product_id} page={page_key} "
            f"chunks_so_far={chunks_count}"
        )
        raise
    except Exception as exc:
        logger.warning(f"SSE error product={product_id} page={page_key} err={exc}")
        yield _frame({"type": "error", "message": f"AI 助手当前不可用：{exc}"})
        yield _frame({"type": "done"})
    finally:
        dur_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"SSE completed product={product_id} page={page_key} "
            f"chunks={chunks_count} chars={total_chars} duration_ms={dur_ms}"
        )
