"use client";
/**
 * DashboardShell — Phase 7.2 Amazon Ads Console + collapsible sidebar
 */
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
	Home,
	Upload as UploadIcon,
	BarChart3,
	CheckSquare,
	ListChecks,
	Settings,
	Bell,
	RotateCw,
	HelpCircle,
	User,
	ChevronsLeft,
	ChevronsRight,
	Sparkles,
} from "lucide-react";

import {
	aiCopilotCards,
	navItems,
	productContext as defaultProductContext,
	type AICopilotCard,
	type ProductContext,
} from "@/lib/mock-data";
import { CopilotPanel } from "@/components/copilot-panel";

interface DashboardShellProps {
	children: ReactNode;
	title: string;
	subtitle: string;
	productContext?: ProductContext | null;
	productId?: number | null;
	aiCard?: AICopilotCard | null;
}

const NAV_ICON_MAP: Record<
	string,
	React.ComponentType<{ className?: string }>
> = {
	"/": Home,
	"/upload": UploadIcon,
	"/analysis": BarChart3,
	"/actions": ListChecks,
	"/review": CheckSquare,
	"/settings": Settings,
};

const SIDEBAR_KEY = "zeoprix-sidebar-collapsed";
const COPILOT_KEY = "zeoprix-copilot-collapsed";

export function DashboardShell({
	children,
	title,
	subtitle,
	productContext,
	productId,
	aiCard,
}: DashboardShellProps) {
	const pathname = usePathname();
	const router = useRouter();
	const currentProduct = productContext ?? defaultProductContext;
	const primaryCard = aiCard ?? aiCopilotCards[0];
	const currentNav = navItems.find((n) => n.href === pathname);

	const [collapsed, setCollapsed] = useState(false);
	const [copilotCollapsed, setCopilotCollapsed] = useState(false);
	// 跳过 first mount 的 localStorage 写：避免一上来就把默认 false 覆盖掉
	// 用户已保存的 "1"。
	const [hasMounted, setHasMounted] = useState(false);

	useEffect(() => {
		try {
			const saved = window.localStorage.getItem(SIDEBAR_KEY);
			if (saved === "1") setCollapsed(true);
			const savedCopilot = window.localStorage.getItem(COPILOT_KEY);
			if (savedCopilot === "1") setCopilotCollapsed(true);
		} catch {
			// ignore
		}
		setHasMounted(true);
	}, []);

	// localStorage 同步必须放 effect，不能塞进 setState updater
	// （React 19 Strict Mode dev 下 updater 会被双调用，pure 是契约）
	useEffect(() => {
		if (!hasMounted) return;
		try {
			window.localStorage.setItem(SIDEBAR_KEY, collapsed ? "1" : "0");
		} catch {
			// ignore
		}
	}, [collapsed, hasMounted]);

	useEffect(() => {
		if (!hasMounted) return;
		try {
			window.localStorage.setItem(COPILOT_KEY, copilotCollapsed ? "1" : "0");
		} catch {
			// ignore
		}
	}, [copilotCollapsed, hasMounted]);

	function toggleSidebar() {
		setCollapsed((prev) => !prev);
	}

	function toggleCopilot() {
		setCopilotCollapsed((prev) => !prev);
	}

	// 用数字 + inline style 而非 Tailwind arbitrary class —— 绕过 Tailwind v4
	// JIT 在 ternary 双分支扫描时只生成 collapsed 分支（实测：CSS 里有
	// `.w-\[60px\]` `.w-\[44px\]` 但缺 `.w-\[220px\]` `.w-\[360px\]`）的 bug，
	// 导致展开态宽度规则缺失、aside 被 flex 压成内容宽度（60px）。
	const sidebarWidthPx = collapsed ? 60 : 220;
	const copilotWidthPx = copilotCollapsed ? 44 : 360;

	return (
		<div className="min-h-screen bg-bg text-fg">
			{/* ═══ 深 navy banner ═══ */}
			<header className="h-[52px] bg-primary text-on-primary flex items-center px-4 lg:px-6 gap-4 shrink-0">
				<Link href="/" className="flex items-center gap-2 shrink-0">
					<span className="text-[22px] font-bold tracking-tight leading-none">
						zeoprix
					</span>
					<span className="text-[11px] leading-none px-1.5 py-0.5 rounded bg-accent text-on-primary font-bold tracking-wider">
						ADS
					</span>
				</Link>

				<div className="h-5 w-px bg-white/20" />

				<div className="flex items-center gap-2 min-w-0">
					<span className="text-[16px] font-semibold text-white truncate">
						{currentNav?.label ?? "工作台"}
					</span>
					<Link
						href="/"
						title="首页"
						className="inline-flex h-6 w-6 items-center justify-center rounded hover:bg-white/10 transition-colors"
					>
						<Home className="h-4 w-4 text-white/70" />
					</Link>
				</div>

				<div className="flex-1" />

				<div className="hidden md:flex items-end flex-col text-[12px] text-white/90 leading-tight mr-3">
					<span className="font-semibold">{currentProduct.name}</span>
					<span className="text-white/60 text-[11px]">
						{currentProduct.workspace}
					</span>
				</div>
				<button
					type="button"
					title="刷新当前页 (router.refresh)"
					onClick={() => router.refresh()}
					className="inline-flex h-8 w-8 items-center justify-center rounded hover:bg-white/10 transition-colors"
				>
					<RotateCw className="h-4 w-4 text-white/80" />
				</button>
				<button
					type="button"
					title="通知"
					className="inline-flex h-8 w-8 items-center justify-center rounded hover:bg-white/10 transition-colors"
				>
					<Bell className="h-4 w-4 text-white/80" />
				</button>
				<button
					type="button"
					title="帮助"
					className="inline-flex h-8 w-8 items-center justify-center rounded hover:bg-white/10 transition-colors"
				>
					<HelpCircle className="h-4 w-4 text-white/80" />
				</button>
				<button
					type="button"
					title={currentProduct.role}
					className="inline-flex h-8 w-8 items-center justify-center rounded hover:bg-white/10 transition-colors"
				>
					<User className="h-4 w-4 text-white/80" />
				</button>
			</header>

			<div className="flex">
				{/* ═══ 可折叠 sidebar ═══ */}
				<aside
					style={{ width: sidebarWidthPx }}
					className="sticky top-0 h-[calc(100vh-52px)] shrink-0 bg-bg-elevated border-r border-border flex flex-col transition-[width] duration-200 ease-out"
				>
					<nav className="flex-1 py-2 overflow-y-auto">
						<ul className="space-y-0.5">
							{navItems.map((item) => {
								const active = pathname === item.href;
								const Icon = NAV_ICON_MAP[item.href] ?? Home;
								return (
									<li key={item.href} className="relative">
										{active ? (
											<span
												aria-hidden
												className="absolute left-0 top-1 bottom-1 w-[3px] bg-accent rounded-r"
											/>
										) : null}
										<Link
											href={item.href}
											title={collapsed ? item.label : undefined}
											className={
												"flex items-center h-10 mx-1.5 rounded transition-colors " +
												(collapsed ? "justify-center" : "gap-2.5 px-2.5") +
												(active
													? " bg-accent-bg text-accent-strong font-semibold"
													: " text-fg-muted hover:bg-bg-subtle hover:text-fg")
											}
										>
											<Icon className="h-4.5 w-4.5 shrink-0" aria-hidden />
											{collapsed ? null : (
												<span className="truncate text-[13px]">
													{item.label}
												</span>
											)}
										</Link>
									</li>
								);
							})}
						</ul>
					</nav>

					{/* Collapse toggle */}
					<div className="border-t border-border py-1.5 px-1.5">
						<button
							type="button"
							onClick={toggleSidebar}
							title={collapsed ? "展开侧栏" : "收起侧栏"}
							className={
								"flex items-center gap-2 w-full h-9 rounded text-[12px] text-fg-muted hover:bg-bg-subtle hover:text-fg transition-colors " +
								(collapsed ? "justify-center" : "px-2.5")
							}
						>
							{collapsed ? (
								<ChevronsRight className="h-4 w-4" />
							) : (
								<>
									<ChevronsLeft className="h-4 w-4 shrink-0" />
									<span className="truncate">收起侧栏</span>
								</>
							)}
						</button>
					</div>
				</aside>

				{/* ═══ Main content ═══ */}
				<div className="flex-1 min-w-0 flex">
					<main className="flex-1 min-w-0 px-6 lg:px-8 py-6">
						<div className="mb-5 flex items-baseline justify-between gap-4">
							<div className="min-w-0">
								<div className="text-[12px] text-fg-subtle mb-0.5">
									<Link href="/" className="hover:text-link hover:underline">
										zeoprix
									</Link>
									<span className="mx-1">/</span>
									<span>{currentNav?.label ?? "工作台"}</span>
								</div>
								<h1 className="text-fg truncate">{title}</h1>
								<p className="mt-1 text-[13px] text-fg-muted leading-[1.5] max-w-2xl">
									{subtitle}
								</p>
							</div>
							<div className="hidden lg:flex items-baseline gap-4 text-[12px] shrink-0">
								<span className="inline-flex items-baseline gap-1">
									<span className="text-fg-subtle">最近分析</span>
									<span className="font-mono tabular-nums text-fg">
										{currentProduct.lastAnalysisAt}
									</span>
								</span>
								<span className="inline-flex items-baseline gap-1">
									<span className="text-fg-subtle">备份</span>
									<span
										className={
											currentProduct.lastBackupAt.includes("暂无")
												? "text-warning-fg"
												: "text-fg"
										}
									>
										{currentProduct.lastBackupAt}
									</span>
								</span>
							</div>
						</div>

						{children}
					</main>

					<aside
						style={{ width: copilotWidthPx }}
						className="hidden lg:block sticky top-[52px] self-start shrink-0 h-[calc(100vh-52px)] border-l border-border bg-bg-elevated relative transition-[width] duration-200 ease-out"
					>
						{/* 浮动切换按钮：左边缘中心凹起的小圆按钮 */}
						<button
							type="button"
							onClick={toggleCopilot}
							title={copilotCollapsed ? "展开 AI 对话" : "收起 AI 对话"}
							aria-label={copilotCollapsed ? "展开 AI 对话" : "收起 AI 对话"}
							className="absolute left-0 top-4 -translate-x-1/2 z-10 inline-flex h-6 w-6 items-center justify-center rounded-full bg-bg-elevated border border-border shadow-sm text-fg-muted hover:bg-bg-subtle hover:text-fg transition-colors"
						>
							{copilotCollapsed ? (
								<ChevronsLeft className="h-3.5 w-3.5" />
							) : (
								<ChevronsRight className="h-3.5 w-3.5" />
							)}
						</button>

						{copilotCollapsed ? (
							<div className="h-full flex flex-col items-center pt-14 gap-4">
								<span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-border bg-bg-subtle">
									<Sparkles className="h-3.5 w-3.5 text-accent-strong" />
								</span>
								<span
									className="text-[11px] text-fg-subtle font-semibold tracking-wider uppercase"
									style={{ writingMode: "vertical-rl" }}
								>
									Zeoprix Assistant
								</span>
							</div>
						) : (
							<CopilotPanel
								productId={productId ?? null}
								pageKey={
									pathname === "/" ? "workbench" : pathname.replace("/", "")
								}
								pageTitle={title}
								aiCard={primaryCard}
							/>
						)}
					</aside>
				</div>
			</div>
		</div>
	);
}
