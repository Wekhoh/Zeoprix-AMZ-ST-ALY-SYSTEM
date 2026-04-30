"use client";
/**
 * analysis-live-panel — Phase 7.5 Amazon Ads 风
 * 骨架：metric cards grid + tab pills + filter card + analysis table
 */
import { useEffect, useMemo, useState } from "react";
import { useSearchParams, usePathname, useRouter } from "next/navigation";
import { Search, Info } from "lucide-react";

import { writePageContext } from "@/components/page-context";
import type {
	AnalysisPayload,
	AnalysisRow,
	CampaignAggRow,
	AsinAggRow,
} from "@/lib/mock-data";
import { AnalysisTable } from "@/components/workbench-sections";
import { AnalysisDetailDrawer } from "@/components/analysis-detail-drawer";

type Props = {
	payload: AnalysisPayload;
};

type SortKey = "spend-desc" | "orders-desc" | "confidence-desc" | "term-asc";
type FocusMode = "all" | "stoploss" | "scale" | "review";
type ViewMode = "term" | "campaign" | "asin"; // Sprint B.1/B.2

const VIEW_OPTIONS: Array<[ViewMode, string]> = [
	["term", "搜索词"],
	["campaign", "广告活动"],
	["asin", "ASIN"],
];

function fmtMoney(n: number) {
	return `$${n.toFixed(2)}`;
}

function fmtPct(n: number) {
	return `${(n * 100).toFixed(1)}%`;
}

// Sprint B.1 — 简洁 campaign 聚合表
function CampaignAggTable({ rows }: { rows: CampaignAggRow[] }) {
	if (rows.length === 0) {
		return (
			<div className="bg-bg-elevated border border-border rounded-lg p-8 text-center text-[13px] text-fg-subtle">
				暂无广告活动聚合数据
			</div>
		);
	}
	const sorted = [...rows].sort((a, b) => b.spend - a.spend);
	return (
		<div className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
			<div className="px-4 py-3 border-b border-border flex items-baseline gap-3">
				<h2 className="text-fg">广告活动聚合 · {rows.length}</h2>
				<span className="text-[12px] text-fg-muted">按花费降序</span>
			</div>
			<div className="overflow-x-auto">
				<table className="w-full text-[12px]">
					<thead className="bg-bg-subtle text-fg-muted">
						<tr className="text-left">
							<th className="px-3 py-2 font-semibold">活动</th>
							<th className="px-3 py-2 font-semibold">匹配</th>
							<th className="px-3 py-2 font-semibold text-right">花费</th>
							<th className="px-3 py-2 font-semibold text-right">订单</th>
							<th className="px-3 py-2 font-semibold text-right">销售</th>
							<th className="px-3 py-2 font-semibold text-right">CVR</th>
							<th className="px-3 py-2 font-semibold text-right">ACOS</th>
							<th className="px-3 py-2 font-semibold text-right">词数</th>
						</tr>
					</thead>
					<tbody>
						{sorted.map((r, i) => (
							<tr
								key={`${r.campaignName}-${r.matchType}-${i}`}
								className="border-t border-border hover:bg-bg-subtle/50"
							>
								<td className="px-3 py-2 font-mono text-fg truncate max-w-[280px]">
									{r.campaignName}
								</td>
								<td className="px-3 py-2 text-fg-muted">{r.matchType}</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
									{fmtMoney(r.spend)}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
									{r.orders}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
									{fmtMoney(r.sales)}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
									{fmtPct(r.cvr)}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
									{fmtPct(r.acos)}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg-muted">
									{r.termCount}
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</div>
	);
}

// Sprint B.2 — 简洁 ASIN 聚合表
function AsinAggTable({ rows }: { rows: AsinAggRow[] }) {
	if (rows.length === 0) {
		return (
			<div className="bg-bg-elevated border border-border rounded-lg p-8 text-center text-[13px] text-fg-subtle">
				暂无 ASIN 聚合数据
			</div>
		);
	}
	const sorted = [...rows].sort((a, b) => b.spend - a.spend);
	return (
		<div className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
			<div className="px-4 py-3 border-b border-border flex items-baseline gap-3">
				<h2 className="text-fg">ASIN 聚合 · {rows.length}</h2>
				<span className="text-[12px] text-fg-muted">按花费降序</span>
			</div>
			<div className="overflow-x-auto">
				<table className="w-full text-[12px]">
					<thead className="bg-bg-subtle text-fg-muted">
						<tr className="text-left">
							<th className="px-3 py-2 font-semibold">ASIN</th>
							<th className="px-3 py-2 font-semibold">产品</th>
							<th className="px-3 py-2 font-semibold text-right">花费</th>
							<th className="px-3 py-2 font-semibold text-right">订单</th>
							<th className="px-3 py-2 font-semibold text-right">销售</th>
							<th className="px-3 py-2 font-semibold text-right">CVR</th>
							<th className="px-3 py-2 font-semibold text-right">ACOS</th>
							<th className="px-3 py-2 font-semibold text-right">词数</th>
							<th className="px-3 py-2 font-semibold text-right">活动</th>
						</tr>
					</thead>
					<tbody>
						{sorted.map((r) => (
							<tr
								key={r.asin}
								className="border-t border-border hover:bg-bg-subtle/50"
							>
								<td className="px-3 py-2 font-mono text-fg">{r.asin}</td>
								<td className="px-3 py-2 text-fg-muted truncate max-w-[200px]">
									{r.productName}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
									{fmtMoney(r.spend)}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
									{r.orders}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
									{fmtMoney(r.sales)}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
									{fmtPct(r.cvr)}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg">
									{fmtPct(r.acos)}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg-muted">
									{r.termCount}
								</td>
								<td className="px-3 py-2 text-right font-mono tabular-nums text-fg-muted">
									{r.campaignCount}
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</div>
	);
}

const FOCUS_OPTIONS: Array<[FocusMode, string]> = [
	["all", "全部视角"],
	["stoploss", "止损优先"],
	["scale", "补量机会"],
	["review", "待人工拍板"],
];

const SORT_OPTIONS: Array<[SortKey, string]> = [
	["spend-desc", "按花费降序"],
	["orders-desc", "按订单降序"],
	["confidence-desc", "按置信度降序"],
	["term-asc", "按关键词排序"],
];

function parseCurrency(value: string) {
	return Number(value.replace(/[^\d.-]/g, "")) || 0;
}

function parseConfidence(value: string) {
	const normalized = value.replace("%", "");
	return Number(normalized) || 0;
}

function passesFocusMode(row: AnalysisRow, focusMode: FocusMode) {
	if (focusMode === "all") return true;
	if (focusMode === "stoploss") return /否定|negative/i.test(row.action);
	if (focusMode === "scale") return /手动|补量|manual/i.test(row.action);
	if (focusMode === "review")
		return (
			parseConfidence(row.confidence) < 100 ||
			/冲突|审核|conflict/i.test(row.action)
		);
	return true;
}

export function AnalysisLivePanel({ payload }: Props) {
	const analysis = payload.analysis ?? {
		rowCount: 0,
		typeCounts: {} as Record<string, number>,
		actionCounts: {} as Record<string, number>,
	};
	// Sprint A.3: 从 URL searchParams 读初始 filter（"分享链接打开就是同一份视图"）
	const searchParams = useSearchParams();
	const pathname = usePathname();
	const router = useRouter();

	const [typeFilter, setTypeFilter] = useState<string>(
		searchParams.get("type") || "all",
	);
	const [actionFilter, setActionFilter] = useState<string>(
		searchParams.get("action") || "all",
	);
	const [query, setQuery] = useState(searchParams.get("q") || "");
	const [sortKey, setSortKey] = useState<SortKey>(
		(searchParams.get("sort") as SortKey) || "spend-desc",
	);
	const [focusMode, setFocusMode] = useState<FocusMode>(
		(searchParams.get("focus") as FocusMode) || "all",
	);
	// Sprint B.1/B.2 — view mode（term/campaign/asin）
	const [viewMode, setViewMode] = useState<ViewMode>(
		(searchParams.get("view") as ViewMode) || "term",
	);
	// Sprint A.2: 详情抽屉状态 —— 选中 term 触发抽屉打开
	const [selectedTerm, setSelectedTerm] = useState<string | null>(null);

	// Sprint A.3: filter 改变时同步到 URL，刷新/分享链接保持同一视图
	useEffect(() => {
		const next = new URLSearchParams();
		if (typeFilter !== "all") next.set("type", typeFilter);
		if (actionFilter !== "all") next.set("action", actionFilter);
		if (query) next.set("q", query);
		if (sortKey !== "spend-desc") next.set("sort", sortKey);
		if (focusMode !== "all") next.set("focus", focusMode);
		if (viewMode !== "term") next.set("view", viewMode);
		const nextStr = next.toString();
		const url = nextStr ? `${pathname}?${nextStr}` : pathname;
		// replaceState 不入 history，避免每次 filter 变化都创建一条历史
		router.replace(url, { scroll: false });
	}, [
		typeFilter,
		actionFilter,
		query,
		sortKey,
		focusMode,
		viewMode,
		pathname,
		router,
	]);

	const filteredRows = useMemo(() => {
		const normalizedQuery = query.trim().toLowerCase();
		const base = (payload.analysisRows ?? []).filter((row: AnalysisRow) => {
			const typePass = typeFilter === "all" || row.type === typeFilter;
			const actionPass = actionFilter === "all" || row.action === actionFilter;
			const queryPass =
				!normalizedQuery ||
				[row.term, row.type, row.rule, row.action].some((value) =>
					value.toLowerCase().includes(normalizedQuery),
				);
			const focusPass = passesFocusMode(row, focusMode);
			return typePass && actionPass && queryPass && focusPass;
		});

		return [...base].sort((left, right) => {
			switch (sortKey) {
				case "orders-desc":
					return right.orders - left.orders;
				case "confidence-desc":
					return (
						parseConfidence(right.confidence) - parseConfidence(left.confidence)
					);
				case "term-asc":
					return left.term.localeCompare(right.term, "zh-CN");
				case "spend-desc":
				default:
					return parseCurrency(right.spend) - parseCurrency(left.spend);
			}
		});
	}, [
		actionFilter,
		focusMode,
		payload.analysisRows,
		query,
		sortKey,
		typeFilter,
	]);

	const typeOptions = useMemo(
		() => ["all", ...Object.keys(analysis.typeCounts ?? {})],
		[analysis.typeCounts],
	);
	const actionOptions = useMemo(
		() => ["all", ...Object.keys(analysis.actionCounts ?? {})],
		[analysis.actionCounts],
	);
	const visibleActionCounts = useMemo(() => {
		return filteredRows.reduce<Record<string, number>>((acc, row) => {
			acc[row.action] = (acc[row.action] ?? 0) + 1;
			return acc;
		}, {});
	}, [filteredRows]);
	const visibleTypeCounts = useMemo(() => {
		return filteredRows.reduce<Record<string, number>>((acc, row) => {
			acc[row.type] = (acc[row.type] ?? 0) + 1;
			return acc;
		}, {});
	}, [filteredRows]);

	const focusModeLabel =
		FOCUS_OPTIONS.find(([k]) => k === focusMode)?.[1] ?? "全部视角";

	useEffect(() => {
		writePageContext(payload.productId, "analysis", {
			summary: `当前视角 ${focusMode}，词类型 ${typeFilter}，建议动作 ${actionFilter}，筛选后 ${filteredRows.length} 条。`,
			focus_mode: focusMode,
			type_filter: typeFilter,
			action_filter: actionFilter,
			visible_rows: filteredRows.length,
			query,
			sort_key: sortKey,
		});
	}, [
		actionFilter,
		filteredRows.length,
		focusMode,
		payload.productId,
		query,
		sortKey,
		typeFilter,
	]);

	const totalRows = analysis.rowCount ?? 0;

	const metricItems: Array<{ label: string; value: string; hint: string }> = [
		{
			label: "可见行",
			value: String(filteredRows.length),
			hint: "筛选后命中行数",
		},
		{
			label: "总行数",
			value: String(totalRows),
			hint: "当前快照所有行",
		},
		{
			label: "当前视角",
			value: focusModeLabel,
			hint: "focus mode",
		},
		{
			label: "匹配动作",
			value: String(Object.keys(visibleActionCounts).length),
			hint: "可见行涉及动作种类",
		},
		{
			label: "匹配类型",
			value: String(Object.keys(visibleTypeCounts).length),
			hint: "可见行涉及词类型",
		},
	];

	return (
		<div className="space-y-5">
			{/* ═══ 1. Metric cards ═══ */}
			<div className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
					{metricItems.map((m, i) => (
						<div
							key={m.label}
							className={
								"px-4 py-3.5 border-border " +
								(i % 2 !== 0 ? "border-l " : "") +
								(i % 3 !== 0 ? "sm:border-l " : "sm:border-l-0 ") +
								(i % 5 !== 0 ? "lg:border-l " : "lg:border-l-0 ") +
								(i >= 2 ? "border-t " : "") +
								(i >= 3 ? "sm:border-t " : "sm:border-t-0 ") +
								(i >= 5 ? "lg:border-t " : "lg:border-t-0")
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
			</div>

			{/* ═══ Sprint B.1/B.2 — view mode segmented tabs ═══ */}
			<div className="inline-flex bg-bg-subtle border border-border rounded-md p-0.5">
				{VIEW_OPTIONS.map(([value, label]) => {
					const active = viewMode === value;
					return (
						<button
							key={value}
							type="button"
							onClick={() => setViewMode(value)}
							className={
								"px-4 h-7 inline-flex items-center rounded text-[12px] font-semibold transition-colors " +
								(active
									? "bg-bg-elevated text-fg shadow-sm border border-border"
									: "text-fg-muted hover:text-fg")
							}
						>
							{label}
						</button>
					);
				})}
			</div>

			{viewMode === "term" && (
			<>
			{/* ═══ 2. Focus tab pills ═══ */}
			<div className="flex flex-wrap items-center gap-2">
				{FOCUS_OPTIONS.map(([value, label]) => {
					const active = focusMode === value;
					return (
						<button
							key={value}
							type="button"
							onClick={() => setFocusMode(value)}
							className={
								"px-3.5 h-8 inline-flex items-center rounded-full text-[13px] transition-colors " +
								(active
									? "bg-bg-elevated border border-fg text-fg font-semibold"
									: "bg-bg-elevated border border-border text-fg-muted hover:bg-bg-subtle hover:border-border-strong")
							}
						>
							{label}
						</button>
					);
				})}
			</div>

			{/* ═══ 3. Filter & Sort card ═══ */}
			<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="flex items-center justify-between px-4 py-3 border-b border-border">
					<div className="flex items-baseline gap-3">
						<h2 className="text-fg">筛选与排序</h2>
						<span className="text-[12px] text-fg-muted">
							{filteredRows.length} / {totalRows} rows
						</span>
					</div>
				</div>
				<div className="p-4 grid gap-3 md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)] md:items-end">
					<div className="space-y-1.5">
						<label className="text-[12px] font-semibold text-fg-muted">
							搜索
						</label>
						<div className="relative">
							<Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-fg-subtle pointer-events-none" />
							<input
								value={query}
								onChange={(e) => setQuery(e.target.value)}
								placeholder="搜索关键词、规则或动作…"
								className="w-full h-9 rounded border border-border bg-bg-elevated pl-9 pr-3 text-[13px] text-fg outline-none placeholder:text-fg-subtle transition-colors focus-visible:border-accent focus-visible:ring-[3px] focus-visible:ring-accent/20"
							/>
						</div>
					</div>
					<div className="space-y-1.5">
						<label className="text-[12px] font-semibold text-fg-muted">
							词类型
						</label>
						<select
							value={typeFilter}
							onChange={(e) => setTypeFilter(e.target.value)}
							className="h-9 w-full rounded border border-border bg-bg-elevated px-3 text-[13px] text-fg outline-none cursor-pointer transition-colors focus-visible:border-accent focus-visible:ring-[3px] focus-visible:ring-accent/20"
						>
							{typeOptions.map((option) => (
								<option key={option} value={option}>
									{option === "all" ? "全部" : option}
								</option>
							))}
						</select>
					</div>
					<div className="space-y-1.5">
						<label className="text-[12px] font-semibold text-fg-muted">
							建议动作
						</label>
						<select
							value={actionFilter}
							onChange={(e) => setActionFilter(e.target.value)}
							className="h-9 w-full rounded border border-border bg-bg-elevated px-3 text-[13px] text-fg outline-none cursor-pointer transition-colors focus-visible:border-accent focus-visible:ring-[3px] focus-visible:ring-accent/20"
						>
							{actionOptions.map((option) => (
								<option key={option} value={option}>
									{option === "all" ? "全部" : option}
								</option>
							))}
						</select>
					</div>
					<div className="space-y-1.5">
						<label className="text-[12px] font-semibold text-fg-muted">
							排序
						</label>
						<select
							value={sortKey}
							onChange={(e) => setSortKey(e.target.value as SortKey)}
							className="h-9 w-full rounded border border-border bg-bg-elevated px-3 text-[13px] text-fg outline-none cursor-pointer transition-colors focus-visible:border-accent focus-visible:ring-[3px] focus-visible:ring-accent/20"
						>
							{SORT_OPTIONS.map(([k, label]) => (
								<option key={k} value={k}>
									{label}
								</option>
							))}
						</select>
					</div>
				</div>
				{(Object.keys(visibleActionCounts).length > 0 ||
					Object.keys(visibleTypeCounts).length > 0) && (
					<div className="px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-[12px] border-t border-border">
						<span className="text-fg-subtle font-semibold uppercase tracking-wide">
							分布
						</span>
						{Object.entries(visibleActionCounts).map(([k, v]) => (
							<span
								key={`a-${k}`}
								className="inline-flex items-baseline gap-1 px-2 py-0.5 rounded-full bg-accent-bg text-accent-strong"
							>
								<span className="font-semibold">{k}</span>
								<span className="font-mono tabular-nums">{v}</span>
							</span>
						))}
						{Object.entries(visibleTypeCounts).map(([k, v]) => (
							<span
								key={`t-${k}`}
								className="inline-flex items-baseline gap-1 px-2 py-0.5 rounded-full bg-bg-subtle text-fg-muted border border-border"
							>
								<span>{k}</span>
								<span className="font-mono tabular-nums text-fg">{v}</span>
							</span>
						))}
					</div>
				)}
			</section>

			{/* ═══ 4. Table ═══ */}
			<AnalysisTable
				analysisRows={filteredRows}
				onRowClick={(term) => setSelectedTerm(term)}
			/>
			</>
			)}

			{viewMode === "campaign" && (
				<CampaignAggTable rows={payload.campaignRows ?? []} />
			)}

			{viewMode === "asin" && <AsinAggTable rows={payload.asinRows ?? []} />}

			{/* Sprint A.2: 详情抽屉 */}
			<AnalysisDetailDrawer
				term={selectedTerm}
				productId={payload.productId ?? null}
				onClose={() => setSelectedTerm(null)}
			/>
		</div>
	);
}
