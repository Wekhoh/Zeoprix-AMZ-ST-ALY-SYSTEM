/**
 * <Badge> — 状态标签（default / success / warning / error / accent）
 * Notion 风微 tinted 背景 + Vercel 风 1px 边框
 */
import * as React from "react";
import { tv, type VariantProps } from "tailwind-variants";
import { clsx } from "clsx";

const badge = tv({
	base: [
		"inline-flex items-center gap-1.5 whitespace-nowrap",
		"rounded-full border px-2.5 py-0.5",
		"text-xs font-medium leading-none",
	],
	variants: {
		tone: {
			default: "border-border bg-bg-elevated text-fg-muted",
			success: "border-success/30 bg-success-bg text-success-fg",
			warning: "border-warning/30 bg-warning-bg text-warning-fg",
			error: "border-error/30 bg-error-bg text-error-fg",
			accent: "border-accent/30 bg-accent-bg text-accent-fg",
		},
	},
	defaultVariants: { tone: "default" },
});

type BadgeVariants = VariantProps<typeof badge>;

export interface BadgeProps
	extends React.HTMLAttributes<HTMLSpanElement>,
		BadgeVariants {
	dot?: boolean;
}

export function Badge({
	className,
	tone,
	dot,
	children,
	...props
}: BadgeProps) {
	const dotColor =
		tone === "success"
			? "bg-success"
			: tone === "warning"
				? "bg-warning"
				: tone === "error"
					? "bg-error"
					: tone === "accent"
						? "bg-accent"
						: "bg-fg-muted";
	return (
		<span className={clsx(badge({ tone }), className)} {...props}>
			{dot && (
				<span
					aria-hidden="true"
					className={clsx("h-1.5 w-1.5 rounded-full", dotColor)}
				/>
			)}
			{children}
		</span>
	);
}
