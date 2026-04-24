/**
 * <Kbd> — 键盘快捷键视觉（⌘ K / Ctrl K / Esc / 1...）
 */
import * as React from "react";
import { clsx } from "clsx";

export type KbdProps = React.HTMLAttributes<HTMLElement>;

export function Kbd({ className, children, ...props }: KbdProps) {
	return (
		<kbd
			className={clsx(
				"inline-flex items-center justify-center",
				"min-w-[1.5rem] px-1.5 py-0.5",
				"rounded border border-border bg-bg-subtle",
				"text-xs font-mono font-medium text-fg-muted leading-none",
				className,
			)}
			{...props}
		>
			{children}
		</kbd>
	);
}
