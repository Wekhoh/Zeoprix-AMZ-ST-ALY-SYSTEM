"use client";
/**
 * CopilotRichText — Phase 7.3 真 markdown 渲染
 *
 * Gemini 回复常含 markdown：## headers / **bold** / `code` / 列表 / fenced code。
 * 之前手写 tokenizer 仅识别 ASIN 和反引号 keyword，其它符号原样显示。
 * 现在用 react-markdown 全量渲染，并在外层注入 2 个特殊跳转：
 *   - ASIN (B0+8 alnum) → /review?focus={asin}
 *   - 反引号 `term` → /analysis?focus={term}（内部 inline code 渲染为链接）
 */
import Link from "next/link";
import ReactMarkdown, { type Components } from "react-markdown";

const ASIN_RE = /\bB0[A-Z0-9]{8}\b/gi;

/**
 * 把 plain prose 中的 ASIN 转 markdown link，避开 fenced code 和反引号。
 */
export function injectAsinLinks(input: string): string {
	const fences: string[] = [];
	let s = input.replace(/```[\s\S]*?```/g, (m) => {
		fences.push(m);
		return ` FENCE${fences.length - 1}`;
	});
	const codes: string[] = [];
	s = s.replace(/`[^`\n]+`/g, (m) => {
		codes.push(m);
		return ` CODE${codes.length - 1}`;
	});
	s = s.replace(ASIN_RE, (m) => {
		const upper = m.toUpperCase();
		return `[${upper}](/review?focus=${upper})`;
	});
	s = s.replace(/ CODE(\d+)/g, (_, i) => codes[Number(i)]);
	s = s.replace(/ FENCE(\d+)/g, (_, i) => fences[Number(i)]);
	return s;
}

const components: Components = {
	// 反引号 `term` → 跳到 /analysis；fenced ```code``` 保持代码样式
	code({ className, children, ...props }) {
		const isBlock = !!(className && /^language-/.test(className));
		if (isBlock) {
			return (
				<code className={`${className ?? ""} font-mono text-[12px]`} {...props}>
					{children}
				</code>
			);
		}
		const term = String(children).trim();
		if (!term) {
			return <code {...props}>{children}</code>;
		}
		return (
			<Link
				href={`/analysis?focus=${encodeURIComponent(term)}`}
				className="font-mono text-link hover:underline"
				title={`在搜索词分析中聚焦「${term}」`}
			>
				{term}
			</Link>
		);
	},
	pre({ children, ...props }) {
		return (
			<pre
				className="my-2 rounded bg-bg-subtle px-3 py-2 text-[12px] font-mono overflow-x-auto"
				{...props}
			>
				{children}
			</pre>
		);
	},
	a({ href, children, ...props }) {
		if (href && (href.startsWith("/review") || href.startsWith("/analysis"))) {
			return (
				<Link href={href} className="font-mono text-link hover:underline">
					{children}
				</Link>
			);
		}
		return (
			<a
				href={href}
				target="_blank"
				rel="noopener noreferrer"
				className="text-link hover:underline"
				{...props}
			>
				{children}
			</a>
		);
	},
	p({ children }) {
		return <p className="my-1.5 first:mt-0 last:mb-0">{children}</p>;
	},
	h1({ children }) {
		return <h1 className="text-[15px] font-bold mt-3 mb-1.5">{children}</h1>;
	},
	h2({ children }) {
		return <h2 className="text-[14px] font-bold mt-2.5 mb-1">{children}</h2>;
	},
	h3({ children }) {
		return (
			<h3 className="text-[13.5px] font-semibold mt-2 mb-1">{children}</h3>
		);
	},
	h4({ children }) {
		return <h4 className="text-[13px] font-semibold mt-2 mb-1">{children}</h4>;
	},
	ul({ children }) {
		return <ul className="list-disc pl-5 my-1.5 space-y-0.5">{children}</ul>;
	},
	ol({ children }) {
		return <ol className="list-decimal pl-5 my-1.5 space-y-0.5">{children}</ol>;
	},
	li({ children }) {
		return <li className="leading-[1.55]">{children}</li>;
	},
	strong({ children }) {
		return <strong className="font-semibold">{children}</strong>;
	},
	em({ children }) {
		return <em className="italic">{children}</em>;
	},
	blockquote({ children }) {
		return (
			<blockquote className="my-2 border-l-2 border-border pl-3 text-fg-muted italic">
				{children}
			</blockquote>
		);
	},
	hr() {
		return <hr className="my-3 border-border" />;
	},
};

export function CopilotRichText({ text }: { text: string }) {
	if (!text) return null;
	const processed = injectAsinLinks(text);
	return <ReactMarkdown components={components}>{processed}</ReactMarkdown>;
}
