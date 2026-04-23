"use client";
/**
 * DailyInsightsCard — Sprint 4 · A3
 *
 * 首页工作台的"今日 AI 洞察"卡片。
 * - 首次加载 GET /frontend/insights/today
 * - 点击"生成今日摘要"按钮调 POST /frontend/insights/generate
 * - Amazon Ads 风（复用现有 bordered-card 视觉）
 */
import { useCallback, useEffect, useState } from "react";
import { Sparkles, RefreshCw } from "lucide-react";

import { BACKEND_BASE_URL } from "@/lib/backend";

export type InsightRow = {
	id: number;
	product_id: number | null;
	date: string;
	summary: string;
	key_findings: string[];
	recommendations: string[];
	statistics: Record<string, unknown>;
	created_at: string;
};

type Props = {
	productId?: number | null;
};

function formatCreatedAt(iso: string): string {
	if (!iso) return "";
	try {
		const date = new Date(iso);
		if (Number.isNaN(date.getTime())) return iso;
		return date.toLocaleString("zh-CN", {
			month: "2-digit",
			day: "2-digit",
			hour: "2-digit",
			minute: "2-digit",
		});
	} catch {
		return iso;
	}
}

function buildQuery(productId: number | null | undefined): string {
	if (productId == null) return "";
	return `?product_id=${encodeURIComponent(String(productId))}`;
}

export function DailyInsightsCard({ productId }: Props) {
	const [today, setToday] = useState<InsightRow | null>(null);
	const [loading, setLoading] = useState(true);
	const [generating, setGenerating] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const load = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const response = await fetch(
				`${BACKEND_BASE_URL}/frontend/insights/today${buildQuery(productId)}`,
				{ cache: "no-store" },
			);
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			const body = (await response.json()) as { today: InsightRow | null };
			setToday(body.today);
		} catch (err) {
			setError((err as Error).message);
		} finally {
			setLoading(false);
		}
	}, [productId]);

	useEffect(() => {
		void load();
	}, [load]);

	const generate = useCallback(async () => {
		setGenerating(true);
		setError(null);
		try {
			const response = await fetch(
				`${BACKEND_BASE_URL}/frontend/insights/generate${buildQuery(productId)}`,
				{ method: "POST", cache: "no-store" },
			);
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			const row = (await response.json()) as InsightRow;
			setToday(row);
		} catch (err) {
			setError((err as Error).message);
		} finally {
			setGenerating(false);
		}
	}, [productId]);

	return (
		<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
			<div className="flex items-center justify-between px-4 py-3 border-b border-border">
				<div className="flex items-center gap-2">
					<Sparkles className="h-3.5 w-3.5 text-accent-strong" />
					<h2 className="text-fg">今日 AI 洞察</h2>
					{today ? (
						<span className="text-[12px] text-fg-subtle font-mono tabular-nums">
							{formatCreatedAt(today.created_at)}
						</span>
					) : null}
				</div>
				<button
					type="button"
					onClick={() => void generate()}
					disabled={generating || loading}
					className="inline-flex items-center gap-1.5 px-3 h-8 rounded-full bg-accent text-on-primary text-[12.5px] font-semibold hover:bg-accent-strong disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
				>
					<RefreshCw
						className={"h-3 w-3 " + (generating ? "animate-spin" : "")}
					/>
					{today ? "重新生成" : "生成今日摘要"}
				</button>
			</div>

			<div className="p-4">
				{error ? (
					<div className="text-[13px] text-error-fg bg-error-bg/40 border border-error/30 rounded px-3 py-2 mb-3">
						{error}
					</div>
				) : null}

				{loading ? (
					<div className="text-[13px] text-fg-muted">加载今日洞察…</div>
				) : today ? (
					<div className="space-y-4">
						<p className="text-[14px] leading-[1.7] text-fg">
							{today.summary}
						</p>

						{today.key_findings.length > 0 ? (
							<div>
								<h3 className="text-fg mb-2">关键发现</h3>
								<ul className="space-y-1.5">
									{today.key_findings.slice(0, 5).map((f, i) => (
										<li
											key={`finding-${i}`}
											className="flex items-start gap-2 text-[13px] text-fg leading-[1.55]"
										>
											<span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-accent shrink-0" />
											<span className="flex-1">{f}</span>
										</li>
									))}
								</ul>
							</div>
						) : null}

						{today.recommendations.length > 0 ? (
							<div>
								<h3 className="text-fg mb-2">推荐行动</h3>
								<ol className="space-y-1.5">
									{today.recommendations.slice(0, 5).map((r, i) => (
										<li
											key={`rec-${i}`}
											className="flex items-start gap-2 text-[13px] text-fg leading-[1.55]"
										>
											<span className="inline-flex items-center justify-center h-[18px] w-[18px] rounded-full bg-bg-subtle text-[11px] font-mono tabular-nums text-fg-muted font-semibold shrink-0 mt-0.5">
												{i + 1}
											</span>
											<span className="flex-1">{r}</span>
										</li>
									))}
								</ol>
							</div>
						) : null}
					</div>
				) : (
					<div className="text-center py-6">
						<div className="text-[13px] text-fg-muted mb-3">
							今天还没有生成 AI 洞察。
						</div>
						<div className="text-[12px] text-fg-subtle">
							点击右上角「生成今日摘要」让 Copilot 总结当前产品的数据。
						</div>
					</div>
				)}
			</div>
		</section>
	);
}
