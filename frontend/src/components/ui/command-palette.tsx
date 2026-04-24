"use client";
/**
 * <CommandPalette> — Cmd+K 全局命令面板（Notion 风）
 * 跳转 6 页 + AI 动作（T29 占位，Sprint 4 接真实）
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
	BarChart3,
	ClipboardCheck,
	LayoutGrid,
	ListChecks,
	Settings as SettingsIcon,
	Sparkles,
	Upload,
} from "lucide-react";
import { clsx } from "clsx";

type NavItem = {
	label: string;
	href: string;
	icon: React.ComponentType<{ className?: string }>;
	keywords?: string[];
};

const navItems: NavItem[] = [
	{
		label: "运营工作台",
		href: "/",
		icon: LayoutGrid,
		keywords: ["workbench", "home", "dashboard", "首页"],
	},
	{
		label: "数据导入",
		href: "/upload",
		icon: Upload,
		keywords: ["upload", "import", "csv", "文件"],
	},
	{
		label: "搜索词分析",
		href: "/analysis",
		icon: BarChart3,
		keywords: ["analysis", "search-terms", "分析"],
	},
	{
		label: "审核中心",
		href: "/review",
		icon: ClipboardCheck,
		keywords: ["review", "pending", "相关性"],
	},
	{
		label: "操作清单",
		href: "/actions",
		icon: ListChecks,
		keywords: ["actions", "批次", "导出"],
	},
	{
		label: "数据管理",
		href: "/settings",
		icon: SettingsIcon,
		keywords: ["settings", "配置", "备份"],
	},
];

const headingClass =
	"[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-fg-subtle [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider";
const itemClass =
	"flex items-center gap-3 px-3 py-2 rounded-sm text-sm text-fg cursor-pointer data-[selected=true]:bg-bg-subtle";

export function CommandPalette() {
	const router = useRouter();
	const [open, setOpen] = React.useState(false);

	React.useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
				e.preventDefault();
				setOpen((v) => !v);
			}
		};
		document.addEventListener("keydown", handler);
		return () => document.removeEventListener("keydown", handler);
	}, []);

	const go = (href: string) => {
		setOpen(false);
		router.push(href);
	};

	return (
		<Command.Dialog
			open={open}
			onOpenChange={setOpen}
			label="全局命令面板"
			className={clsx(
				"fixed inset-0 z-50 flex items-start justify-center pt-[20vh]",
				"bg-fg/20 backdrop-blur-sm",
			)}
			contentClassName={clsx(
				"w-full max-w-lg mx-4",
				"rounded-lg border border-border bg-bg-elevated",
				"overflow-hidden",
			)}
		>
			<Command.Input
				placeholder="输入命令或跳转页面..."
				className={clsx(
					"w-full h-12 px-4 text-sm text-fg bg-transparent",
					"border-b border-border outline-none",
					"placeholder:text-fg-subtle",
				)}
			/>
			<Command.List className="max-h-[60vh] overflow-y-auto p-1">
				<Command.Empty className="px-4 py-8 text-center text-sm text-fg-muted">
					没有匹配结果
				</Command.Empty>
				<Command.Group heading="导航" className={headingClass}>
					{navItems.map((item) => {
						const Icon = item.icon;
						return (
							<Command.Item
								key={item.href}
								keywords={item.keywords}
								onSelect={() => go(item.href)}
								className={itemClass}
							>
								<Icon className="h-4 w-4 text-fg-muted" aria-hidden="true" />
								<span>{item.label}</span>
							</Command.Item>
						);
					})}
				</Command.Group>
				<Command.Group heading="AI 动作" className={headingClass}>
					<Command.Item
						onSelect={() => {
							setOpen(false);
							window.alert("Sprint 4 将接入：生成今日 AI 摘要");
						}}
						className={itemClass}
					>
						<Sparkles className="h-4 w-4 text-accent-fg" aria-hidden="true" />
						<span>生成今日摘要</span>
					</Command.Item>
				</Command.Group>
			</Command.List>
		</Command.Dialog>
	);
}
