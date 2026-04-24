"use client";
/**
 * /demo — Sprint 2 DS 验收陈列页
 * 所有 10 个 UI 组件 + typography + color token + 对比度标注
 */
import * as React from "react";
import { FileSearch } from "lucide-react";

import { Card, CardHeader, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Kbd } from "@/components/ui/kbd";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { ToastProvider, useToast } from "@/components/ui/toast";
import { CommandPalette } from "@/components/ui/command-palette";

function ToastDemo() {
	const { push } = useToast();
	return (
		<div className="flex flex-wrap gap-2">
			<Button
				variant="secondary"
				onClick={() => push({ title: "操作完成", description: "一条默认通知" })}
			>
				Default Toast
			</Button>
			<Button
				variant="secondary"
				onClick={() =>
					push({
						tone: "success",
						title: "上传成功",
						description: "32 行数据已入库",
					})
				}
			>
				Success
			</Button>
			<Button
				variant="secondary"
				onClick={() =>
					push({
						tone: "warning",
						title: "部分失败",
						description: "2 个文件解析异常",
					})
				}
			>
				Warning
			</Button>
			<Button
				variant="secondary"
				onClick={() =>
					push({
						tone: "error",
						title: "请求失败",
						description: "Gemini API 配额用尽",
					})
				}
			>
				Error
			</Button>
		</div>
	);
}

const contrastSamples = [
	{ name: "fg on bg", fg: "text-fg", bg: "bg-bg", ratio: "18.62 : 1 · AAA" },
	{
		name: "fg-muted on bg",
		fg: "text-fg-muted",
		bg: "bg-bg",
		ratio: "7.57 : 1 · AAA",
	},
	{
		name: "fg-subtle on bg",
		fg: "text-fg-subtle",
		bg: "bg-bg",
		ratio: "5.22 : 1 · AA",
	},
	{
		name: "accent-fg on accent-bg",
		fg: "text-accent-fg",
		bg: "bg-accent-bg",
		ratio: "5.88 : 1 · AA",
	},
	{
		name: "success-fg on success-bg",
		fg: "text-success-fg",
		bg: "bg-success-bg",
		ratio: "4.63 : 1 · AA",
	},
	{
		name: "warning-fg on warning-bg",
		fg: "text-warning-fg",
		bg: "bg-warning-bg",
		ratio: "7.94 : 1 · AAA",
	},
	{
		name: "error-fg on error-bg",
		fg: "text-error-fg",
		bg: "bg-error-bg",
		ratio: "5.64 : 1 · AA",
	},
	{
		name: "fg on highlight",
		fg: "text-fg",
		bg: "bg-highlight",
		ratio: "≥ 18 : 1 · AAA",
	},
];

export default function DemoPage() {
	return (
		<ToastProvider>
			<CommandPalette />
			<main className="min-h-screen bg-bg text-fg">
				<header className="border-b border-border">
					<div className="mx-auto max-w-5xl px-6 py-8 flex items-center justify-between gap-4">
						<div className="min-w-0">
							<h1 className="text-3xl font-semibold tracking-tight">
								Design System
							</h1>
							<p className="mt-2 text-sm text-fg-muted">
								Vercel × Notion hybrid · Sprint 2 验收 · 所有颜色通过 WCAG 2.1
								AA
							</p>
						</div>
						<div className="flex items-center gap-3 shrink-0">
							<span className="text-xs text-fg-subtle hidden sm:inline-flex items-center gap-1">
								按 <Kbd>Ctrl</Kbd> <Kbd>K</Kbd> 打开命令面板
							</span>
							<ThemeToggle />
						</div>
					</div>
				</header>

				<div className="mx-auto max-w-5xl px-6 py-12 space-y-12">
					<Section
						title="Typography"
						description="严格 codified 字号/行高/字距，禁止魔术数字"
					>
						<Card>
							<div className="space-y-3">
								<h1 className="text-5xl font-semibold tracking-tight">
									64 · 5xl Hero Heading
								</h1>
								<h2 className="text-4xl font-semibold tracking-tight">
									48 · 4xl Page Title
								</h2>
								<h3 className="text-3xl font-semibold tracking-tight">
									32 · 3xl Section
								</h3>
								<h4 className="text-2xl font-semibold tracking-tight">
									24 · 2xl Subsection
								</h4>
								<h5 className="text-xl font-semibold tracking-tight">
									20 · xl Card Title
								</h5>
								<p className="text-lg">
									18 · lg 强调段落。Notion 舒展行高 1.6 让长文字易读。
								</p>
								<p className="text-base">
									16 · base 正文默认。Vercel 微 letter-spacing -0.005em
									让字形更紧凑。
								</p>
								<p className="text-sm text-fg-muted">
									14 · sm 次要文字（fg-muted 对比度 7.57 : 1 AAA）
								</p>
								<p className="text-xs text-fg-subtle">
									12 · xs meta 信息（fg-subtle 5.22 : 1 AA）
								</p>
								<code className="text-sm">{"Geist Mono: const x = 42;"}</code>
							</div>
						</Card>
					</Section>

					<Section
						title="Colors & Contrast"
						description="每对 text/bg 已验证 WCAG AA"
					>
						<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
							{contrastSamples.map((c) => (
								<div
									key={c.name}
									className={`${c.bg} border border-border rounded-md px-4 py-3`}
								>
									<div className={`${c.fg} text-sm font-medium`}>{c.name}</div>
									<div className={`${c.fg} text-xs mt-1 opacity-80 font-mono`}>
										{c.ratio}
									</div>
								</div>
							))}
						</div>
					</Section>

					<Section title="Buttons">
						<Card>
							<div className="flex flex-wrap gap-3">
								<Button variant="primary">Primary</Button>
								<Button variant="secondary">Secondary</Button>
								<Button variant="ghost">Ghost</Button>
								<Button variant="danger">Danger</Button>
								<Button variant="primary" loading>
									Loading
								</Button>
								<Button variant="secondary" disabled>
									Disabled
								</Button>
							</div>
							<div className="flex flex-wrap gap-3 mt-4">
								<Button size="sm">Small</Button>
								<Button size="md">Medium</Button>
								<Button size="lg">Large</Button>
							</div>
						</Card>
					</Section>

					<Section title="Inputs">
						<Card>
							<div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-xl">
								<Input placeholder="Default input" />
								<Input placeholder="Disabled" disabled />
								<Input placeholder="Error state" error defaultValue="错误" />
								<Input placeholder="Small" inputSize="sm" />
							</div>
						</Card>
					</Section>

					<Section title="Badges">
						<Card>
							<div className="flex flex-wrap gap-2">
								<Badge>Default</Badge>
								<Badge tone="accent" dot>
									Active
								</Badge>
								<Badge tone="success" dot>
									Success
								</Badge>
								<Badge tone="warning" dot>
									Warning
								</Badge>
								<Badge tone="error" dot>
									Error
								</Badge>
							</div>
						</Card>
					</Section>

					<Section title="Cards" description="替换 codex 原 345+ 处裸写">
						<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
							<Card>
								<CardHeader title="默认卡片" description="1px 细边框，零阴影" />
								<p className="text-sm text-fg-muted">
									正文对比度 18.62 : 1 AAA
								</p>
								<CardFooter>
									<Button size="sm" variant="ghost">
										取消
									</Button>
									<Button size="sm" variant="primary">
										确认
									</Button>
								</CardFooter>
							</Card>
							<Card tone="muted">
								<CardHeader
									title="Muted"
									description="bg-bg-subtle"
									action={<Badge tone="accent">Tag</Badge>}
								/>
								<p className="text-sm text-fg-muted">次要分组容器</p>
							</Card>
							<Card tone="accent">
								<CardHeader
									title="Accent"
									description="accent tint 背景 + border-accent/40"
								/>
								<p className="text-sm text-accent-fg">强调场景</p>
							</Card>
							<Card interactive>
								<CardHeader title="Interactive" description="hover 边框加深" />
								<p className="text-sm text-fg-muted">hover 看看</p>
							</Card>
						</div>
					</Section>

					<Section title="Skeleton (Loading)">
						<Card>
							<div className="space-y-3">
								<Skeleton className="h-4 w-3/4" />
								<Skeleton className="h-4 w-1/2" />
								<Skeleton className="h-24 w-full" />
							</div>
						</Card>
					</Section>

					<Section title="Empty State">
						<EmptyState
							icon={<FileSearch className="h-10 w-10" />}
							heading="尚无分析数据"
							description="上传亚马逊广告搜索词报告后，规则引擎会自动生成建议"
							action={<Button variant="primary">去上传</Button>}
						/>
					</Section>

					<Section title="Toasts">
						<Card>
							<p className="text-sm text-fg-muted mb-4">
								点按钮触发通知，4 秒自动消失
							</p>
							<ToastDemo />
						</Card>
					</Section>

					<Section title="Keyboard & Command Palette">
						<Card>
							<p className="text-sm text-fg-muted">
								按 <Kbd>Ctrl</Kbd> <Kbd>K</Kbd>（Mac <Kbd>⌘</Kbd> <Kbd>K</Kbd>
								）打开命令面板跳转 6 页或触发 AI 动作；按 <Kbd>Esc</Kbd> 关闭
							</p>
						</Card>
					</Section>

					<div className="text-xs text-fg-subtle border-t border-border pt-6">
						Sprint 2 交付 · Vercel × Notion Design System · 10 个通用组件 ·
						所有颜色通过 WCAG 2.1 AA 对比度验证
					</div>
				</div>
			</main>
		</ToastProvider>
	);
}

function Section({
	title,
	description,
	children,
}: {
	title: string;
	description?: string;
	children: React.ReactNode;
}) {
	return (
		<section>
			<div className="mb-4">
				<h2 className="text-xl font-semibold tracking-tight">{title}</h2>
				{description && (
					<p className="mt-1 text-sm text-fg-muted">{description}</p>
				)}
			</div>
			{children}
		</section>
	);
}
