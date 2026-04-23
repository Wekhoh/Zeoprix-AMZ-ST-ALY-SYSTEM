// frontend/src/lib/copilot-stream.ts
/**
 * Copilot SSE 流式客户端（Sprint 4 · A1）
 * 调用后端 POST /frontend/copilot/chat/stream，逐 frame 分发到 handlers。
 * AbortController signal 由调用方传入以支持取消。
 */

import { BACKEND_BASE_URL } from "@/lib/backend";

export type ActionLink = { label: string; href: string };

export type CopilotEnvelopeFrame = {
	followUpPrompts: string[];
	recommendedNextActions: string[];
	actionLinks: ActionLink[];
	warning: string | null;
};

export type CopilotFrame =
	| { type: "context"; contextLabel: string | null }
	| { type: "delta"; text: string }
	| ({ type: "envelope" } & CopilotEnvelopeFrame)
	| { type: "error"; message: string }
	| { type: "done" };

export type CopilotChatPayload = {
	product_id: number | null;
	page_key: string;
	page_title: string;
	page_context: Record<string, unknown>;
	user_message: string;
	history: Array<{ role: "assistant" | "user"; content: string }>;
};

export type StreamHandlers = {
	onContext?: (label: string | null) => void;
	onDelta: (text: string) => void;
	onEnvelope: (env: CopilotEnvelopeFrame) => void;
	onError: (message: string) => void;
	signal?: AbortSignal;
};

export async function streamCopilotChat(
	payload: CopilotChatPayload,
	handlers: StreamHandlers,
): Promise<void> {
	const response = await fetch(`${BACKEND_BASE_URL}/frontend/copilot/chat/stream`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
		signal: handlers.signal,
	});
	if (!response.ok) {
		handlers.onError(`HTTP ${response.status}`);
		return;
	}
	if (!response.body) {
		handlers.onError("response body is null");
		return;
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder("utf-8");
	let buffer = "";

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;
			buffer += decoder.decode(value, { stream: true });
			const events = buffer.split("\n\n");
			buffer = events.pop() ?? "";
			for (const evt of events) {
				const line = evt.trim();
				if (!line.startsWith("data: ")) continue;
				const jsonStr = line.slice("data: ".length);
				let frame: CopilotFrame;
				try {
					frame = JSON.parse(jsonStr) as CopilotFrame;
				} catch {
					continue;
				}
				if (process.env.NODE_ENV === "development") {
					console.debug("[copilot-stream]", frame);
				}
				switch (frame.type) {
					case "context":
						handlers.onContext?.(frame.contextLabel);
						break;
					case "delta":
						handlers.onDelta(frame.text);
						break;
					case "envelope":
						handlers.onEnvelope({
							followUpPrompts: frame.followUpPrompts,
							recommendedNextActions: frame.recommendedNextActions,
							actionLinks: frame.actionLinks,
							warning: frame.warning,
						});
						break;
					case "error":
						handlers.onError(frame.message);
						break;
					case "done":
						return;
				}
			}
		}
	} catch (err) {
		if ((err as Error).name === "AbortError") {
			return;
		}
		handlers.onError((err as Error).message);
	} finally {
		reader.releaseLock();
	}
}
