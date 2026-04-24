/**
 * <Card> — Zeoprix AMZ-ST Data-Dense Dashboard
 * Source: design-system/zeoprix-amz-st/MASTER.md
 * - Default elevation: "flat" — hairline border, no shadow (ops dashboard)
 * - Optional elevation: "raised" — shadow-md + hover shadow-lg
 * - radius-xl 12px (MASTER card spec)
 * - padding-md 24px (p-6)
 */
import * as React from "react";
import { tv, type VariantProps } from "tailwind-variants";
import { clsx } from "clsx";

const card = tv({
	base: [
		"border border-border bg-bg-elevated",
		"transition-[background-color,border-color,box-shadow,transform] duration-200 ease-out",
	],
	variants: {
		padding: {
			none: "",
			sm: "p-4",
			md: "p-6",
			lg: "p-8",
		},
		radius: {
			md: "rounded-md",
			lg: "rounded-lg",
			xl: "rounded-xl",
		},
		tone: {
			default: "",
			muted: "bg-bg-subtle",
			accent: "border-accent/40 bg-accent-bg",
		},
		elevation: {
			flat: "",
			raised: "shadow-md hover:shadow-lg",
		},
		interactive: {
			true: "hover:border-border-strong cursor-pointer",
			false: "",
		},
	},
	compoundVariants: [
		{
			interactive: true,
			elevation: "raised",
			class: "hover:-translate-y-0.5",
		},
	],
	defaultVariants: {
		padding: "md",
		radius: "xl",
		tone: "default",
		elevation: "flat",
		interactive: false,
	},
});

type CardVariants = VariantProps<typeof card>;

export interface CardProps
	extends React.HTMLAttributes<HTMLDivElement>,
		CardVariants {}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
	(
		{ className, padding, radius, tone, elevation, interactive, ...props },
		ref,
	) => {
		return (
			<div
				ref={ref}
				className={clsx(
					card({ padding, radius, tone, elevation, interactive }),
					className,
				)}
				{...props}
			/>
		);
	},
);
Card.displayName = "Card";

/**
 * <CardHeader> — 标题区
 */
export interface CardHeaderProps
	extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
	title?: React.ReactNode;
	description?: React.ReactNode;
	action?: React.ReactNode;
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
	({ className, title, description, action, children, ...props }, ref) => {
		return (
			<div
				ref={ref}
				className={clsx(
					"flex items-start justify-between gap-4",
					"pb-4 mb-4 border-b border-border",
					className,
				)}
				{...props}
			>
				<div className="min-w-0 flex-1">
					{title && (
						<h3 className="text-lg font-semibold text-fg tracking-tight leading-tight">
							{title}
						</h3>
					)}
					{description && (
						<p className="mt-1 text-[13px] font-medium text-fg-muted leading-relaxed">
							{description}
						</p>
					)}
					{children}
				</div>
				{action && <div className="shrink-0">{action}</div>}
			</div>
		);
	},
);
CardHeader.displayName = "CardHeader";

/**
 * <CardFooter> — 尾部操作区
 */
export const CardFooter = React.forwardRef<
	HTMLDivElement,
	React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
	return (
		<div
			ref={ref}
			className={clsx(
				"flex items-center justify-end gap-2",
				"pt-4 mt-4 border-t border-border",
				className,
			)}
			{...props}
		/>
	);
});
CardFooter.displayName = "CardFooter";
