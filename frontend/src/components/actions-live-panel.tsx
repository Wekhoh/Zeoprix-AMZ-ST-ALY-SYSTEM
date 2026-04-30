"use client";
/**
 * actions-live-panel — Phase 7.7 Amazon Ads 风
 * 骨架：metric cards + 操作卡（ActionsMutationPanel）+ 活动 log + ExecutionBatchBoard
 */
import { useEffect, useMemo, useState } from "react";
import { Info, Zap, Clock } from "lucide-react";

import { recordFrontendActivity } from "@/components/live-activity";
import { writePageContext } from "@/components/page-context";
import { ActionsMutationPanel } from "@/components/actions-mutation-panel";
import { ExecutionBatchBoard } from "@/components/workbench-sections";
import type {
	ActionsPayload,
	ExecutionBatch,
	WeeklyCompareData,
	WeeklyCompareDailyPoint,
} from "@/lib/mock-data";

// Sprint B.3 — 内联 SVG sparkline（复用 analysis-detail-drawer 模式，避免引入 recharts）
function MiniSparkline({
	points,
	field,
}: {
	points: WeeklyCompareDailyPoint[];
	field: "spend" | "orders" | "sales";
}) {
	if (points.length === 0)
		return <div className="text-[11px] text-fg-subtle">无数据</div>;
	const values = points.map((p) => p[field] as number);
	const max = Math.max(...values, 1);
	const min = Math.min(...values, 0);
	const range = max - min || 1;
	const stepX = points.length > 1 ? 100 / (points.length - 1) : 0;
	const path = values
		.map((v, i) => {
			const x = (i * stepX).toFixed(2);
			const y = (48 - ((v - min) / range) * 44 - 2).toFixed(2);
			return `${i === 0 ? "M" : "L"}${x},${y}`;
		})
		.join(" ");
	return (
		<svg
			viewBox="0 0 100 48"
			preserveAspectRatio="none"
			className="w-full h-full"
		>
			<path d={path} fill="none" stroke="var(--accent)" strokeWidth={1.5} />
		</svg>
	);
}

function fmtDelta(d: number) {
	const pct = (d * 100).toFixed(1);
	const sign = d > 0 ? "▲" : d < 0 ? "▼" : "·";
	const tone =
		d > 0 ? "text-success-fg" : d < 0 ? "text-error-fg" : "text-fg-muted";
	return { sign, pct, tone };
}

function WeeklyCompareSection({ data }: { data?: WeeklyCompareData }) {
	if (!data) return null;
	const sd = fmtDelta(data.delta.spend);
	const od = fmtDelta(data.delta.orders);
	const lt = fmtDelta(data.delta.sales);
	const cards = [
		{
			label: "花费",
			thisV: data.thisWeek.spend,
			lastV: data.lastWeek.spend,
			d: sd,
			fmt: (n: number) => `$${n.toFixed(2)}`,
			field: "spend" as const,
		},
		{
			label: "订单",
			thisV: data.thisWeek.orders,
			lastV: data.lastWeek.orders,
			d: od,
			fmt: (n: number) => String(n),
			field: "orders" as const,
		},
		{
			label: "销售",
			thisV: data.thisWeek.sales,
			lastV: data.lastWeek.sales,
			d: lt,
			fmt: (n: number) => `$${n.toFixed(2)}`,
			field: "sales" as const,
		},
	];
	return (
		<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
			<div className="px-4 py-3 border-b border-border flex items-baseline gap-3">
				<h2 className="text-fg">本周 vs 上周</h2>
				<span className="text-[12px] text-fg-muted">
					14 天日序列 · 最近 7 天 vs 之前 7 天
				</span>
			</div>
			<div className="p-4 grid gap-4 md:grid-cols-3">
				{cards.map((m) => (
					<div key={m.label}>
						<div className="text-[11px] text-fg-subtle mb-1">{m.label}</div>
						<div className="flex items-baseline gap-2 flex-wrap">
							<span className="text-[20px] font-bold tabular-nums text-fg">
								{m.fmt(m.thisV)}
							</span>
							<span className={`text-[12px] font-semibold ${m.d.tone}`}>
								{m.d.sign} {m.d.pct}%
							</span>
						</div>
						<div className="text-[11px] text-fg-muted mt-0.5">
							上周 {m.fmt(m.lastV)}
						</div>
						<div className="mt-2 h-12">
							<MiniSparkline points={data.dailySeries} field={m.field} />
						</div>
					</div>
				))}
			</div>
		</section>
	);
}

type Props = {
	payload: ActionsPayload;
	backendBaseUrl: string;
};

type BatchMutationResponse = {
	id?: number;
	batch_code?: string;
	batch_type?: string;
	status?: string;
	summary?: {
		item_count?: number;
		spend_total?: number;
		sales_total?: number;
		items?: Array<{
			term?: string;
			suggested_action?: string;
			action_type?: string;
			spend?: number;
			sales?: number;
		}>;
	};
	verdict?: string;
	effect_summary?: {
		status?: string;
		summary?: string;
		top_improving_terms?: string[];
		top_risky_terms?: string[];
	};
};

function normalizeBatch(response: BatchMutationResponse): ExecutionBatch {
	return {
		id: response.id,
		code: response.batch_code ?? "批次",
		type: response.batch_type ?? "执行批次",
		status: response.status ?? "draft",
		itemCount: response.summary?.item_count ?? 0,
		spend: `$${Number(response.summary?.spend_total ?? 0).toFixed(2)}`,
		sales: `$${Number(response.summary?.sales_total ?? 0).toFixed(2)}`,
		verdict: response.effect_summary?.status ?? response.verdict ?? "待观察",
		summary: response.effect_summary?.summary ?? "暂无批次说明。",
		improving: response.effect_summary?.top_improving_terms ?? [],
		risky: response.effect_summary?.top_risky_terms ?? [],
		itemsPreview: (response.summary?.items ?? []).slice(0, 5).map((item) => ({
			term: item.term ?? "未命名词",
			action: item.suggested_action ?? item.action_type ?? "待执行",
			spend: `$${Number(item.spend ?? 0).toFixed(2)}`,
		})),
		itemsDetail: (response.summary?.items ?? []).map((item) => ({
			term: item.term ?? "未命名词",
			action: item.suggested_action ?? item.action_type ?? "待执行",
			actionType: item.action_type ?? "pending",
			spend: `$${Number(item.spend ?? 0).toFixed(2)}`,
			sales: `$${Number(item.sales ?? 0).toFixed(2)}`,
		})),
	};
}

function buildActionLog(line: string, previous: string[]) {
	return [line, ...previous].slice(0, 4);
}

export function ActionsLivePanel({ payload, backendBaseUrl }: Props) {
	const [executionBatches, setExecutionBatches] = useState<ExecutionBatch[]>(
		payload.executionBatches ?? [],
	);
	const [actions, setActions] = useState(
		payload.actions ?? {
			negativeCount: 0,
			manualCount: 0,
			conflictCount: 0,
			latestBatchCode: null as string | null,
		},
	);
	const [activityLog, setActivityLog] = useState<string[]>([]);

	const latestBatch = executionBatches[0];

	useEffect(() => {
		const previewTerms = latestBatch?.itemsPreview
			?.slice(0, 3)
			.map((item) => item.term)
			.join("、");
		writePageContext(payload.productId, "actions", {
			summary: `待执行：否词 ${actions.negativeCount}、手动补量 ${actions.manualCount}、分歧词 ${actions.conflictCount}；最近批次 ${latestBatch?.code ?? actions.latestBatchCode ?? "暂无"}${previewTerms ? `，重点词 ${previewTerms}` : ""}。`,
			latest_batch_code: latestBatch?.code ?? actions.latestBatchCode ?? null,
			latest_batch_status: latestBatch?.status ?? null,
			latest_batch_terms: previewTerms ?? null,
			negative_count: actions.negativeCount,
			manual_count: actions.manualCount,
			conflict_count: actions.conflictCount,
		});
	}, [actions, latestBatch, payload.productId]);

	const mutationPanelPayload = useMemo(
		() => ({
			...payload,
			actions,
			executionBatches,
		}),
		[actions, executionBatches, payload],
	);

	function handleBatchCreated(
		response: BatchMutationResponse,
		batchType: string,
	) {
		const batch = normalizeBatch(response);
		setExecutionBatches((current) =>
			[batch, ...current.filter((item) => item.id !== batch.id)].slice(0, 5),
		);
		setActions((current) => ({
			...current,
			latestBatchCode: batch.code,
		}));
		const line = `${batchType === "negative" ? "已生成否词批次" : "已生成手动批次"} ${batch.code}，覆盖 ${batch.itemCount} 项。`;
		setActivityLog((current) => buildActionLog(line, current));
		recordFrontendActivity(payload.productId, {
			label: "最近执行",
			title: `${batch.code} 已创建`,
			detail: line,
			href: "/actions",
		});
	}

	function handleBatchUpdated(response: BatchMutationResponse) {
		const batch = normalizeBatch(response);
		setExecutionBatches((current) =>
			current.map((item) => (item.id === batch.id ? batch : item)),
		);
		setActions((current) => ({
			...current,
			latestBatchCode: batch.code,
		}));
		const line = `批次 ${batch.code} 已更新为 ${batch.status}。`;
		setActivityLog((current) => buildActionLog(line, current));
		recordFrontendActivity(payload.productId, {
			label: "最近执行",
			title: `${batch.code} 状态已更新`,
			detail: line,
			href: "/actions",
		});
	}

	const metricItems: Array<{ label: string; value: string; hint: string }> = [
		{
			label: "否词待执行",
			value: String(actions.negativeCount ?? 0),
			hint: "等待批次执行",
		},
		{
			label: "手动补量",
			value: String(actions.manualCount ?? 0),
			hint: "建议手动投放",
		},
		{
			label: "分歧词",
			value: String(actions.conflictCount ?? 0),
			hint: "需人工拍板",
		},
		{
			label: "最近批次",
			value: latestBatch?.code ?? actions.latestBatchCode ?? "暂无",
			hint: latestBatch?.status ?? "尚未生成批次",
		},
	];

	return (
		<div className="space-y-5">
			{/* ═══ 1. Metric cards ═══ */}
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
										: "text-[14px] font-mono")
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
			</div>

			{/* ═══ 1.5 Sprint B.3 — 本周 vs 上周对比 + 14 天 sparkline ═══ */}
			<WeeklyCompareSection data={payload.weeklyCompare} />

			{/* ═══ 2. 操作卡 + 活动 log ═══ */}
			<div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
				<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
					<div className="flex items-center justify-between px-4 py-3 border-b border-border">
						<div className="flex items-center gap-2">
							<Zap className="h-3.5 w-3.5 text-accent-strong" />
							<h2 className="text-fg">批次执行操作</h2>
							<span className="text-[12px] text-fg-muted">
								生成 / 更新 / 导出
							</span>
						</div>
					</div>
					<div className="p-4">
						<ActionsMutationPanel
							payload={mutationPanelPayload}
							backendBaseUrl={backendBaseUrl}
							onBatchCreated={handleBatchCreated}
							onBatchUpdated={handleBatchUpdated}
						/>
					</div>
				</section>

				<aside className="space-y-4">
					{activityLog.length > 0 ? (
						<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
							<div className="flex items-center justify-between px-4 py-3 border-b border-border">
								<div className="flex items-center gap-2">
									<Clock className="h-3.5 w-3.5 text-fg-muted" />
									<h2 className="text-fg">最近执行</h2>
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
							<h2 className="text-fg">最近批次详情</h2>
						</div>
						<div className="p-4 space-y-2.5 text-[13px] leading-[1.55]">
							{latestBatch ? (
								<>
									<div className="flex items-center gap-2 flex-wrap">
										<span className="font-mono text-[12px] px-1.5 py-0.5 border border-border rounded text-fg">
											{latestBatch.code}
										</span>
										<span className="inline-flex items-center px-1.5 py-0.5 text-[11px] rounded bg-accent-bg text-accent-strong font-semibold">
											{latestBatch.type}
										</span>
										<span className="inline-flex items-center px-1.5 py-0.5 text-[11px] rounded bg-bg-subtle text-fg-muted font-semibold">
											{latestBatch.status}
										</span>
									</div>
									<p className="text-fg">{latestBatch.verdict}</p>
									<p className="text-fg-muted text-[12.5px]">
										{latestBatch.summary}
									</p>
									<div className="flex items-center gap-4 text-[12px] text-fg-muted pt-1">
										<span>
											items:{" "}
											<span className="font-mono tabular-nums font-semibold text-fg">
												{latestBatch.itemCount}
											</span>
										</span>
										<span>
											spend:{" "}
											<span className="font-mono tabular-nums text-fg">
												{latestBatch.spend}
											</span>
										</span>
										<span>
											sales:{" "}
											<span className="font-mono tabular-nums text-fg">
												{latestBatch.sales}
											</span>
										</span>
									</div>
								</>
							) : (
								<p className="text-fg-muted">
									暂无已创建批次。请使用左侧面板生成第一个批次。
								</p>
							)}
						</div>
					</section>
				</aside>
			</div>

			{/* ═══ 3. Execution Batch Board (全部批次) ═══ */}
			<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="flex items-center justify-between px-4 py-3 border-b border-border">
					<div className="flex items-baseline gap-3">
						<h2 className="text-fg">全部批次</h2>
						<span className="text-[12px] text-fg-muted">
							{executionBatches.length} batches
						</span>
					</div>
				</div>
				<div className="p-4">
					<ExecutionBatchBoard executionBatches={executionBatches} />
				</div>
			</section>
		</div>
	);
}
