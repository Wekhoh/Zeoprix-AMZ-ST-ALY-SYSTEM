/**
 * Vitest unit — Sprint 5 · D.8c
 *
 * 验证 CopilotRichText 内部 `tokenize` 纯函数对 ASIN / 反引号关键词
 * 的识别、大小写规范化、重叠决议、多片段混排的正确性。
 *
 * 不 render React（避免引 jsdom + testing-library），只测 tokenizer 本身。
 */

import { describe, it, expect } from "vitest";

import { tokenize } from "./copilot-rich-text";

describe("CopilotRichText.tokenize", () => {
	it("returns a single text token when no markers match", () => {
		const tokens = tokenize("只是普通文字，没有 ASIN 也没有反引号");
		expect(tokens).toHaveLength(1);
		expect(tokens[0]).toEqual({
			kind: "text",
			value: "只是普通文字，没有 ASIN 也没有反引号",
		});
	});

	it("recognizes ASIN with case normalization to uppercase", () => {
		const tokens = tokenize("可以看 b07xyz1234 的详情");
		const asinTokens = tokens.filter((t) => t.kind === "asin");
		expect(asinTokens).toHaveLength(1);
		expect(asinTokens[0].value).toBe("B07XYZ1234");
	});

	it("recognizes backtick-wrapped term verbatim", () => {
		const tokens = tokenize("关注 `neck pillow` 这个词");
		const termTokens = tokens.filter((t) => t.kind === "term");
		expect(termTokens).toHaveLength(1);
		expect(termTokens[0].value).toBe("neck pillow");
	});

	it("handles mixed ASIN + term + text segments preserving order", () => {
		const tokens = tokenize("ASIN B07SRRQS5B 对应 `travel pillow` 关键词");
		expect(tokens.map((t) => t.kind)).toEqual([
			"text",
			"asin",
			"text",
			"term",
			"text",
		]);
		const asinToken = tokens.find((t) => t.kind === "asin");
		const termToken = tokens.find((t) => t.kind === "term");
		expect(asinToken?.value).toBe("B07SRRQS5B");
		expect(termToken?.value).toBe("travel pillow");
	});

	it("drops overlapping matches keeping the earliest-starting one", () => {
		const tokens = tokenize("看看 `B07ABC1234 相关词`");
		const termTokens = tokens.filter((t) => t.kind === "term");
		const asinTokens = tokens.filter((t) => t.kind === "asin");
		expect(termTokens).toHaveLength(1);
		expect(asinTokens).toHaveLength(0);
		expect(termTokens[0].value).toBe("B07ABC1234 相关词");
	});

	it("emits empty array for empty input", () => {
		expect(tokenize("")).toEqual([]);
	});

	it("captures multiple ASINs in one input", () => {
		const tokens = tokenize("B01ABC1234 和 B07XYZ5678 都是候选");
		const asins = tokens.filter((t) => t.kind === "asin").map((t) => t.value);
		expect(asins).toEqual(["B01ABC1234", "B07XYZ5678"]);
	});
});
