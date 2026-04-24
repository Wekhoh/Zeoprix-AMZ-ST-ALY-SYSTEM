"use client";
/**
 * <Input> — Zeoprix AMZ-ST Data-Dense Dashboard
 * Source: design-system/zeoprix-amz-st/MASTER.md
 * - radius 8px (rounded-lg)
 * - border slate-200 / focus navy + 3px 15% opacity ring
 * - heights: sm 32 / md 40 / lg 44 (mobile touch-friendly lg)
 */
import * as React from "react";
import { tv, type VariantProps } from "tailwind-variants";
import { clsx } from "clsx";

const input = tv({
	base: [
		"w-full bg-bg-elevated text-fg placeholder:text-fg-subtle",
		"border border-border rounded-lg px-4",
		"outline-none transition-[border-color,box-shadow] duration-200 ease-out",
		"focus-visible:border-primary focus-visible:ring-[3px] focus-visible:ring-primary/15",
		"disabled:bg-bg-subtle disabled:text-fg-muted disabled:cursor-not-allowed",
	],
	variants: {
		inputSize: {
			sm: "h-8 text-[13px] px-3",
			md: "h-10 text-sm",
			lg: "h-11 text-base",
		},
		error: {
			true: "border-error focus-visible:border-error focus-visible:ring-error/15",
			false: "",
		},
	},
	defaultVariants: {
		inputSize: "md",
		error: false,
	},
});

type InputVariants = VariantProps<typeof input>;

export interface InputProps
	extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size">,
		InputVariants {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
	({ className, inputSize, error, type = "text", ...props }, ref) => {
		return (
			<input
				ref={ref}
				type={type}
				className={clsx(input({ inputSize, error }), className)}
				{...props}
			/>
		);
	},
);
Input.displayName = "Input";
