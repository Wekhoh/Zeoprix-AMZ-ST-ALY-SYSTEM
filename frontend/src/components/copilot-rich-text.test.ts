/**
 * Vitest unit — Phase 7.3 markdown 升级
 *
 * 验证 injectAsinLinks 把 plain prose 中的 ASIN 转 markdown 链接，
 * 同时保留 fenced code blocks / 反引号 inline code 不被替换。
 *
 * 不 render React，只测预处理函数本身。
 */

import { describe, it, expect } from "vitest";

import { injectAsinLinks } from "./copilot-rich-text";

describe("CopilotRichText.injectAsinLinks", () => {
	it("returns input unchanged when no ASIN match", () => {
		const out = injectAsinLinks("普通文字，没有 ASIN 也没有反引号");
		expect(out).toBe("普通文字，没有 ASIN 也没有反引号");
	});

	it("converts plain ASIN to markdown link with uppercase normalization", () => {
		const out = injectAsinLinks("可以看 b07xyz1234 的详情");
		expect(out).toBe("可以看 [B07XYZ1234](/review?focus=B07XYZ1234) 的详情");
	});

	it("converts multiple ASINs preserving order", () => {
		const out = injectAsinLinks("B01ABC1234 和 B07XYZ5678 都是候选");
		expect(out).toBe(
			"[B01ABC1234](/review?focus=B01ABC1234) 和 [B07XYZ5678](/review?focus=B07XYZ5678) 都是候选",
		);
	});

	it("does NOT replace ASIN inside backtick inline code", () => {
		const out = injectAsinLinks("看看 `B07ABC1234 相关词`");
		expect(out).toBe("看看 `B07ABC1234 相关词`");
	});

	it("does NOT replace ASIN inside fenced code blocks", () => {
		const input = "示例：\n```\nB07ABC1234\n```";
		const out = injectAsinLinks(input);
		expect(out).toContain("```\nB07ABC1234\n```");
		expect(out).not.toContain("[B07ABC1234]");
	});

	it("preserves backtick code while replacing surrounding ASIN", () => {
		const out = injectAsinLinks("ASIN B07SRRQS5B 用 `travel pillow` 查");
		expect(out).toBe(
			"ASIN [B07SRRQS5B](/review?focus=B07SRRQS5B) 用 `travel pillow` 查",
		);
	});

	it("returns empty string for empty input", () => {
		expect(injectAsinLinks("")).toBe("");
	});
});
