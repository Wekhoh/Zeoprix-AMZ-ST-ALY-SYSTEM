"use client";
/**
 * CopilotPanel — Phase 7.2 Amazon Seller Assistant 风
 * - Header: Zeoprix Assistant · Powered by Zeoprix + icon 组（新对话 / 历史 / 更多）
 * - Greeting area: sparkles 圆 icon + 名字 + welcome 文案 + "Ask anything" 引导
 * - 5 个建议 pills（满宽白底、蓝字、细 border 圆角矩形）
 * - 底部输入：灰色圆角胶囊 + `+` icon + placeholder + 蓝色圆形 send
 * - 免责声明
 */
import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
	Copy,
	MessageSquarePlus,
	RotateCcw,
	Send,
	Sparkles,
} from "lucide-react";

import { getPageContextKey, readPageContext } from "@/components/page-context";
import { BACKEND_BASE_URL } from "@/lib/backend";
import type { AICopilotCard } from "@/lib/mock-data";
import {
	streamCopilotChat,
	type CopilotEnvelopeFrame,
} from "@/lib/copilot-stream";
import { CopilotRichText } from "@/components/copilot-rich-text";

type Props = {
	productId?: number | null;
	pageKey: string;
	pageTitle: string;
	aiCard: AICopilotCard;
};

type ChatMessage = { role: "assistant" | "user"; content: string };
type ActionLink = { label: string; href: string };
type StoredCopilotState = {
	messages: ChatMessage[];
	prompts: string[];
	recommendedActions: string[];
	actionLinks: ActionLink[];
	contextLabel: string | null;
	warning: string | null;
};

function buildStorageKey(
	productId: number | null | undefined,
	pageKey: string,
) {
	return `zeoprix-copilot:${productId ?? "global"}:${pageKey}`;
}

export function CopilotPanel({ productId, pageKey, pageTitle, aiCard }: Props) {
	const router = useRouter();
	const storageKey = useMemo(
		() => buildStorageKey(productId, pageKey),
		[pageKey, productId],
	);
	const pageContextKey = useMemo(
		() => getPageContextKey(productId, pageKey),
		[pageKey, productId],
	);

	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [input, setInput] = useState("");
	const [prompts, setPrompts] = useState<string[]>(aiCard.prompts);
	const [recommendedActions, setRecommendedActions] = useState<string[]>([]);
	const [actionLinks, setActionLinks] = useState<ActionLink[]>([]);
	const [warning, setWarning] = useState<string | null>(null);
	const [pageContext, setPageContext] = useState<Record<string, unknown>>({});
	const [hydrated, setHydrated] = useState(false);
	const [pending, startTransition] = useTransition();

	const scrollRef = useRef<HTMLDivElement>(null);
	const inputRef = useRef<HTMLTextAreaElement>(null);
	const abortRef = useRef<AbortController | null>(null);
	const streamEnabled =
		(process.env.NEXT_PUBLIC_COPILOT_STREAM_ENABLED ?? "1") !== "0";

	useEffect(() => {
		return () => {
			abortRef.current?.abort();
		};
	}, []);

	useEffect(() => {
		try {
			const raw = window.sessionStorage.getItem(storageKey);
			if (raw) {
				const parsed = JSON.parse(raw) as Partial<StoredCopilotState>;
				if (parsed.messages?.length) setMessages(parsed.messages);
				if (parsed.prompts?.length) setPrompts(parsed.prompts);
				if (parsed.recommendedActions)
					setRecommendedActions(parsed.recommendedActions);
				if (parsed.actionLinks) setActionLinks(parsed.actionLinks);
				if (parsed.warning !== undefined) setWarning(parsed.warning);
			}
		} catch {
			// ignore
		}
		setHydrated(true);
	}, [storageKey]);

	useEffect(() => {
		if (!hydrated) return;
		try {
			window.sessionStorage.setItem(
				storageKey,
				JSON.stringify({
					messages,
					prompts,
					recommendedActions,
					actionLinks,
					contextLabel: null,
					warning,
				}),
			);
		} catch {
			// ignore
		}
	}, [
		actionLinks,
		hydrated,
		messages,
		prompts,
		recommendedActions,
		storageKey,
		warning,
	]);

	useEffect(() => {
		const sync = () => setPageContext(readPageContext(productId, pageKey));
		sync();
		const handle = (event: Event) => {
			const custom = event as CustomEvent<{ key?: string }>;
			if (!custom.detail?.key || custom.detail.key === pageContextKey) sync();
		};
		window.addEventListener(
			"zeoprix:page-context-updated",
			handle as EventListener,
		);
		window.addEventListener("storage", sync);
		return () => {
			window.removeEventListener(
				"zeoprix:page-context-updated",
				handle as EventListener,
			);
			window.removeEventListener("storage", sync);
		};
	}, [pageContextKey, pageKey, productId]);

	useEffect(() => {
		if (scrollRef.current)
			scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
	}, [messages, pending]);

	function clearConversation() {
		setMessages([]);
		setPrompts(aiCard.prompts);
		setRecommendedActions([]);
		setActionLinks([]);
		setWarning(null);
		setInput("");
		inputRef.current?.focus();
	}

	// Phase 7.3 UX: Esc 中止流式响应
	useEffect(() => {
		if (!pending) return;
		function onKey(e: KeyboardEvent) {
			if (e.key === "Escape") {
				abortRef.current?.abort();
			}
		}
		window.addEventListener("keydown", onKey);
		return () => window.removeEventListener("keydown", onKey);
	}, [pending]);

	const [copiedAt, setCopiedAt] = useState<number | null>(null);
	async function copyText(text: string, idx: number) {
		try {
			await navigator.clipboard.writeText(text);
			setCopiedAt(idx);
			setTimeout(() => setCopiedAt(null), 1200);
		} catch {
			// 浏览器不支持 / 权限拒绝时静默失败
		}
	}

	function regenerate() {
		// 找最后一条 user 消息，回退到它之前的状态再重发
		for (let i = messages.length - 1; i >= 0; i--) {
			if (messages[i].role === "user") {
				const lastUser = messages[i].content;
				sendMessage(lastUser, { regenerate: true });
				return;
			}
		}
	}

	async function sendMessage(
		message: string,
		options?: { regenerate?: boolean },
	) {
		const trimmed = message.trim();
		if (!trimmed) return;
		// regenerate：截掉最后一条匹配的 user 消息及其后的所有内容
		let baseMessages = messages;
		if (options?.regenerate) {
			for (let i = messages.length - 1; i >= 0; i--) {
				if (messages[i].role === "user" && messages[i].content === trimmed) {
					baseMessages = messages.slice(0, i);
					break;
				}
			}
		}
		const nextMessages = [
			...baseMessages,
			{ role: "user" as const, content: trimmed },
			{ role: "assistant" as const, content: "" },
		];
		setMessages(nextMessages);
		setInput("");
		setWarning(null);

		abortRef.current?.abort();
		abortRef.current = new AbortController();

		const appendToLastAssistant = (text: string) => {
			setMessages((current) => {
				if (current.length === 0) return current;
				const last = current[current.length - 1];
				if (last.role !== "assistant") return current;
				const patched = { ...last, content: last.content + text };
				return [...current.slice(0, -1), patched];
			});
		};

		const applyEnvelope = (env: CopilotEnvelopeFrame) => {
			setPrompts(
				env.followUpPrompts.length ? env.followUpPrompts : aiCard.prompts,
			);
			setRecommendedActions(env.recommendedNextActions);
			setActionLinks(env.actionLinks);
			setWarning(env.warning);
		};

		const fallbackNonStream = async () => {
			try {
				const response = await fetch(
					`${BACKEND_BASE_URL}/frontend/copilot/chat`,
					{
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({
							product_id: productId ?? null,
							page_key: pageKey,
							page_title: pageTitle,
							page_context: pageContext,
							user_message: trimmed,
							history: nextMessages.slice(-6),
						}),
					},
				);
				const body = (await response
					.json()
					.catch(() => ({ message: "AI 助手当前不可用。" }))) as {
					message?: string;
					followUpPrompts?: string[];
					recommendedNextActions?: string[];
					actionLinks?: ActionLink[];
					warning?: string | null;
				};
				appendToLastAssistant(body.message ?? "AI 助手当前不可用。");
				applyEnvelope({
					followUpPrompts: body.followUpPrompts ?? [],
					recommendedNextActions: body.recommendedNextActions ?? [],
					actionLinks: body.actionLinks ?? [],
					warning: body.warning ?? null,
				});
			} catch {
				setWarning("AI 助手当前不可用，请稍后再试。");
			}
		};

		startTransition(async () => {
			if (!streamEnabled) {
				await fallbackNonStream();
				return;
			}
			try {
				await streamCopilotChat(
					{
						product_id: productId ?? null,
						page_key: pageKey,
						page_title: pageTitle,
						page_context: pageContext,
						user_message: trimmed,
						history: nextMessages.slice(-6),
					},
					{
						onDelta: appendToLastAssistant,
						onEnvelope: applyEnvelope,
						onError: async (msg, meta) => {
							// 流中断（已收到部分内容）：保留 partial 内容，不触发 fallback
							// 避免重复请求 Gemini 把已收到的内容覆盖掉
							if (meta?.partial && meta?.recoverable) {
								appendToLastAssistant(
									`\n\n（响应被中断，已接收 ${meta.chunksReceived ?? 0} 个 chunk）`,
								);
								setWarning(`${msg}，可重新发送以重试`);
								return;
							}
							// 流前/不可恢复错误：清掉空占位 + 回退到稳定模式
							setMessages((current) => {
								const last = current[current.length - 1];
								if (last?.role === "assistant" && last.content === "") {
									return current.slice(0, -1);
								}
								return current;
							});
							setWarning(`流式请求失败：${msg}，已回退到稳定模式`);
							await fallbackNonStream();
						},
						signal: abortRef.current!.signal,
					},
				);
			} finally {
				abortRef.current = null;
			}
		});
	}

	const hasMessages = messages.length > 0;
	const recentMessages = messages.slice(-12);
	const visiblePrompts = prompts.slice(0, 5);

	return (
		<section className="flex h-full flex-col bg-bg-elevated">
			{/* ═══ Header ═══ */}
			<header className="flex items-start justify-between gap-2 px-4 pt-4 pb-3 border-b border-border">
				<div>
					<h2 className="text-[16px] font-bold text-fg leading-tight">
						Zeoprix Assistant
					</h2>
					<p className="text-[12px] text-fg-muted leading-tight mt-0.5">
						Powered by Zeoprix
					</p>
				</div>
				<div className="flex items-center gap-0.5">
					<button
						type="button"
						title="新对话"
						onClick={clearConversation}
						className="inline-flex h-7 w-7 items-center justify-center rounded-full text-fg-muted hover:bg-bg-subtle hover:text-fg transition-colors"
					>
						<MessageSquarePlus className="h-4 w-4" />
					</button>
				</div>
			</header>

			{/* ═══ Content ═══ */}
			<div
				ref={scrollRef}
				className="flex-1 overflow-y-auto px-4 py-4 space-y-3.5"
			>
				{!hasMessages ? (
					<>
						<div className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-border">
							<Sparkles className="h-3.5 w-3.5 text-fg-muted" />
						</div>

						<h3 className="text-[15px] font-semibold text-fg mt-3">
							Zeoprix Assistant
						</h3>
						<p className="text-[13px] text-fg-muted leading-[1.55]">
							你好，我是 Zeoprix Assistant —
							让我用数据和运营经验帮你做更好的决策。
						</p>

						<p className="text-[13px] text-fg leading-[1.55] mt-2">
							<strong className="font-semibold">追问任意问题</strong>
							，或从下面选一个开始：
						</p>

						<div className="space-y-2 pt-1">
							{visiblePrompts.map((prompt) => (
								<button
									key={prompt}
									type="button"
									onClick={() => sendMessage(prompt)}
									className="w-full text-left px-3.5 py-2.5 rounded-lg border border-border bg-bg-elevated hover:bg-bg-subtle hover:border-border-strong text-[13px] text-link transition-colors"
								>
									{prompt}
								</button>
							))}
						</div>
					</>
				) : (
					(() => {
						let lastAsstIdx = -1;
						for (let i = recentMessages.length - 1; i >= 0; i--) {
							if (recentMessages[i].role === "assistant") {
								lastAsstIdx = i;
								break;
							}
						}
						return recentMessages.map((message, index) =>
							message.role === "assistant" ? (
								<div
									key={`${message.role}-${index}`}
									className="group flex items-start gap-2.5"
								>
									<span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border">
										<Sparkles className="h-3 w-3 text-fg-muted" aria-hidden />
									</span>
									<div className="flex-1 min-w-0">
										<div className="text-[13.5px] leading-[1.6] text-fg whitespace-pre-wrap">
											<CopilotRichText text={message.content} />
										</div>
										{message.content && !pending ? (
											<div className="mt-1 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
												<button
													type="button"
													title={copiedAt === index ? "已复制" : "复制"}
													onClick={() => copyText(message.content, index)}
													className="inline-flex h-6 w-6 items-center justify-center rounded text-fg-subtle hover:bg-bg-subtle hover:text-fg transition-colors"
												>
													<Copy className="h-3 w-3" />
												</button>
												{index === lastAsstIdx ? (
													<button
														type="button"
														title="重新生成"
														onClick={regenerate}
														className="inline-flex h-6 w-6 items-center justify-center rounded text-fg-subtle hover:bg-bg-subtle hover:text-fg transition-colors"
													>
														<RotateCcw className="h-3 w-3" />
													</button>
												) : null}
												{copiedAt === index ? (
													<span className="text-[11px] text-fg-subtle">
														已复制
													</span>
												) : null}
											</div>
										) : null}
									</div>
								</div>
							) : (
								<div
									key={`${message.role}-${index}`}
									className="flex justify-end"
								>
									<div className="max-w-[85%] rounded-2xl bg-bg-subtle px-3.5 py-2 text-[13.5px] leading-[1.55] text-fg whitespace-pre-wrap">
										{message.content}
									</div>
								</div>
							),
						);
					})()
				)}

				{pending ? (
					<div className="flex items-center gap-2.5">
						<span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border">
							<Sparkles className="h-3 w-3 text-fg-muted" aria-hidden />
						</span>
						<div className="flex gap-1 py-2">
							<span
								className="h-1.5 w-1.5 rounded-full bg-fg-subtle animate-bounce"
								style={{ animationDelay: "0ms" }}
							/>
							<span
								className="h-1.5 w-1.5 rounded-full bg-fg-subtle animate-bounce"
								style={{ animationDelay: "150ms" }}
							/>
							<span
								className="h-1.5 w-1.5 rounded-full bg-fg-subtle animate-bounce"
								style={{ animationDelay: "300ms" }}
							/>
						</div>
					</div>
				) : null}

				{warning ? (
					<div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning-bg px-3 py-2 text-[12.5px] leading-[1.55] text-warning-fg">
						<span className="mt-0.5">⚠</span>
						<span>{warning}</span>
					</div>
				) : null}

				{hasMessages && actionLinks.length > 0 ? (
					<div className="flex flex-wrap gap-x-3 gap-y-1 pt-1">
						{actionLinks.map((link) => (
							<button
								key={link.href}
								type="button"
								onClick={() => router.push(link.href)}
								className="text-[12px] text-link hover:underline"
							>
								→ {link.label}
							</button>
						))}
					</div>
				) : null}

				{hasMessages && visiblePrompts.length > 0 && !pending ? (
					<div className="pt-2 space-y-1.5">
						{visiblePrompts.slice(0, 3).map((prompt) => (
							<button
								key={prompt}
								type="button"
								onClick={() => sendMessage(prompt)}
								className="block w-full text-left px-3 py-2 rounded-lg border border-border bg-bg-elevated hover:bg-bg-subtle text-[12.5px] text-link transition-colors"
							>
								{prompt}
							</button>
						))}
					</div>
				) : null}
			</div>

			{/* ═══ Input ═══ */}
			<div className="px-3 pb-3 pt-2 border-t border-border">
				<div className="flex items-center gap-2 bg-bg-subtle rounded-full pl-3 pr-1 py-1">
					<textarea
						ref={inputRef}
						value={input}
						onChange={(e) => setInput(e.target.value)}
						onKeyDown={(e) => {
							if (e.key === "Enter" && !e.shiftKey) {
								e.preventDefault();
								sendMessage(input);
							}
						}}
						placeholder={`Message Zeoprix Assistant…`}
						rows={1}
						className="flex-1 min-w-0 resize-none bg-transparent text-[13.5px] leading-[1.5] text-fg outline-none placeholder:text-fg-subtle py-1.5 px-0.5 max-h-28"
					/>
					<button
						type="button"
						disabled={pending || !input.trim()}
						onClick={() => sendMessage(input)}
						className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-link text-white hover:bg-link-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
						aria-label="发送"
						title={pending ? "Esc 中止" : "发送 (Enter，Shift+Enter 换行)"}
					>
						<Send className="h-3.5 w-3.5" />
					</button>
				</div>
				<p className="text-center text-[11px] text-fg-subtle mt-2 px-2">
					Zeoprix Assistant 仍在学习中，请核对回复。
					{pending ? " · Esc 中止" : ""}
				</p>
			</div>
		</section>
	);
}
