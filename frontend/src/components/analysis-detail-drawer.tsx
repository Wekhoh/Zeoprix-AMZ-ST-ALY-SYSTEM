"use client";

/**
 * AnalysisDetailDrawer — Sprint A.2 frontend
 *
 * 行点击展开右侧抽屉，一次请求 /frontend/analysis/term/{term} 拉到：
 *   - 30 天 spend / clicks / orders 折线（SVG inline，无依赖）
 *   - 30 天总计指标
 *   - 触发过的规则
 *   - 历史人工决策
 */

import { useEffect, useState } from "react";
import { X } from "lucide-react";

import { BACKEND_BASE_URL } from "@/lib/backend";

type DailyPoint = {
	date: string;
	spend: number;
	clicks: number;
	orders: number;
	sales: number;
};

type AppliedRule = { rule: string; hits: number };

type HistoricalDecision = {
	decidedAt: string;
	decision: string;
	scope: string;
	notes?: string;
};

type TermDetail = {
	term: string;
	termType: string;
	found: boolean;
	message?: string;
	firstSeen?: string;
	lastSeen?: string;
	currentRelevance?: string;
	dailySeries?: DailyPoint[];
	aggregates?: {
		spend: number;
		clicks: number;
		orders: number;
		sales: number;
		cvr: number;
		acos: number;
		rowCount: number;
	};
	appliedRules?: AppliedRule[];
	historicalDecisions?: HistoricalDecision[];
};

type Props = {
	term: string | null;
	productId: number | null;
	onClose: () => void;
};

function formatPct(v: number) {
	return `${(v * 100).toFixed(1)}%`;
}

function MiniSparkline({
	points,
	field,
	stroke = "var(--accent)",
	height = 48,
}: {
	points: DailyPoint[];
	field: keyof DailyPoint;
	stroke?: string;
	height?: number;
}) {
	if (points.length === 0) {
		return <div className="text-[11px] text-fg-subtle">无数据</div>;
	}
	const values = points.map((p) => Number(p[field] ?? 0));
	const max = Math.max(...values, 1);
	const min = Math.min(...values, 0);
	const range = max - min || 1;
	const stepX = points.length > 1 ? 100 / (points.length - 1) : 0;
	const path = values
		.map((v, i) => {
			const x = (i * stepX).toFixed(2);
			const y = (height - ((v - min) / range) * (height - 4) - 2).toFixed(2);
			return `${i === 0 ? "M" : "L"}${x},${y}`;
		})
		.join(" ");
	return (
		<svg
			viewBox={`0 0 100 ${height}`}
			preserveAspectRatio="none"
			className="w-full"
			style={{ height }}
		>
			<path d={path} fill="none" stroke={stroke} strokeWidth={1.5} />
		</svg>
	);
}

export function AnalysisDetailDrawer({ term, productId, onClose }: Props) {
	const [data, setData] = useState<TermDetail | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!term) return;
		const controller = new AbortController();
		setLoading(true);
		setError(null);
		setData(null);
		const url = new URL(
			`${BACKEND_BASE_URL}/frontend/analysis/term/${encodeURIComponent(term)}`,
		);
		if (productId != null) url.searchParams.set("product_id", String(productId));
		fetch(url.toString(), { signal: controller.signal })
			.then(async (r) => {
				if (!r.ok) throw new Error(`HTTP ${r.status}`);
				const body = (await r.json()) as TermDetail;
				setData(body);
			})
			.catch((e) => {
				if ((e as Error).name === "AbortError") return;
				setError((e as Error).message || "加载失败");
			})
			.finally(() => setLoading(false));
		return () => controller.abort();
	}, [term, productId]);

	// Esc 关闭
	useEffect(() => {
		if (!term) return;
		function handleKey(e: KeyboardEvent) {
			if (e.key === "Escape") onClose();
		}
		window.addEventListener("keydown", handleKey);
		return () => window.removeEventListener("keydown", handleKey);
	}, [term, onClose]);

	if (!term) return null;

	return (
		<div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
			<div className="absolute inset-0 bg-black/30" />
			<aside
				className="relative w-full max-w-[460px] h-full bg-bg-elevated border-l border-border overflow-y-auto shadow-2xl"
				onClick={(e) => e.stopPropagation()}
			>
				<header className="sticky top-0 z-10 flex items-center justify-between px-5 py-3 border-b border-border bg-bg-elevated">
					<div className="min-w-0">
						<div className="text-[11px] uppercase tracking-wider text-fg-subtle">
							TERM DETAIL
						</div>
						<h3 className="font-mono text-[15px] font-semibold text-fg truncate">
							{term}
						</h3>
					</div>
					<button
						type="button"
						onClick={onClose}
						title="关闭 (Esc)"
						className="rounded p-1 text-fg-muted hover:bg-bg-subtle hover:text-fg transition"
					>
						<X className="h-4 w-4" />
					</button>
				</header>

				<div className="px-5 py-4 space-y-5">
					{loading ? (
						<div className="text-[13px] text-fg-muted">加载中…</div>
					) : error ? (
						<div className="rounded border border-error-fg/30 bg-error-bg/40 p-3 text-[13px] text-error-fg">
							加载失败：{error}
						</div>
					) : !data ? null : !data.found ? (
						<div className="text-[13px] text-fg-muted">{data.message}</div>
					) : (
						<>
							<div className="grid grid-cols-2 gap-x-4 gap-y-3 text-[12px]">
								<div>
									<div className="text-fg-subtle">类型</div>
									<div className="text-fg font-medium">{data.termType}</div>
								</div>
								<div>
									<div className="text-fg-subtle">当前决策</div>
									<div className="text-fg font-medium">
										{data.currentRelevance ?? "pending"}
									</div>
								</div>
								<div>
									<div className="text-fg-subtle">首次出现</div>
									<div className="text-fg font-mono">
										{data.firstSeen ?? "—"}
									</div>
								</div>
								<div>
									<div className="text-fg-subtle">最近出现</div>
									<div className="text-fg font-mono">
										{data.lastSeen ?? "—"}
									</div>
								</div>
							</div>

							{data.aggregates ? (
								<section>
									<div className="text-[11px] uppercase tracking-wider text-fg-subtle mb-2">
										30D AGGREGATES
									</div>
									<div className="grid grid-cols-3 gap-3 text-[13px]">
										<div>
											<div className="text-fg-subtle text-[11px]">花费</div>
											<div className="font-mono tabular-nums text-fg font-medium">
												${data.aggregates.spend.toFixed(2)}
											</div>
										</div>
										<div>
											<div className="text-fg-subtle text-[11px]">点击</div>
											<div className="font-mono tabular-nums text-fg font-medium">
												{data.aggregates.clicks}
											</div>
										</div>
										<div>
											<div className="text-fg-subtle text-[11px]">订单</div>
											<div className="font-mono tabular-nums text-fg font-medium">
												{data.aggregates.orders}
											</div>
										</div>
										<div>
											<div className="text-fg-subtle text-[11px]">销售额</div>
											<div className="font-mono tabular-nums text-fg font-medium">
												${data.aggregates.sales.toFixed(2)}
											</div>
										</div>
										<div>
											<div className="text-fg-subtle text-[11px]">CVR</div>
											<div className="font-mono tabular-nums text-fg font-medium">
												{formatPct(data.aggregates.cvr)}
											</div>
										</div>
										<div>
											<div className="text-fg-subtle text-[11px]">ACOS</div>
											<div className="font-mono tabular-nums text-fg font-medium">
												{formatPct(data.aggregates.acos)}
											</div>
										</div>
									</div>
								</section>
							) : null}

							{data.dailySeries && data.dailySeries.length > 0 ? (
								<section>
									<div className="text-[11px] uppercase tracking-wider text-fg-subtle mb-2">
										30D TREND
									</div>
									<div className="space-y-2">
										<div>
											<div className="text-[11px] text-fg-subtle mb-0.5">花费</div>
											<MiniSparkline
												points={data.dailySeries}
												field="spend"
												stroke="var(--accent)"
											/>
										</div>
										<div>
											<div className="text-[11px] text-fg-subtle mb-0.5">订单</div>
											<MiniSparkline
												points={data.dailySeries}
												field="orders"
												stroke="var(--success-fg)"
											/>
										</div>
										<div>
											<div className="text-[11px] text-fg-subtle mb-0.5">点击</div>
											<MiniSparkline
												points={data.dailySeries}
												field="clicks"
												stroke="var(--fg-muted)"
											/>
										</div>
									</div>
								</section>
							) : null}

							{data.appliedRules && data.appliedRules.length > 0 ? (
								<section>
									<div className="text-[11px] uppercase tracking-wider text-fg-subtle mb-2">
										APPLIED RULES
									</div>
									<ul className="space-y-1 text-[13px]">
										{data.appliedRules.map((r) => (
											<li key={r.rule} className="flex justify-between">
												<span className="text-fg">{r.rule}</span>
												<span className="font-mono text-fg-subtle">
													×{r.hits}
												</span>
											</li>
										))}
									</ul>
								</section>
							) : null}

							{data.historicalDecisions &&
							data.historicalDecisions.length > 0 ? (
								<section>
									<div className="text-[11px] uppercase tracking-wider text-fg-subtle mb-2">
										HISTORICAL DECISIONS
									</div>
									<ul className="space-y-2 text-[12px]">
										{data.historicalDecisions.map((h, i) => (
											<li
												key={i}
												className="rounded border border-border bg-bg-subtle/40 p-2"
											>
												<div className="flex justify-between">
													<span className="font-medium text-fg">
														{h.decision}
													</span>
													<span className="font-mono text-fg-subtle">
														{h.decidedAt}
													</span>
												</div>
												{h.notes ? (
													<div className="mt-1 text-fg-muted">{h.notes}</div>
												) : null}
												{h.scope === "global" ? (
													<div className="mt-1 text-[11px] text-amber-700">
														(全局生效)
													</div>
												) : null}
											</li>
										))}
									</ul>
								</section>
							) : null}
						</>
					)}
				</div>
			</aside>
		</div>
	);
}
