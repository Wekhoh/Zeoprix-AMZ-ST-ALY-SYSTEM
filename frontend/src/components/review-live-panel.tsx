"use client";
/**
 * review-live-panel — Phase 7.6 Amazon Ads 风
 * 骨架：metric cards + 左 ReviewMutationPanel (包裹卡) + 右 队列 + 活动 log
 */
import { useEffect, useMemo, useState } from "react";
import { Info, ClipboardCheck, ListTodo } from "lucide-react";

import { recordFrontendActivity } from "@/components/live-activity";
import { writePageContext } from "@/components/page-context";
import { ReviewMutationPanel } from "@/components/review-mutation-panel";
import type { ReviewPayload } from "@/lib/mock-data";

type Props = {
	payload: ReviewPayload;
	backendBaseUrl: string;
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

export function ReviewLivePanel({ payload, backendBaseUrl }: Props) {
	const [reviewState, setReviewState] = useState(
		payload.review ?? {
			stats: { total: 0, reviewed: 0, pending: 0 },
			pendingItems: [],
		},
	);
	const [activityLog, setActivityLog] = useState<string[]>([]);

	useEffect(() => {
		const queueTerms = reviewState.pendingItems
			.slice(0, 3)
			.map((item) => item.term)
			.join("、");
		writePageContext(payload.productId, "review", {
			summary: `待审核 ${reviewState.stats.pending ?? 0} 条，已审核 ${reviewState.stats.reviewed ?? 0} 条${queueTerms ? `；队列重点词 ${queueTerms}` : ""}。`,
			pending_count: reviewState.stats.pending ?? 0,
			reviewed_count: reviewState.stats.reviewed ?? 0,
			queue_terms: queueTerms,
		});
	}, [payload.productId, reviewState]);

	const mutationPayload = useMemo(
		() => ({
			...payload,
			review: reviewState,
		}),
		[payload, reviewState],
	);

	function handleDecisionSubmitted(
		itemKey: string,
		response: ReviewMutationResponse,
		decisionLabel: string,
	) {
		const target = reviewState.pendingItems.find(
			(item) => buildReviewKey(item) === itemKey,
		);
		setReviewState((current) => ({
			stats: {
				total: response.stats?.total ?? current.stats.total,
				reviewed: response.stats?.reviewed ?? current.stats.reviewed,
				pending:
					response.stats?.pending ?? Math.max(current.stats.pending - 1, 0),
			},
			pendingItems: current.pendingItems.filter(
				(item) => buildReviewKey(item) !== itemKey,
			),
		}));
		if (target) {
			const line = `已将 ${target.term} 标记为${decisionLabel}。`;
			setActivityLog((current) => [line, ...current].slice(0, 4));
			recordFrontendActivity(payload.productId, {
				label: "最近审核",
				title: `${target.term} 已人工拍板`,
				detail: line,
				href: "/review",
			});
		}
	}

	const total = reviewState.stats.total ?? 0;
	const reviewed = reviewState.stats.reviewed ?? 0;
	const pending = reviewState.stats.pending ?? 0;
	const completionRate = total > 0 ? Math.round((reviewed / total) * 100) : 0;

	const metricItems: Array<{ label: string; value: string; hint: string }> = [
		{ label: "总数", value: String(total), hint: "当前分析快照条数" },
		{
			label: "已审核",
			value: String(reviewed),
			hint: "人工已拍板结果",
		},
		{ label: "待审核", value: String(pending), hint: "分歧或冲突待定" },
		{
			label: "完成率",
			value: `${completionRate}%`,
			hint: "已审核 / 总数",
		},
	];

	return (
		<div className="space-y-5">
			{/* ═══ 1. Metric cards + 进度条 ═══ */}
			<div className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="grid grid-cols-2 md:grid-cols-4">
					{metricItems.map((m, i) => (
						<div
							key={m.label}
							className={
								"px-4 py-3.5 border-border " +
								(i % 2 !== 0 ? "border-l " : "") +
								(i % 4 !== 0 ? "md:border-l " : "md:border-l-0 ") +
								(i >= 2 ? "border-t " : "") +
								(i >= 4 ? "md:border-t " : "md:border-t-0")
							}
						>
							<div className="flex items-center gap-1 text-[12px] font-semibold text-fg mb-1.5">
								<span>{m.label}</span>
								<Info className="h-3 w-3 text-fg-subtle" />
							</div>
							<div
								className={
									"font-bold text-fg leading-none " +
									(/^\d/.test(m.value)
										? "text-[20px] tabular-nums"
										: "text-[14px]")
								}
							>
								{m.value}
							</div>
							<span className="block text-[12px] text-fg-subtle mt-2">
								{m.hint}
							</span>
						</div>
					))}
				</div>
				<div className="px-4 py-3 border-t border-border">
					<div className="flex items-center gap-3">
						<span className="text-[11px] uppercase tracking-wide text-fg-subtle font-semibold">
							progress
						</span>
						<div className="flex-1 h-2 rounded-full bg-bg-subtle overflow-hidden">
							<div
								className="h-full bg-accent rounded-full transition-all"
								style={{ width: `${completionRate}%` }}
							/>
						</div>
						<span className="font-mono text-[12px] tabular-nums text-fg-muted min-w-[60px] text-right">
							{reviewed} / {total}
						</span>
					</div>
				</div>
			</div>

			{/* ═══ 2. Main 2-col ═══ */}
			<div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
				<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
					<div className="flex items-center justify-between px-4 py-3 border-b border-border">
						<div className="flex items-baseline gap-3">
							<h2 className="text-fg">人工审核操作</h2>
							<span className="text-[12px] text-fg-muted">
								对每条分歧词选择最终判断
							</span>
						</div>
					</div>
					<div className="p-4">
						<ReviewMutationPanel
							payload={mutationPayload}
							backendBaseUrl={backendBaseUrl}
							onDecisionSubmitted={handleDecisionSubmitted}
						/>
					</div>
				</section>

				<aside className="space-y-4">
					{activityLog.length > 0 ? (
						<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
							<div className="flex items-center justify-between px-4 py-3 border-b border-border">
								<div className="flex items-center gap-2">
									<ClipboardCheck className="h-3.5 w-3.5 text-accent-strong" />
									<h2 className="text-fg">最近审核</h2>
								</div>
								<span className="text-[12px] text-fg-muted">
									{activityLog.length}
								</span>
							</div>
							<ul className="divide-y divide-border">
								{activityLog.map((item, i) => (
									<li
										key={`${item}-${i}`}
										className="flex items-start gap-2 px-4 py-2.5"
									>
										<span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-success" />
										<span className="flex-1 text-[12.5px] text-fg-muted leading-[1.5]">
											{item}
										</span>
									</li>
								))}
							</ul>
						</section>
					) : null}

					<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
						<div className="flex items-center justify-between px-4 py-3 border-b border-border">
							<div className="flex items-center gap-2">
								<ListTodo className="h-3.5 w-3.5 text-fg-muted" />
								<h2 className="text-fg">待审核队列</h2>
							</div>
							<span className="text-[12px] text-fg-muted">
								{reviewState.pendingItems.length} 条
							</span>
						</div>
						{reviewState.pendingItems.length ? (
							<ul className="divide-y divide-border max-h-[520px] overflow-y-auto">
								{reviewState.pendingItems.map((item) => (
									<li
										key={buildReviewKey(item)}
										className="px-4 py-3 hover:bg-bg-subtle/40 transition-colors"
									>
										<div className="text-[13px] font-semibold text-fg truncate">
											{item.term}
										</div>
										<div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12px] text-fg-muted">
											<span className="inline-flex items-center px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-[11px] font-mono">
												{item.termType}
											</span>
											<span className="truncate max-w-[150px]">
												{item.campaignName}
											</span>
											<span className="font-mono tabular-nums text-fg-subtle">
												{item.createdAt}
											</span>
										</div>
									</li>
								))}
							</ul>
						) : (
							<div className="p-8 text-center text-[13px] text-fg-muted">
								当前没有待审核项。
							</div>
						)}
					</section>
				</aside>
			</div>
		</div>
	);
}
