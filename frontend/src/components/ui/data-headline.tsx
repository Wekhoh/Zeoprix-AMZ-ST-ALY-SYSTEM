/**
 * <DataHeadline> — Phase 5 section header，替代散落的 SectionHead
 * 格式：[Calistoga eyebrow] · [Inter zh 标题] · [count mono] · [LivePulse?] · [action]
 */
import * as React from "react";
import { clsx } from "clsx";
import { LivePulse } from "@/components/ui/live-pulse";

export interface DataHeadlineProps {
	eyebrow: string;
	title: React.ReactNode;
	count?: React.ReactNode;
	live?: boolean;
	action?: React.ReactNode;
	className?: string;
}

export function DataHeadline({
	eyebrow,
	title,
	count,
	live = false,
	action,
	className,
}: DataHeadlineProps) {
	return (
		<div
			className={clsx(
				"flex items-end justify-between gap-4 border-b border-border pb-2.5",
				className,
			)}
		>
			<div className="flex items-baseline gap-3 min-w-0">
				<span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-fg">
					{eyebrow}
				</span>
				<span className="font-mono text-[11px] text-fg-subtle">·</span>
				<h2 className="text-[15px] font-semibold tracking-tight text-fg truncate">
					{title}
				</h2>
				{count ? (
					<span className="font-mono text-[11px] tabular-nums text-fg-muted">
						{count}
					</span>
				) : null}
				{live ? <LivePulse size="sm" className="ml-1 self-center" /> : null}
			</div>
			{action ? <div className="shrink-0">{action}</div> : null}
		</div>
	);
}
