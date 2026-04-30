"use client";
/**
 * workbench-sections.tsx — Ops Terminal 方向
 * 设计：单列 feed + inline metric strip + hairline 分区，完全不同于 codex 的 card grid
 */

import Link from "next/link";
import {
	Info,
	X,
	UserCircle,
	Globe,
	FileDown,
	ClipboardList,
	Upload as UploadIcon,
	CheckSquare,
	ArrowRight,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { DataHeadline } from "@/components/ui/data-headline";

import { DailyInsightsCard } from "@/components/daily-insights-card";
import { readFrontendActivity } from "@/components/live-activity";
import { writePageContext } from "@/components/page-context";

import {
	analysisRows as defaultAnalysisRows,
	executionBatches as defaultExecutionBatches,
	structureBuckets as defaultStructureBuckets,
	topActions as defaultTopActions,
	recentActivity as defaultRecentActivity,
	trendBars as defaultTrendBars,
	trendCards as defaultTrendCards,
	workbenchStats as defaultWorkbenchStats,
	type AnalysisRow,
	type ExecutionBatch,
	type StructureBucket,
	type TopAction,
	type RecentActivityItem,
	type TrendBar,
	type TrendCard,
	type WorkbenchStat,
} from "@/lib/mock-data";

import { Badge } from "@/components/ui/badge";

/* ==========================================================
   SectionHead — 委托给 DataHeadline（Phase 5 editorial）
   ========================================================== */
function SectionHead({
	code,
	label,
	count,
	action,
	live = false,
}: {
	code: string;
	label: string;
	count?: string;
	action?: React.ReactNode;
	live?: boolean;
}) {
	return (
		<DataHeadline
			eyebrow={code}
			title={label}
			count={count}
			action={action}
			live={live}
		/>
	);
}

/* ==========================================================
   TrendChart — 大 SVG 折线（area fill + gradient + endpoint）
   ========================================================== */
function TrendChart({
	bars,
	height = 140,
}: {
	bars: TrendBar[];
	height?: number;
}) {
	if (!bars || bars.length === 0) return null;
	const width = 800;
	const padX = 0;
	const padY = 8;
	const values = bars.map((b) => Number(b.value) || 0);
	const maxV = Math.max(...values, 1);
	const minV = Math.min(...values, 0);
	const rangeV = Math.max(maxV - minV, 1);
	const stepX = (width - padX * 2) / Math.max(bars.length - 1, 1);
	const toY = (v: number) =>
		height - padY - ((v - minV) / rangeV) * (height - padY * 2);
	const points = values
		.map((v, i) => `${(padX + i * stepX).toFixed(1)},${toY(v).toFixed(1)}`)
		.join(" ");
	const areaPath =
		`M${padX.toFixed(1)},${(height - padY).toFixed(1)} ` +
		values
			.map((v, i) => `L${(padX + i * stepX).toFixed(1)},${toY(v).toFixed(1)}`)
			.join(" ") +
		` L${(padX + (bars.length - 1) * stepX).toFixed(1)},${(height - padY).toFixed(1)} Z`;
	const lastX = padX + (bars.length - 1) * stepX;
	const lastY = toY(values[values.length - 1]);

	return (
		<svg
			viewBox={`0 0 ${width} ${height}`}
			className="w-full"
			preserveAspectRatio="none"
			aria-hidden="true"
			style={{ height: `${height}px` }}
		>
			<defs>
				<linearGradient id="trend-area" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0%" stopColor="currentColor" stopOpacity="0.18" />
					<stop offset="100%" stopColor="currentColor" stopOpacity="0" />
				</linearGradient>
			</defs>
			<path d={areaPath} fill="url(#trend-area)" className="text-accent" />
			<polyline
				points={points}
				fill="none"
				stroke="currentColor"
				strokeWidth="1.5"
				strokeLinejoin="round"
				strokeLinecap="round"
				className="text-accent"
			/>
			{/* endpoint dot + pulse */}
			<circle cx={lastX} cy={lastY} r="3.5" className="fill-accent" />
			<circle
				cx={lastX}
				cy={lastY}
				r="6"
				className="fill-accent/30 animate-ping origin-center"
				style={{ transformOrigin: `${lastX}px ${lastY}px` }}
			/>
		</svg>
	);
}

/* ==========================================================
   WorkbenchOverview — 重新设计（Ops Terminal 方向）
   ========================================================== */

export function WorkbenchOverview({
	workbenchStats = defaultWorkbenchStats,
	topActions = defaultTopActions,
	productId = null,
	recentActivity = defaultRecentActivity,
	trendCards = defaultTrendCards,
	trendBars = defaultTrendBars,
	structureBuckets = defaultStructureBuckets,
}: {
	workbenchStats?: WorkbenchStat[];
	topActions?: TopAction[];
	productId?: number | null;
	recentActivity?: RecentActivityItem[];
	trendCards?: TrendCard[];
	trendBars?: TrendBar[];
	structureBuckets?: StructureBucket[];
}) {
	const [localActivity, setLocalActivity] = useState<RecentActivityItem[]>([]);

	useEffect(() => {
		setLocalActivity(readFrontendActivity(productId));
	}, [productId]);

	const mergedActivity = useMemo(() => {
		const seen = new Set<string>();
		return [...localActivity, ...recentActivity]
			.filter((item) => {
				const key = `${item.label}-${item.title}`;
				if (seen.has(key)) return false;
				seen.add(key);
				return true;
			})
			.slice(0, 5);
	}, [localActivity, recentActivity]);

	useEffect(() => {
		writePageContext(productId, "workbench", {
			summary: `当前阶段 ${workbenchStats[0]?.value ?? "待分析"}；最近分析 ${workbenchStats[1]?.value ?? "暂无"}；今天优先动作 ${topActions[0]?.title ?? "暂无"}${mergedActivity[0]?.title ? `；最近动态 ${mergedActivity[0].title}` : ""}。`,
			stage: workbenchStats[0]?.value ?? null,
			latest_analysis: workbenchStats[1]?.value ?? null,
			top_action: topActions[0]?.title ?? null,
			latest_activity: mergedActivity[0]?.title ?? null,
		});
	}, [mergedActivity, productId, topActions, workbenchStats]);

	const totalStructure = useMemo(
		() => structureBuckets.reduce((s, b) => s + (Number(b.count) || 0), 0),
		[structureBuckets],
	);
	const maxStructure = useMemo(
		() => Math.max(...structureBuckets.map((b) => Number(b.count) || 0), 1),
		[structureBuckets],
	);

	const termsValue = workbenchStats[3]?.value?.match(/(\d+)\s*条/)?.[1] ?? "—";
	const stage = workbenchStats[0]?.value ?? "待分析";
	const snapshots = workbenchStats[2]?.value?.split(" ")[0] ?? "0";

	// Amazon Ads 风：从 trendCards[0].detail 解析订单/销售额/ACOS
	const firstTrend = trendCards[0]?.detail ?? "";
	const ordersMatch = firstTrend.match(/订单\s*(\d+)/);
	const salesMatch = firstTrend.match(/销售额\s*\$?([\d.,]+)/);
	const acosMatch = firstTrend.match(/ACOS\s*([\d.]+%)/);

	const metricItems: Array<{
		label: string;
		value: string;
		href?: string;
	}> = [
		{ label: "搜索词", value: termsValue, href: "/analysis" },
		{ label: "分析快照", value: snapshots, href: "/analysis" },
		{ label: "今日待处理", value: String(topActions.length), href: "/actions" },
		{ label: "近 7 天销售", value: trendCards[0]?.value ?? "—" },
		{ label: "订单数", value: ordersMatch?.[1] ?? "—" },
		{ label: "广告花费", value: salesMatch?.[1] ? `$${salesMatch[1]}` : "—" },
		{ label: "ACOS", value: acosMatch?.[1] ?? "—" },
	];

	const topAction = topActions[0];
	const secondAction = topActions[1];

	return (
		<div className="space-y-5">
			{/* 1. Tab pills row */}
			<div className="flex flex-wrap items-center gap-2">
				<button
					type="button"
					className="px-3.5 h-8 rounded-full bg-bg-elevated border border-fg text-[13px] font-semibold text-fg"
				>
					All
				</button>
				<Link
					href="/actions"
					className="px-3.5 h-8 inline-flex items-center rounded-full bg-bg-elevated border border-border text-[13px] text-fg-muted hover:bg-bg-subtle hover:border-border-strong transition-colors"
				>
					今日动作
				</Link>
				<Link
					href="/analysis"
					className="px-3.5 h-8 inline-flex items-center rounded-full bg-bg-elevated border border-border text-[13px] text-fg-muted hover:bg-bg-subtle hover:border-border-strong transition-colors"
				>
					搜索词分析
				</Link>
				<Link
					href="/review"
					className="px-3.5 h-8 inline-flex items-center rounded-full bg-bg-elevated border border-border text-[13px] text-fg-muted hover:bg-bg-subtle hover:border-border-strong transition-colors"
				>
					审核中心
				</Link>
			</div>

			{/* 2. Metric cards row — Amazon Ads 风 */}
			<div className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 2xl:grid-cols-7">
					{metricItems.map((m, i) => (
						<div
							key={m.label}
							className={
								"px-4 py-3.5 border-border " +
								(i % 2 !== 0 ? "border-l " : "") +
								(i % 3 !== 0 ? "sm:border-l " : "sm:border-l-0 ") +
								(i % 4 !== 0 ? "md:border-l " : "md:border-l-0 ") +
								(i % 7 !== 0 ? "2xl:border-l " : "2xl:border-l-0 ") +
								(i >= 2 ? "border-t " : "") +
								(i >= 3 ? "sm:border-t " : "sm:border-t-0 ") +
								(i >= 4 ? "md:border-t " : "md:border-t-0 ") +
								(i >= 7 ? "2xl:border-t" : "2xl:border-t-0")
							}
						>
							<div className="flex items-center gap-1 text-[12px] font-semibold text-fg mb-1.5">
								<span>{m.label}</span>
								<Info className="h-3 w-3 text-fg-subtle" />
							</div>
							<div className="text-[20px] font-bold tabular-nums text-fg leading-none">
								{m.value}
							</div>
							{m.href ? (
								<Link
									href={m.href}
									className="inline-block text-[12px] text-link hover:underline mt-2"
								>
									View details
								</Link>
							) : (
								<span className="block text-[12px] text-fg-subtle mt-2">—</span>
							)}
						</div>
					))}
				</div>
			</div>

			{/* 3. Tool links */}
			<div className="flex items-center gap-4 text-[13px]">
				<button type="button" className="text-link hover:underline">
					Show all ({metricItems.length})
				</button>
				<span className="text-fg-subtle">|</span>
				<button type="button" className="text-link hover:underline">
					View chart only
				</button>
				<span className="text-fg-subtle">|</span>
				<button type="button" className="text-link hover:underline">
					Hide all
				</button>
			</div>

			{/* 4. Insight cards row */}
			<div className="grid gap-4 lg:grid-cols-3">
				{/* Card 1 — 今日待处理 */}
				<article className="bg-bg-elevated border border-border rounded-lg p-5 relative flex flex-col">
					<button
						type="button"
						className="absolute top-3 right-3 inline-flex h-6 w-6 items-center justify-center rounded-full text-fg-subtle hover:bg-bg-subtle hover:text-fg transition-colors"
						aria-label="关闭"
					>
						<X className="h-3.5 w-3.5" />
					</button>
					<h3 className="text-fg pr-6">今日待处理动作</h3>
					<p className="mt-1.5 text-[13px] font-semibold text-fg">
						{topAction?.title ?? "暂无待处理动作"}
					</p>
					<p className="mt-1.5 text-[13px] text-fg-muted leading-[1.55] flex-1">
						{topAction?.description ?? "当前没有检测到高优先级的待处理动作。"}
					</p>
					<div className="mt-4">
						<div className="text-[22px] font-bold tabular-nums text-fg leading-none">
							{topActions.length}{" "}
							<span className="text-[13px] font-normal text-fg-muted">
								of {topActions.length}
							</span>
						</div>
						<div className="mt-2 h-[3px] w-full rounded bg-bg-subtle overflow-hidden">
							<div
								className="h-full bg-accent"
								style={{ width: `${topActions.length > 0 ? 100 : 0}%` }}
							/>
						</div>
						<p className="mt-2 text-[12px] text-fg-muted">
							高优先级动作 · 最近分析生成
						</p>
					</div>
					<div className="flex flex-wrap gap-2 mt-3">
						<span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded-full bg-bg-subtle border border-border text-fg-muted">
							<UserCircle className="h-3 w-3" />1 Advertiser
						</span>
						<span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded-full bg-bg-subtle border border-border text-fg-muted">
							<Globe className="h-3 w-3" />
							{stage}
						</span>
					</div>
					<Link
						href="/actions"
						className="mt-4 text-[13px] text-link hover:underline"
					>
						查看操作清单
					</Link>
				</article>

				{/* Card 2 — 补量机会 */}
				<article className="bg-bg-elevated border border-border rounded-lg p-5 relative flex flex-col">
					<button
						type="button"
						className="absolute top-3 right-3 inline-flex h-6 w-6 items-center justify-center rounded-full text-fg-subtle hover:bg-bg-subtle hover:text-fg transition-colors"
						aria-label="关闭"
					>
						<X className="h-3.5 w-3.5" />
					</button>
					<h3 className="text-fg pr-6">补量机会</h3>
					<p className="mt-1.5 text-[13px] font-semibold text-fg">
						{secondAction?.title ?? "暂无补量建议"}
					</p>
					<p className="mt-1.5 text-[13px] text-fg-muted leading-[1.55] flex-1">
						{secondAction?.description ?? "当前没有待补量的机会词。"}
					</p>
					<div className="flex items-baseline gap-3 mt-4">
						<span className="text-[22px] font-bold tabular-nums text-fg leading-none">
							{secondAction ? "1" : "0"}
						</span>
						<span className="text-[12px] text-fg-muted">个推荐补量机会</span>
					</div>
					<div className="flex flex-wrap gap-2 mt-3">
						<span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded-full bg-bg-subtle border border-border text-fg-muted">
							<UserCircle className="h-3 w-3" />1 Advertiser
						</span>
						<span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded-full bg-bg-subtle border border-border text-fg-muted">
							<Globe className="h-3 w-3" />
							待人工拍板
						</span>
					</div>
					<Link
						href="/actions"
						className="mt-4 text-[13px] text-link hover:underline"
					>
						启动补量方案
					</Link>
				</article>

				{/* Card 3 — Performance */}
				<article className="bg-bg-elevated border border-border rounded-lg p-5 relative flex flex-col">
					<div className="flex items-baseline justify-between gap-2 mb-3 pr-6">
						<h3 className="text-fg">Performance</h3>
						<span className="text-[12px] text-fg-muted">近 30 天</span>
					</div>
					<div className="grid grid-cols-3 gap-3 mb-3">
						{trendCards.slice(0, 3).map((card, i) => {
							const colors = ["bg-violet-500", "bg-teal-500", "bg-pink-500"];
							return (
								<div key={card.label} className="space-y-1">
									<div className="inline-flex items-center gap-1 text-[11px] text-fg-muted">
										<span className={`h-2 w-2 rounded-sm ${colors[i % 3]}`} />
										<span>{card.label}</span>
									</div>
									<div className="text-[16px] font-bold tabular-nums text-fg leading-tight">
										{card.value}
									</div>
								</div>
							);
						})}
					</div>
					<div className="flex-1 min-h-[80px]">
						<TrendChart bars={trendBars} height={80} />
					</div>
					<Link
						href="/analysis"
						className="mt-3 text-[13px] text-link hover:underline"
					>
						查看完整分析 →
					</Link>
				</article>
			</div>

			{/* 4.5 今日 AI 洞察 — Sprint 4 · A3 */}
			<DailyInsightsCard productId={productId} />

			{/* 5. 搜索词结构 — Amazon campaigns table 风 */}
			<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="flex items-center justify-between px-4 py-3 border-b border-border">
					<div className="flex items-baseline gap-3">
						<h2 className="text-fg">搜索词结构</h2>
						<span className="text-[12px] text-fg-muted">
							{totalStructure} terms · {structureBuckets.length} buckets
						</span>
					</div>
					<Link
						href="/analysis"
						className="text-[13px] text-link hover:underline"
					>
						View filtered data
					</Link>
				</div>
				<div className="divide-y divide-border">
					{structureBuckets.map((bucket) => {
						const count = Number(bucket.count) || 0;
						const pct = Math.max(
							1,
							Math.min(100, (count / maxStructure) * 100),
						);
						const globalPct = totalStructure
							? ((count / totalStructure) * 100).toFixed(1)
							: "0.0";
						return (
							<div
								key={bucket.label}
								className="grid grid-cols-[minmax(120px,180px)_minmax(0,1fr)_72px_64px] items-center gap-4 px-4 py-3 hover:bg-bg-subtle/50 transition-colors"
							>
								<div className="text-[13px] font-medium text-fg truncate">
									{bucket.label}
								</div>
								<div className="relative h-[6px] rounded-full bg-bg-subtle overflow-hidden">
									<div
										className="absolute inset-y-0 left-0 rounded-full bg-accent"
										style={{ width: `${pct}%` }}
									/>
								</div>
								<div className="text-right text-[13px] font-mono tabular-nums font-semibold text-fg">
									{bucket.count}
								</div>
								<div className="text-right text-[13px] font-mono tabular-nums text-fg-muted">
									{globalPct}%
								</div>
							</div>
						);
					})}
				</div>
			</section>
		</div>
	);
}

/* ==========================================================
   OperationsStream — 左 最近批次 + 右 系统活动流
   Amazon Ads 后台 "Recent campaigns / Activity" 风
   ========================================================== */

function statusToneClass(status: string) {
	if (status.includes("已执行") || status.includes("完成"))
		return "bg-success-bg text-success-fg";
	if (
		status.includes("部分") ||
		status.includes("待人工") ||
		status.includes("分歧")
	)
		return "bg-warning-bg text-warning-fg";
	if (status.includes("失败") || status.includes("异常"))
		return "bg-error-bg text-error-fg";
	return "bg-bg-subtle text-fg-muted";
}

function activityIcon(label: string) {
	if (/(导入|上传|upload)/i.test(label)) return UploadIcon;
	if (/(审核|分歧|review)/i.test(label)) return CheckSquare;
	if (/(批次|执行|action)/i.test(label)) return ClipboardList;
	if (/(导出|export|备份)/i.test(label)) return FileDown;
	return ClipboardList;
}

function activityToneClass(label: string) {
	if (/(导入|上传|upload)/i.test(label)) return "bg-link text-on-primary";
	if (/(审核|分歧|review)/i.test(label)) return "bg-accent text-on-primary";
	if (/(批次|执行|action)/i.test(label)) return "bg-success text-on-primary";
	if (/(导出|export|备份)/i.test(label)) return "bg-fg-muted text-on-primary";
	return "bg-fg-subtle text-on-primary";
}

export function OperationsStream({
	executionBatches = defaultExecutionBatches,
	recentActivity = defaultRecentActivity,
}: {
	executionBatches?: ExecutionBatch[];
	recentActivity?: RecentActivityItem[];
}) {
	const batches = executionBatches.slice(0, 3);
	const activity = recentActivity.slice(0, 5);

	return (
		<section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px] mt-2">
			{/* ═══ 左：最近批次 ═══ */}
			<div className="bg-bg-elevated border border-border rounded-lg overflow-hidden flex flex-col">
				<div className="flex items-center justify-between px-4 py-3 border-b border-border">
					<div className="flex items-baseline gap-3">
						<h2 className="text-fg">最近批次</h2>
						<span className="text-[12px] text-fg-muted">
							{executionBatches.length} batches · {batches.length} shown
						</span>
					</div>
					<Link
						href="/actions"
						className="inline-flex items-center gap-1 text-[13px] text-link hover:underline"
					>
						查看全部 <ArrowRight className="h-3 w-3" />
					</Link>
				</div>
				{batches.length === 0 ? (
					<div className="p-8 text-center text-[13px] text-fg-muted">
						暂无执行批次
					</div>
				) : (
					<div className="divide-y divide-border">
						{batches.map((batch) => (
							<Link
								key={batch.code}
								href="/actions"
								className="block px-4 py-3 hover:bg-bg-subtle/60 transition-colors"
							>
								<div className="flex items-center gap-2 mb-1.5 flex-wrap">
									<span className="font-mono text-[12px] px-1.5 py-0.5 border border-border rounded text-fg">
										{batch.code}
									</span>
									<span className="inline-flex items-center px-1.5 py-0.5 text-[11px] rounded bg-accent-bg text-accent-strong font-semibold">
										{batch.type}
									</span>
									<span
										className={
											"inline-flex items-center px-1.5 py-0.5 text-[11px] rounded font-semibold " +
											statusToneClass(batch.status)
										}
									>
										{batch.status}
									</span>
									<span className="ml-auto text-[12px] text-fg-muted">
										<span className="font-mono tabular-nums text-fg font-semibold">
											{batch.itemCount}
										</span>{" "}
										items
									</span>
								</div>
								<p className="text-[13px] text-fg leading-[1.5] line-clamp-2">
									{batch.verdict}
								</p>
								<div className="mt-2 flex items-center gap-4 text-[12px] text-fg-muted">
									<span className="inline-flex items-baseline gap-1">
										<span>花费</span>
										<span className="font-mono tabular-nums text-fg">
											{batch.spend}
										</span>
									</span>
									<span className="inline-flex items-baseline gap-1">
										<span>销售</span>
										<span className="font-mono tabular-nums text-fg">
											{batch.sales}
										</span>
									</span>
									{batch.improving.length > 0 ? (
										<span className="inline-flex items-baseline gap-1">
											<span className="text-success-fg">+</span>
											<span className="font-mono tabular-nums text-success-fg">
												{batch.improving.length}
											</span>
										</span>
									) : null}
									{batch.risky.length > 0 ? (
										<span className="inline-flex items-baseline gap-1">
											<span className="text-warning-fg">!</span>
											<span className="font-mono tabular-nums text-warning-fg">
												{batch.risky.length}
											</span>
										</span>
									) : null}
								</div>
							</Link>
						))}
					</div>
				)}
			</div>

			{/* ═══ 右：系统活动流 ═══ */}
			<aside className="bg-bg-elevated border border-border rounded-lg overflow-hidden flex flex-col">
				<div className="flex items-center justify-between px-4 py-3 border-b border-border">
					<h2 className="text-fg">系统活动</h2>
					<span className="text-[12px] text-fg-muted">
						{activity.length} 条
					</span>
				</div>
				{activity.length === 0 ? (
					<div className="p-6 text-center text-[13px] text-fg-muted">
						暂无活动记录
					</div>
				) : (
					<ul className="divide-y divide-border">
						{activity.map((item, i) => {
							const Icon = activityIcon(item.label);
							const toneClass = activityToneClass(item.label);
							return (
								<li key={`${item.label}-${i}`}>
									{item.href ? (
										<Link
											href={item.href}
											className="flex items-start gap-3 px-4 py-3 hover:bg-bg-subtle/60 transition-colors"
										>
											<span
												className={
													"mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded " +
													toneClass
												}
											>
												<Icon className="h-3 w-3" />
											</span>
											<div className="flex-1 min-w-0">
												<div className="flex items-baseline gap-2">
													<span className="text-[11px] font-semibold uppercase tracking-wide text-fg-muted">
														{item.label}
													</span>
												</div>
												<p className="text-[13px] text-fg leading-[1.45] mt-0.5">
													{item.title}
												</p>
												{item.detail ? (
													<p className="text-[12px] text-fg-subtle leading-[1.45] mt-0.5 line-clamp-1">
														{item.detail}
													</p>
												) : null}
											</div>
										</Link>
									) : (
										<div className="flex items-start gap-3 px-4 py-3">
											<span
												className={
													"mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded " +
													toneClass
												}
											>
												<Icon className="h-3 w-3" />
											</span>
											<div className="flex-1 min-w-0">
												<span className="text-[11px] font-semibold uppercase tracking-wide text-fg-muted">
													{item.label}
												</span>
												<p className="text-[13px] text-fg leading-[1.45] mt-0.5">
													{item.title}
												</p>
												{item.detail ? (
													<p className="text-[12px] text-fg-subtle leading-[1.45] mt-0.5 line-clamp-1">
														{item.detail}
													</p>
												) : null}
											</div>
										</div>
									)}
								</li>
							);
						})}
					</ul>
				)}
			</aside>
		</section>
	);
}

/* ==========================================================
   AnalysisTable — token 迁移到新 DS（Sprint 3 后续重构）
   ========================================================== */

export function AnalysisTable({
	analysisRows = defaultAnalysisRows,
	onRowClick,
}: {
	analysisRows?: AnalysisRow[];
	// Sprint A.2: 行点击回调，传入 term —— 触发详情抽屉
	onRowClick?: (term: string) => void;
}) {
	return (
		<section className="space-y-4">
			<SectionHead
				code="TABLE"
				label="搜索词分析总览"
				count={`${analysisRows.length} rows${onRowClick ? " · 点击行看 30 天详情" : ""}`}
			/>
			<div className="border border-border rounded-md overflow-hidden">
				<table className="w-full border-collapse text-left text-[13px]">
					<thead className="bg-bg-subtle text-fg-subtle text-[12px] uppercase tracking-wider">
						<tr>
							<th className="px-3 py-2.5 font-medium">关键词</th>
							<th className="px-3 py-2.5 font-medium">类型</th>
							<th className="px-3 py-2.5 font-medium">规则</th>
							<th className="px-3 py-2.5 font-medium">动作</th>
							<th className="px-3 py-2.5 font-medium text-right">花费</th>
							<th className="px-3 py-2.5 font-medium text-right">订单</th>
							<th className="px-3 py-2.5 font-medium text-right">置信度</th>
						</tr>
					</thead>
					<tbody>
						{analysisRows.map((row) => (
							<tr
								key={row.term}
								onClick={onRowClick ? () => onRowClick(row.term) : undefined}
								className={
									"border-t border-border hover:bg-bg-subtle/40 transition" +
									(onRowClick ? " cursor-pointer" : "")
								}
							>
								<td className="px-3 py-2.5 font-mono text-[13px] font-medium text-fg">
									{row.term}
								</td>
								<td className="px-3 py-2.5 text-fg-muted">{row.type}</td>
								<td className="px-3 py-2.5 text-fg-muted">{row.rule}</td>
								<td className="px-3 py-2.5">
									<Badge>{row.action}</Badge>
								</td>
								<td className="px-3 py-2.5 text-right font-mono tabular-nums text-fg">
									{row.spend}
								</td>
								<td className="px-3 py-2.5 text-right font-mono tabular-nums text-fg">
									{row.orders}
								</td>
								<td className="px-3 py-2.5 text-right font-mono tabular-nums text-fg-muted">
									{row.confidence}
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</section>
	);
}

/* ==========================================================
   ExecutionBatchBoard — token 迁移到新 DS
   ========================================================== */

export function ExecutionBatchBoard({
	executionBatches = defaultExecutionBatches,
}: {
	executionBatches?: ExecutionBatch[];
}) {
	const [expandedCode, setExpandedCode] = useState<string | null>(
		executionBatches[0]?.code ?? null,
	);
	const [detailQuery, setDetailQuery] = useState<Record<string, string>>({});

	return (
		<section className="space-y-5">
			{executionBatches.map((batch) => {
				const isExpanded = expandedCode === batch.code;
				const query = (detailQuery[batch.code] ?? "").trim().toLowerCase();
				const detailRows = (batch.itemsDetail ?? []).filter((item) => {
					if (!query) return true;
					return [item.term, item.action, item.actionType].some((value) =>
						value.toLowerCase().includes(query),
					);
				});
				return (
					<div
						key={batch.code}
						className="border border-border rounded-md bg-bg-elevated p-5"
					>
						<div className="flex flex-wrap items-center gap-2">
							<span className="font-mono text-[12px] px-2 py-0.5 border border-border rounded text-fg">
								{batch.code}
							</span>
							<Badge>{batch.type}</Badge>
							<Badge tone="accent" dot>
								{batch.status}
							</Badge>
						</div>
						<div className="mt-4 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
							<div className="space-y-3">
								<div>
									<div className="text-[11px] uppercase tracking-[0.06em] text-fg-subtle">
										批次摘要
									</div>
									<div className="mt-1 text-[15px] font-semibold tracking-tight text-fg">
										{batch.verdict}
									</div>
									<p className="mt-1.5 text-[13px] leading-relaxed text-fg-muted">
										{batch.summary}
									</p>
								</div>
								<div className="grid grid-cols-2 gap-3 pt-2 border-t border-border">
									<div>
										<div className="text-[11px] uppercase tracking-[0.06em] text-fg-subtle">
											覆盖项数
										</div>
										<div className="mt-1 font-mono text-[16px] font-semibold text-fg tabular-nums">
											{batch.itemCount}
										</div>
									</div>
									<div>
										<div className="text-[11px] uppercase tracking-[0.06em] text-fg-subtle">
											花费 / 销售
										</div>
										<div className="mt-1 font-mono text-[16px] font-semibold text-fg tabular-nums">
											{batch.spend} / {batch.sales}
										</div>
									</div>
								</div>
							</div>
							<div className="grid grid-cols-2 gap-3">
								<div>
									<div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-success-fg">
										<span>+</span>
										<span>improving</span>
									</div>
									<ul className="mt-2 space-y-1 text-[13px] text-fg">
										{batch.improving.map((term) => (
											<li key={term} className="truncate">
												{term}
											</li>
										))}
									</ul>
								</div>
								<div>
									<div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-warning-fg">
										<span>!</span>
										<span>risky</span>
									</div>
									<ul className="mt-2 space-y-1 text-[13px] text-fg">
										{batch.risky.map((term) => (
											<li key={term} className="truncate">
												{term}
											</li>
										))}
									</ul>
								</div>
							</div>
						</div>
						{batch.itemsPreview?.length ? (
							<div className="mt-4 pt-4 border-t border-border">
								<div className="flex items-center justify-between gap-3">
									<div className="flex items-center gap-1.5 text-[12px] text-fg-muted">
										<span className="font-mono text-fg-subtle">&gt;</span>
										{isExpanded ? (
											<span>
												展开中 ·{" "}
												<span className="font-mono tabular-nums">
													{detailRows.length || batch.itemsPreview.length}
												</span>{" "}
												items
											</span>
										) : (
											<span>
												<span className="font-mono tabular-nums">
													{batch.itemsPreview.length}
												</span>{" "}
												items · click to expand
											</span>
										)}
									</div>
									<button
										onClick={() =>
											setExpandedCode((current) =>
												current === batch.code ? null : batch.code,
											)
										}
										className="text-[12px] px-2.5 py-1 border border-border rounded hover:bg-bg-subtle"
									>
										{isExpanded ? "收起" : "展开"}
									</button>
								</div>
								{isExpanded ? (
									<div className="mt-3 space-y-3">
										<input
											value={detailQuery[batch.code] ?? ""}
											onChange={(event) =>
												setDetailQuery((current) => ({
													...current,
													[batch.code]: event.target.value,
												}))
											}
											placeholder="grep 词或动作…"
											className="w-full rounded border border-border bg-bg px-3 py-2 text-[13px] text-fg outline-none placeholder:text-fg-subtle focus-visible:border-accent"
										/>
										<div className="overflow-hidden rounded border border-border">
											<table className="w-full border-collapse text-left text-[13px]">
												<thead className="bg-bg-subtle text-fg-subtle text-[12px] uppercase tracking-wider">
													<tr>
														<th className="px-3 py-2 font-medium">关键词</th>
														<th className="px-3 py-2 font-medium">动作</th>
														<th className="px-3 py-2 font-medium">类型</th>
														<th className="px-3 py-2 font-medium text-right">
															花费
														</th>
														<th className="px-3 py-2 font-medium text-right">
															销售
														</th>
													</tr>
												</thead>
												<tbody>
													{detailRows.length ? (
														detailRows.map((item) => (
															<tr
																key={`${batch.code}-${item.term}-${item.actionType}`}
																className="border-t border-border"
															>
																<td className="px-3 py-2 font-mono text-[13px] font-medium text-fg">
																	{item.term}
																</td>
																<td className="px-3 py-2 text-fg-muted">
																	{item.action}
																</td>
																<td className="px-3 py-2 text-fg-muted">
																	{item.actionType}
																</td>
																<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
																	{item.spend}
																</td>
																<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
																	{item.sales}
																</td>
															</tr>
														))
													) : (
														<tr className="border-t border-border">
															<td
																className="px-3 py-3 text-fg-muted"
																colSpan={5}
															>
																无匹配
															</td>
														</tr>
													)}
												</tbody>
											</table>
										</div>
									</div>
								) : (
									<div className="mt-3 flex flex-wrap gap-2">
										{batch.itemsPreview.slice(0, 3).map((item) => (
											<span
												key={`${batch.code}-${item.term}`}
												className="font-mono text-[12px] px-2 py-0.5 border border-border rounded text-fg"
											>
												{item.term}
											</span>
										))}
									</div>
								)}
							</div>
						) : null}
					</div>
				);
			})}
		</section>
	);
}
