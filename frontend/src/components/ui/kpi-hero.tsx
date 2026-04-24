/**
 * <KpiHero> — Phase 5 核心视觉元素
 * 大号数字（响应式 28-40px）+ label + 可选 trend + subtitle
 * Source: design-system/zeoprix-amz-st/MASTER.md + Phase 5 plan
 */
import * as React from "react";
import { clsx } from "clsx";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

export interface KpiHeroProps {
	value: React.ReactNode;
	label: React.ReactNode;
	trend?: number | null;
	subtitle?: React.ReactNode;
	unit?: React.ReactNode;
	compact?: boolean;
	className?: string;
}

export function KpiHero({
	value,
	label,
	trend,
	subtitle,
	unit,
	compact = false,
	className,
}: KpiHeroProps) {
	const trendTone =
		trend == null ? "neutral" : trend > 0 ? "up" : trend < 0 ? "down" : "flat";
	const TrendIcon =
		trendTone === "up"
			? ArrowUpRight
			: trendTone === "down"
				? ArrowDownRight
				: Minus;
	const trendColor =
		trendTone === "up"
			? "text-success-fg"
			: trendTone === "down"
				? "text-error-fg"
				: "text-fg-subtle";

	return (
		<div
			className={clsx(
				"flex flex-col",
				compact ? "gap-1" : "gap-1.5",
				className,
			)}
		>
			<div className="text-micro text-fg-subtle">{label}</div>

			<div className="flex items-baseline gap-1.5 min-w-0">
				<span
					className={clsx(
						compact ? "text-display" : "text-hero",
						"text-fg",
						"truncate",
					)}
				>
					{value}
				</span>
				{unit ? (
					<span className="text-[13px] font-medium text-fg-muted whitespace-nowrap">
						{unit}
					</span>
				) : null}
			</div>

			{(trend != null || subtitle) && (
				<div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[12px]">
					{trend != null ? (
						<span
							className={clsx(
								"inline-flex items-center gap-0.5 font-mono tabular-nums font-semibold",
								trendColor,
							)}
						>
							<TrendIcon className="h-3 w-3" aria-hidden />
							{trend > 0 ? "+" : ""}
							{trend}%
						</span>
					) : null}
					{subtitle ? (
						<span className="text-fg-muted truncate">{subtitle}</span>
					) : null}
				</div>
			)}
		</div>
	);
}
