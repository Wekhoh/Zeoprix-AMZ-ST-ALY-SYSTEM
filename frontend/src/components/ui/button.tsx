"use client";
/**
 * <Button> — Zeoprix AMZ-ST Data-Dense Dashboard
 * Source: design-system/zeoprix-amz-st/MASTER.md
 * - primary: sky-700 fill + white text (accent CTA)
 * - secondary: border + bg-elevated (hairline style for ops dashboards)
 * - outline: navy outline + transparent bg (MASTER .btn-secondary)
 * - radius 8px (rounded-lg)
 * - font-weight 600
 * - hover translateY(-1px) lift
 * - 200ms ease transitions
 */
import * as React from "react";
import { tv, type VariantProps } from "tailwind-variants";
import { clsx } from "clsx";
import { Loader2 } from "lucide-react";

const button = tv({
	base: [
		"inline-flex items-center justify-center gap-2 whitespace-nowrap cursor-pointer select-none",
		"font-semibold rounded-lg",
		"transition-[background-color,border-color,color,transform,box-shadow] duration-200 ease-out",
		"focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-primary/20 focus-visible:ring-offset-0",
		"disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none disabled:hover:translate-y-0",
	],
	variants: {
		variant: {
			primary:
				"bg-accent text-white shadow-sm hover:bg-accent-strong hover:-translate-y-px hover:shadow-md",
			secondary:
				"border border-border-strong bg-bg-elevated text-fg hover:bg-bg-subtle hover:border-primary",
			outline:
				"border-2 border-primary bg-transparent text-primary hover:bg-primary hover:text-on-primary",
			ghost: "text-fg hover:bg-bg-subtle",
			danger:
				"bg-error text-white shadow-sm hover:bg-error-fg hover:-translate-y-px hover:shadow-md",
		},
		size: {
			sm: "h-8 px-3 text-[13px]",
			md: "h-10 px-5 text-sm",
			lg: "h-11 px-6 text-[15px]",
		},
	},
	defaultVariants: {
		variant: "secondary",
		size: "md",
	},
});

type ButtonVariants = VariantProps<typeof button>;

export interface ButtonProps
	extends React.ButtonHTMLAttributes<HTMLButtonElement>,
		ButtonVariants {
	loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
	(
		{ className, variant, size, loading, disabled, children, ...props },
		ref,
	) => {
		return (
			<button
				ref={ref}
				className={clsx(button({ variant, size }), className)}
				disabled={disabled || loading}
				{...props}
			>
				{loading && (
					<Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
				)}
				{children}
			</button>
		);
	},
);
Button.displayName = "Button";
