/**
 * <EmptyState> — 统一"无数据"占位
 * 虚线边框 + 居中 + icon/heading/description/action
 */
import * as React from "react";
import { clsx } from "clsx";

export interface EmptyStateProps
	extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
	icon?: React.ReactNode;
	heading: React.ReactNode;
	description?: React.ReactNode;
	action?: React.ReactNode;
}

export function EmptyState({
	className,
	icon,
	heading,
	description,
	action,
	...props
}: EmptyStateProps) {
	return (
		<div
			className={clsx(
				"flex flex-col items-center justify-center text-center",
				"px-6 py-12 rounded-lg border border-dashed border-border",
				"bg-bg-subtle",
				className,
			)}
			{...props}
		>
			{icon && <div className="mb-4 text-fg-subtle">{icon}</div>}
			<h3 className="text-base font-semibold text-fg tracking-tight">
				{heading}
			</h3>
			{description && (
				<p className="mt-2 max-w-md text-sm text-fg-muted leading-relaxed">
					{description}
				</p>
			)}
			{action && <div className="mt-6">{action}</div>}
		</div>
	);
}
