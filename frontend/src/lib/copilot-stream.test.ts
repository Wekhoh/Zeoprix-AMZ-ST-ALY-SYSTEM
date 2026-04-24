/**
 * Vitest smoke — Sprint 5 · D.8a
 *
 * 验证 `streamCopilotChat` 能把合法 SSE 字节流正确拆帧成 typed handlers 回调。
 * 用 Node 20 built-in `ReadableStream` 造一个假 Response，避开 DOM / 网络。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { streamCopilotChat } from "./copilot-stream";

function makeSseResponse(sseChunks: string[]): Response {
	const encoder = new TextEncoder();
	const stream = new ReadableStream({
		start(controller) {
			for (const chunk of sseChunks) {
				controller.enqueue(encoder.encode(chunk));
			}
			controller.close();
		},
	});
	return new Response(stream, {
		status: 200,
		headers: { "content-type": "text/event-stream" },
	});
}

describe("streamCopilotChat", () => {
	beforeEach(() => {
		vi.stubGlobal("fetch", vi.fn());
	});
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it("dispatches context/delta/envelope frames in order then exits on done", async () => {
		const sse = [
			'data: {"type":"context","contextLabel":"workbench"}\n\n',
			'data: {"type":"delta","text":"Hello"}\n\n',
			'data: {"type":"delta","text":" world"}\n\n',
			'data: {"type":"envelope","followUpPrompts":["p1"],"recommendedNextActions":["a1"],"actionLinks":[],"warning":null}\n\n',
			'data: {"type":"done"}\n\n',
		];
		(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
			makeSseResponse(sse),
		);

		const calls: string[] = [];
		const deltas: string[] = [];
		let envelopeSeen: unknown = null;
		let contextSeen: string | null = "";

		await streamCopilotChat(
			{
				page_key: "workbench",
				page_title: "工作台",
				user_message: "hi",
				history: [],
				page_context: {},
				product_id: null,
			},
			{
				onContext: (label) => {
					contextSeen = label;
					calls.push("context");
				},
				onDelta: (text) => {
					deltas.push(text);
					calls.push("delta");
				},
				onEnvelope: (env) => {
					envelopeSeen = env;
					calls.push("envelope");
				},
				onError: (msg) => {
					calls.push(`error:${msg}`);
				},
			},
		);

		expect(contextSeen).toBe("workbench");
		expect(deltas.join("")).toBe("Hello world");
		expect(envelopeSeen).toMatchObject({
			followUpPrompts: ["p1"],
			recommendedNextActions: ["a1"],
		});
		expect(calls).toEqual(["context", "delta", "delta", "envelope"]);
	});

	it("emits onError and exits on non-OK HTTP", async () => {
		(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
			new Response(null, { status: 503 }),
		);

		const errors: string[] = [];
		await streamCopilotChat(
			{
				page_key: "workbench",
				page_title: "工作台",
				user_message: "hi",
				history: [],
				page_context: {},
				product_id: null,
			},
			{
				onContext: () => {},
				onDelta: () => {},
				onEnvelope: () => {},
				onError: (msg) => {
					errors.push(msg);
				},
			},
		);

		expect(errors).toHaveLength(1);
		expect(errors[0]).toMatch(/HTTP\s+503/);
	});

	it("forwards backend error frame via onError", async () => {
		const sse = [
			'data: {"type":"error","message":"gemini down"}\n\n',
			'data: {"type":"done"}\n\n',
		];
		(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
			makeSseResponse(sse),
		);

		const errors: string[] = [];
		await streamCopilotChat(
			{
				page_key: "workbench",
				page_title: "工作台",
				user_message: "hi",
				history: [],
				page_context: {},
				product_id: null,
			},
			{
				onContext: () => {},
				onDelta: () => {},
				onEnvelope: () => {},
				onError: (msg) => {
					errors.push(msg);
				},
			},
		);

		expect(errors).toEqual(["gemini down"]);
	});
});
