"use client";
/**
 * <ThemeToggle> — 3 档切换（light / dark / system）
 * 用 next-themes；suppressHydrationWarning 避免初次 SSR 不一致
 */
import * as React from "react";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { clsx } from "clsx";

const options = [
	{ key: "light", icon: Sun, label: "浅色" },
	{ key: "dark", icon: Moon, label: "深色" },
	{ key: "system", icon: Monitor, label: "跟随系统" },
] as const;

export function ThemeToggle({ className }: { className?: string }) {
	const { theme, setTheme } = useTheme();
	const [mounted, setMounted] = React.useState(false);

	React.useEffect(() => {
		setMounted(true);
	}, []);

	return (
		<div
			className={clsx(
				"inline-flex items-center rounded-md border border-border bg-bg-elevated p-0.5",
				className,
			)}
			role="radiogroup"
			aria-label="主题切换"
		>
			{options.map(({ key, icon: Icon, label }) => {
				const active = mounted && theme === key;
				return (
					<button
						key={key}
						type="button"
						role="radio"
						aria-checked={active}
						aria-label={label}
						title={label}
						onClick={() => setTheme(key)}
						className={clsx(
							"inline-flex items-center justify-center rounded-sm",
							"h-7 w-7",
							"transition-colors duration-150",
							"text-fg-subtle hover:text-fg",
							active && "bg-bg-subtle text-fg",
						)}
						suppressHydrationWarning
					>
						<Icon className="h-4 w-4" aria-hidden="true" />
					</button>
				);
			})}
		</div>
	);
}
