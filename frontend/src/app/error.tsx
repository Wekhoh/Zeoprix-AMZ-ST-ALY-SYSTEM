"use client";
/**
 * Root error boundary — Sprint 5 · C.5
 *
 * Next.js 16 App Router 约定文件：捕获本路由段及其子段抛出的渲染错误，
 * 提供"出错了 + 重试 / 返回首页"兜底界面。
 *
 * 不可被 server-only 错误拦截（那需要 global-error.tsx）。当前这个版本
 * 已覆盖所有 6 个 dynamic 页面 + /demo + /_not-found 的渲染异常。
 */
import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

type Props = {
	error: Error & { digest?: string };
	reset: () => void;
};

export default function GlobalRouteError({ error, reset }: Props) {
	useEffect(() => {
		// dev: 控制台打印完整 error 便于调试
		// prod: 仅记录 digest (Next.js 自动哈希) 便于服务端追溯
		// eslint-disable-next-line no-console
		console.error(
			"[route-error]",
			error.digest ?? "no-digest",
			error.message,
			error,
		);
	}, [error]);

	const isDev = process.env.NODE_ENV === "development";

	return (
		<main className="min-h-[calc(100vh-52px)] flex items-center justify-center px-6 py-10">
			<section className="w-full max-w-lg bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-warning-bg/30">
					<AlertTriangle className="h-4 w-4 text-warning-fg" />
					<h2 className="text-warning-fg">页面出错了</h2>
				</div>
				<div className="p-6 space-y-4">
					<p className="text-[14px] leading-[1.65] text-fg">
						抱歉，这个页面在渲染时遇到了未预期的错误。
						你可以点击「重试」让它再加载一次，或者返回首页继续其他操作。
					</p>

					{isDev && error.message ? (
						<details className="text-[12.5px] text-fg-muted bg-bg-subtle rounded border border-border p-3">
							<summary className="cursor-pointer text-fg-muted hover:text-fg select-none">
								开发者详情（仅 development 可见）
							</summary>
							<pre className="mt-2 whitespace-pre-wrap break-words font-mono text-[12px] leading-[1.5]">
								{error.message}
								{error.digest ? `\n\ndigest: ${error.digest}` : ""}
								{error.stack ? `\n\n${error.stack}` : ""}
							</pre>
						</details>
					) : null}

					{error.digest && !isDev ? (
						<div className="text-[12px] text-fg-subtle font-mono">
							错误码：<span className="text-fg-muted">{error.digest}</span>
						</div>
					) : null}

					<div className="flex flex-wrap items-center gap-2 pt-1">
						<button
							type="button"
							onClick={reset}
							className="inline-flex items-center gap-1.5 px-3 h-9 rounded-full bg-accent text-on-primary text-[13px] font-semibold hover:bg-accent-strong transition-colors"
						>
							<RefreshCw className="h-3.5 w-3.5" />
							重试
						</button>
						<Link
							href="/"
							className="inline-flex items-center gap-1.5 px-3 h-9 rounded-full bg-bg-elevated border border-border text-fg-muted text-[13px] hover:bg-bg-subtle hover:text-fg transition-colors"
						>
							<Home className="h-3.5 w-3.5" />
							返回首页
						</Link>
					</div>
				</div>
			</section>
		</main>
	);
}
