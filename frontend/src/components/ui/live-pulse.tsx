/**
 * <LivePulse> — amber signature 脉冲点
 * Phase 5 Master-Grade 视觉 signature，每页最多 1 处做 "live" 指示器
 */
import * as React from "react";
import { clsx } from "clsx";

export interface LivePulseProps extends React.HTMLAttributes<HTMLSpanElement> {
	tone?: "signature" | "accent" | "success";
	size?: "sm" | "md";
}

export function LivePulse({
	tone = "signature",
	size = "md",
	className,
	...props
}: LivePulseProps) {
	const sz = size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2";
	const dotColor =
		tone === "signature"
			? "bg-accent"
			: tone === "success"
				? "bg-success"
				: "bg-accent";
	return (
		<span
			className={clsx("relative inline-flex shrink-0", sz, className)}
			aria-label="live"
			{...props}
		>
			<span
				className={clsx(
					"absolute inset-0 rounded-full opacity-40 animate-ping",
					dotColor,
				)}
			/>
			<span className={clsx("relative rounded-full", sz, dotColor)} />
		</span>
	);
}
