"use client";
/**
 * CopilotRichText — Sprint 4 · A2
 *
 * 把 Copilot 回复文本里的 ASIN (B0 + 8 alnum) 和反引号包裹的关键词
 * 渲染成可点击链接：
 *   - ASIN `B0XXXXXXXX` → /review?focus={asin}
 *   - `关键词` (反引号) → /analysis?focus={term}
 *
 * 手写 regex tokenizer（无依赖 / 无 react-markdown，以降低 bundle 开销）。
 */
import Link from "next/link";
import type { ReactNode } from "react";

// ASIN: B0 prefix + 8 alphanumeric chars, case-insensitive, word-boundary
const ASIN_RE = /\bB0[A-Z0-9]{8}\b/gi;
// Backtick-wrapped keyword: `abc def` (non-greedy, no embedded backtick)
const TERM_RE = /`([^`\n]+)`/g;

type Token =
	| { kind: "text"; value: string }
	| { kind: "asin"; value: string }
	| { kind: "term"; value: string };

type Match = {
	start: number;
	end: number;
	kind: "asin" | "term";
	value: string;
};

export function tokenize(input: string): Token[] {
	const tokens: Token[] = [];
	let cursor = 0;
	const matches: Match[] = [];

	for (const m of input.matchAll(ASIN_RE)) {
		matches.push({
			start: m.index ?? 0,
			end: (m.index ?? 0) + m[0].length,
			kind: "asin",
			value: m[0].toUpperCase(),
		});
	}
	for (const m of input.matchAll(TERM_RE)) {
		const start = m.index ?? 0;
		matches.push({
			start,
			end: start + m[0].length,
			kind: "term",
			value: m[1],
		});
	}

	matches.sort((a, b) => a.start - b.start || b.end - a.end);

	// Drop overlapping matches (keep the earliest-starting one).
	const filtered: Match[] = [];
	let lastEnd = -1;
	for (const m of matches) {
		if (m.start >= lastEnd) {
			filtered.push(m);
			lastEnd = m.end;
		}
	}

	for (const m of filtered) {
		if (m.start > cursor) {
			tokens.push({ kind: "text", value: input.slice(cursor, m.start) });
		}
		tokens.push({ kind: m.kind, value: m.value });
		cursor = m.end;
	}
	if (cursor < input.length) {
		tokens.push({ kind: "text", value: input.slice(cursor) });
	}
	return tokens;
}

export function CopilotRichText({ text }: { text: string }) {
	if (!text) return null;
	const tokens = tokenize(text);
	const nodes: ReactNode[] = [];
	for (let i = 0; i < tokens.length; i++) {
		const t = tokens[i];
		// 复合 key = kind + 位置 + 内容指纹；同 kind 同 value 多次出现仍唯一
		const tokKey = `${t.kind}-${i}-${t.value}`;
		if (t.kind === "text") {
			nodes.push(<span key={tokKey}>{t.value}</span>);
		} else if (t.kind === "asin") {
			nodes.push(
				<Link
					key={tokKey}
					href={`/review?focus=${encodeURIComponent(t.value)}`}
					className="font-mono text-link hover:underline"
					title={`在审核中心聚焦 ASIN ${t.value}`}
				>
					{t.value}
				</Link>,
			);
		} else {
			nodes.push(
				<Link
					key={tokKey}
					href={`/analysis?focus=${encodeURIComponent(t.value)}`}
					className="text-link hover:underline"
					title={`在搜索词分析中聚焦「${t.value}」`}
				>
					{t.value}
				</Link>,
			);
		}
	}
	return <>{nodes}</>;
}
