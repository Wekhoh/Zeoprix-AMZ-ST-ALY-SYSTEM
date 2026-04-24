/**
 * <Skeleton> — Vercel 标志性 shimmer loading 占位
 */
import * as React from "react";
import { clsx } from "clsx";

export type SkeletonProps = React.HTMLAttributes<HTMLDivElement>;

export function Skeleton({ className, ...props }: SkeletonProps) {
	return (
		<div
			aria-hidden="true"
			className={clsx("animate-pulse rounded-md bg-bg-subtle", className)}
			{...props}
		/>
	);
}
