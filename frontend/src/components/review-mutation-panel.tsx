"use client";

import { useEffect, useState, useTransition } from "react";

import type { ReviewPayload } from "@/lib/mock-data";

type Props = {
	payload: ReviewPayload;
	backendBaseUrl: string;
	onDecisionSubmitted?: (
		itemKey: string,
		response: ReviewMutationResponse,
		decisionLabel: string,
	) => void;
};

type ReviewMutationResponse = {
	reviewId: number;
	stats?: {
		total?: number;
		reviewed?: number;
		pending?: number;
	};
};

function buildReviewKey(
	item: NonNullable<ReviewPayload["review"]>["pendingItems"][number],
) {
	return `${item.term}::${item.campaignName}::${item.createdAt}`;
}

function formatDecisionLabel(relevance: string) {
	switch (relevance) {
		case "strong_core":
			return "强相关";
		case "generic":
			return "泛词";
		case "irrelevant":
			return "不相关";
		default:
			return relevance;
	}
}

export function ReviewMutationPanel({
	payload,
	backendBaseUrl,
	onDecisionSubmitted,
}: Props) {
	const review = payload.review;
	const productId = payload.productId;
	const [notes, setNotes] = useState<Record<string, string>>({});
	const [message, setMessage] = useState<string | null>(null);
	const [pending, startTransition] = useTransition();
	// Sprint A.1: 当前键盘焦点的 queue item index（默认第 1 项）
	const [focusedIndex, setFocusedIndex] = useState(0);

	const visibleItems = (review?.pendingItems ?? []).slice(0, 5);

	// Sprint A.1: 全局键盘快捷键 1=强相关 / 2=泛词 / 3=不相关 / ↑↓ 切换 / Esc 失焦
	useEffect(() => {
		function handleKey(e: KeyboardEvent) {
			// 用户在输入备注时不触发（textarea / input 拦截）
			const tag = (e.target as HTMLElement | null)?.tagName;
			if (tag === "TEXTAREA" || tag === "INPUT") return;
			// 修饰键组合不拦截（避免和浏览器/Cmd+K 冲突）
			if (e.metaKey || e.ctrlKey || e.altKey) return;

			if (visibleItems.length === 0) return;
			const item = visibleItems[focusedIndex];
			if (!item) return;

			if (e.key === "1") {
				e.preventDefault();
				submitDecision(item, "strong_core");
			} else if (e.key === "2") {
				e.preventDefault();
				submitDecision(item, "generic");
			} else if (e.key === "3") {
				e.preventDefault();
				submitDecision(item, "irrelevant");
			} else if (e.key === "ArrowDown") {
				e.preventDefault();
				setFocusedIndex((idx) =>
					Math.min(idx + 1, Math.max(0, visibleItems.length - 1)),
				);
			} else if (e.key === "ArrowUp") {
				e.preventDefault();
				setFocusedIndex((idx) => Math.max(idx - 1, 0));
			} else if (e.key === "Escape") {
				(document.activeElement as HTMLElement | null)?.blur?.();
			}
		}
		window.addEventListener("keydown", handleKey);
		return () => window.removeEventListener("keydown", handleKey);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [visibleItems.length, focusedIndex]);

	async function submitDecision(
		item: NonNullable<ReviewPayload["review"]>["pendingItems"][number],
		relevance: string,
	) {
		if (!productId) return;
		setMessage(null);
		startTransition(async () => {
			const response = await fetch(
				`${backendBaseUrl}/frontend/review/manual-reviews`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						product_id: productId,
						term: item.term,
						term_type: item.termType,
						campaign_id: item.campaignId ?? null,
						relevance,
						notes: notes[item.term] || undefined,
					}),
				},
			);
			if (!response.ok) {
				const body = await response
					.json()
					.catch(() => ({ detail: "提交失败" }));
				setMessage(body.detail ?? "提交失败");
				return;
			}
			const body = (await response
				.json()
				.catch(() => ({}))) as ReviewMutationResponse;
			setMessage(
				`已提交 ${item.term} 的人工审核：${formatDecisionLabel(relevance)}`,
			);
			onDecisionSubmitted?.(
				buildReviewKey(item),
				body,
				formatDecisionLabel(relevance),
			);
			setNotes((current) => {
				const next = { ...current };
				delete next[item.term];
				return next;
			});
		});
	}

	return (
		<section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
			<div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">
				Write Path
			</div>
			<h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">
				审核操作
			</h3>
			<p className="mt-3 text-sm leading-relaxed text-zinc-500">
				直接在新前端里提交人工相关性判断，刷新后队列会减少。
				{" "}
				<span className="text-zinc-400">
					快捷键：<kbd className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px]">1</kbd>=强相关 ·{" "}
					<kbd className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px]">2</kbd>=泛词 ·{" "}
					<kbd className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px]">3</kbd>=不相关 ·{" "}
					<kbd className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px]">↑↓</kbd>=切换
				</span>
			</p>
			<div className="mt-5 space-y-4">
				{visibleItems.map((item, idx) => {
					const isFocused = idx === focusedIndex;
					const history = item.historicalDecisions ?? [];
					return (
						<div
							key={buildReviewKey(item)}
							onClick={() => setFocusedIndex(idx)}
							className={
								"rounded-2xl bg-zinc-50 p-4 cursor-pointer transition " +
								(isFocused
									? "ring-2 ring-amber-500 ring-offset-2 ring-offset-white"
									: "hover:bg-zinc-100")
							}
						>
							<div className="flex items-start justify-between gap-3">
								<div className="text-sm font-medium text-zinc-950">{item.term}</div>
								{typeof item.clusterId === "number" && item.clusterId >= 0 ? (
									<span
										title={`相似词簇 #${item.clusterId}`}
										className="shrink-0 rounded bg-zinc-200 px-1.5 py-0.5 text-[10px] font-mono text-zinc-600"
									>
										簇#{item.clusterId}
									</span>
								) : null}
							</div>
							<div className="mt-1 text-sm text-zinc-500">
								{item.campaignName} ｜ {item.termType}
							</div>
							{history.length > 0 ? (
								<details className="mt-2 text-[12px] text-amber-700">
									<summary className="cursor-pointer hover:underline">
										⚠ 历史决策 {history.length} 条 — 此词此前已被审过
									</summary>
									<ul className="mt-1.5 space-y-1 pl-3">
										{history.slice(0, 3).map((h, hi) => (
											<li key={hi} className="text-zinc-600">
												<span className="font-mono">{h.decidedAt}</span> ·{" "}
												<span className="font-medium">{h.decision}</span>
												{h.scope === "global" ? " (全局)" : ""}
												{h.notes ? ` — ${h.notes}` : ""}
											</li>
										))}
									</ul>
								</details>
							) : null}
							<textarea
								value={notes[item.term] ?? ""}
								onChange={(e) =>
									setNotes((current) => ({
										...current,
										[item.term]: e.target.value,
									}))
								}
								className="mt-3 min-h-20 w-full rounded-2xl border border-zinc-200 bg-white p-3 text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
								placeholder="补充人工判断备注（可选）"
							/>
							<div className="mt-3 flex flex-wrap gap-2">
								<button
									disabled={pending}
									onClick={() => submitDecision(item, "strong_core")}
									className="rounded-full bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50"
								>
									标记强相关
								</button>
								<button
									disabled={pending}
									onClick={() => submitDecision(item, "generic")}
									className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-900 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50"
								>
									标记泛词
								</button>
								<button
									disabled={pending}
									onClick={() => submitDecision(item, "irrelevant")}
									className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-900 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50"
								>
									标记不相关
								</button>
							</div>
						</div>
					);
				})}
			</div>
			{message ? (
				<p className="mt-4 text-sm leading-relaxed text-zinc-500">{message}</p>
			) : null}
		</section>
	);
}
