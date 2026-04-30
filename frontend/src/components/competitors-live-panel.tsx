"use client";
/**
 * competitors-live-panel — Sprint C.1 第二阶段
 * 基于 src/rules/asin_rules 实时计算的对手 ASIN 监控视图。
 *
 * 关键 user value：把"作为搜索词出现在我自己投放里的对手 ASIN"
 * 拽出来给主人看，避免在不知情的情况下持续投放高 ACOS 对手词。
 */
import { useMemo, useState } from "react";

import type { CompetitorPayload, CompetitorAsinRow } from "@/lib/mock-data";

type Props = {
	payload: CompetitorPayload;
};

type SortKey = "spend-desc" | "orders-desc" | "acos-desc" | "asin-asc";

const SORT_OPTIONS: Array<[SortKey, string]> = [
	["spend-desc", "按花费降序"],
	["orders-desc", "按订单降序"],
	["acos-desc", "按 ACOS 降序"],
	["asin-asc", "按 ASIN 排序"],
];

const ACTION_FILTER_OPTIONS = ["all", "否定", "评估", "监控", "保留投放"];

function fmtMoney(n: number) {
	return `$${n.toFixed(2)}`;
}

function fmtPct(n: number) {
	return `${(n * 100).toFixed(1)}%`;
}

function actionTone(action: string) {
	if (action === "否定") return "bg-error-bg text-error-fg";
	if (action === "评估") return "bg-warning-bg text-warning-fg";
	if (action === "监控") return "bg-bg-subtle text-fg-muted";
	if (action === "保留投放") return "bg-success-bg text-success-fg";
	return "bg-bg-subtle text-fg-muted";
}

export function CompetitorsLivePanel({ payload }: Props) {
	const [sortKey, setSortKey] = useState<SortKey>("spend-desc");
	const [actionFilter, setActionFilter] = useState<string>("all");
	const [query, setQuery] = useState("");

	const insights = payload.insights ?? {
		totalCount: 0,
		totalSpend: 0,
		totalOrders: 0,
		avgAcos: 0,
		topPerformers: [],
		worstPerformers: [],
	};

	const filteredRows = useMemo(() => {
		const q = query.trim().toUpperCase();
		const base = (payload.discoveredCompetitors ?? []).filter(
			(r: CompetitorAsinRow) => {
				const actionPass =
					actionFilter === "all" || r.suggestedAction === actionFilter;
				const queryPass = !q || r.asin.includes(q);
				return actionPass && queryPass;
			},
		);
		return [...base].sort((a, b) => {
			switch (sortKey) {
				case "orders-desc":
					return b.orders - a.orders;
				case "acos-desc":
					return b.acos - a.acos;
				case "asin-asc":
					return a.asin.localeCompare(b.asin);
				case "spend-desc":
				default:
					return b.spend - a.spend;
			}
		});
	}, [actionFilter, query, sortKey, payload.discoveredCompetitors]);

	const totalRows = payload.discoveredCompetitors?.length ?? 0;
	const configuredCount = payload.configuredCompetitorAsins?.length ?? 0;
	const showZeroConfigWarning = configuredCount === 0 && totalRows > 0;

	const metricItems = [
		{
			label: "发现的对手 ASIN",
			value: String(insights.totalCount),
			hint: "出现在我搜索词里的非自有 ASIN（含重复活动）",
		},
		{
			label: "对手词总花费",
			value: fmtMoney(insights.totalSpend),
			hint: "投放在对手 ASIN 上的累计花费",
		},
		{
			label: "对手词订单",
			value: String(insights.totalOrders),
			hint: "在对手 ASIN 上拿到的订单",
		},
		{
			label: "平均 ACOS",
			value: fmtPct(insights.avgAcos),
			hint: "(排除无销售)",
		},
		{
			label: "已配置竞品",
			value: String(configuredCount),
			hint: "products.config.competitor_asins",
		},
	];

	return (
		<div className="space-y-5">
			{/* ═══ 1. 零配置警告 ═══ */}
			{showZeroConfigWarning && (
				<div className="border border-warning-fg/40 bg-warning-bg/40 rounded-lg p-4 text-[13px] text-warning-fg">
					<div className="font-semibold mb-1">⚠ 主人尚未配置任何竞品 ASIN</div>
					<div className="text-fg-muted">
						但系统已自动发现 {insights.totalCount} 个对手 ASIN
						出现在我自己的搜索词里，累计花费{" "}
						<span className="font-mono tabular-nums font-semibold">
							{fmtMoney(insights.totalSpend)}
						</span>
						。建议把高频出现的对手 ASIN 加入产品配置，让规则引擎按竞品策略处理。
					</div>
				</div>
			)}

			{/* ═══ 2. Metric cards ═══ */}
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
							<div className="text-[12px] font-semibold text-fg mb-1.5">
								{m.label}
							</div>
							<div
								className={
									"font-bold text-fg leading-none " +
									(/^[$\d]/.test(m.value)
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

			{/* ═══ 3. Top performers ═══ */}
			{insights.topPerformers.length > 0 && (
				<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
					<div className="px-4 py-3 border-b border-border flex items-baseline gap-3">
						<h2 className="text-fg">表现最好的对手词</h2>
						<span className="text-[12px] text-fg-muted">
							按订单数 top {insights.topPerformers.length}
						</span>
					</div>
					<div className="px-4 py-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
						{insights.topPerformers.map((p) => (
							<div
								key={p.asin}
								className="rounded border border-border bg-bg-subtle/40 p-3"
							>
								<div className="font-mono text-[13px] text-fg">{p.asin}</div>
								<div className="mt-1.5 flex justify-between text-[12px] text-fg-muted">
									<span>花费</span>
									<span className="font-mono tabular-nums text-fg">
										{fmtMoney(p.spend)}
									</span>
								</div>
								<div className="flex justify-between text-[12px] text-fg-muted">
									<span>订单</span>
									<span className="font-mono tabular-nums text-fg">
										{p.orders}
									</span>
								</div>
								<div className="flex justify-between text-[12px] text-fg-muted">
									<span>ACOS</span>
									<span className="font-mono tabular-nums text-fg">
										{fmtPct(p.acos)}
									</span>
								</div>
							</div>
						))}
					</div>
				</section>
			)}

			{/* ═══ 4. Filter bar ═══ */}
			<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="px-4 py-3 border-b border-border flex items-baseline gap-3">
					<h2 className="text-fg">发现的对手 ASIN</h2>
					<span className="text-[12px] text-fg-muted">
						{filteredRows.length} / {totalRows} rows
					</span>
				</div>
				<div className="p-4 grid gap-3 md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1fr)] md:items-end">
					<div className="space-y-1.5">
						<label className="text-[12px] font-semibold text-fg-muted">
							搜索 ASIN
						</label>
						<input
							value={query}
							onChange={(e) => setQuery(e.target.value)}
							placeholder="例：B07SRRQS5B"
							className="w-full h-9 rounded border border-border bg-bg-elevated px-3 text-[13px] text-fg outline-none placeholder:text-fg-subtle transition-colors focus-visible:border-accent focus-visible:ring-[3px] focus-visible:ring-accent/20"
						/>
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
							{ACTION_FILTER_OPTIONS.map((opt) => (
								<option key={opt} value={opt}>
									{opt === "all" ? "全部" : opt}
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
			</section>

			{/* ═══ 5. Table ═══ */}
			{filteredRows.length === 0 ? (
				<div className="bg-bg-elevated border border-border rounded-lg p-8 text-center text-[13px] text-fg-subtle">
					{totalRows === 0
						? "暂无对手 ASIN — 看起来主人投的全都是自有 ASIN，干净！"
						: "没有匹配当前筛选的对手 ASIN"}
				</div>
			) : (
				<div className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
					<div className="overflow-x-auto">
						<table className="w-full text-[12px]">
							<thead className="bg-bg-subtle text-fg-muted">
								<tr className="text-left">
									<th className="px-3 py-2 font-semibold">ASIN</th>
									<th className="px-3 py-2 font-semibold">建议动作</th>
									<th className="px-3 py-2 font-semibold">已配置</th>
									<th className="px-3 py-2 font-semibold text-right">展现</th>
									<th className="px-3 py-2 font-semibold text-right">点击</th>
									<th className="px-3 py-2 font-semibold text-right">花费</th>
									<th className="px-3 py-2 font-semibold text-right">订单</th>
									<th className="px-3 py-2 font-semibold text-right">销售</th>
									<th className="px-3 py-2 font-semibold text-right">ACOS</th>
								</tr>
							</thead>
							<tbody>
								{filteredRows.map((r, i) => (
									<tr
										key={`${r.asin}-${i}`}
										className="border-t border-border hover:bg-bg-subtle/50"
									>
										<td className="px-3 py-2 font-mono text-fg">{r.asin}</td>
										<td className="px-3 py-2">
											<span
												className={
													"inline-block px-2 py-0.5 rounded text-[11px] font-semibold " +
													actionTone(r.suggestedAction)
												}
											>
												{r.suggestedAction}
											</span>
										</td>
										<td className="px-3 py-2 text-fg-muted">
											{r.isConfigured ? "✓" : "—"}
										</td>
										<td className="px-3 py-2 text-right font-mono tabular-nums text-fg-muted">
											{r.impressions}
										</td>
										<td className="px-3 py-2 text-right font-mono tabular-nums text-fg-muted">
											{r.clicks}
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
											{fmtPct(r.acos)}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</div>
			)}
		</div>
	);
}
