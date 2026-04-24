const PREFIX = "zeoprix-page-context";

function storageKey(productId: number | null | undefined, pageKey: string) {
	return `${PREFIX}:${productId ?? "global"}:${pageKey}`;
}

export function readPageContext(
	productId: number | null | undefined,
	pageKey: string,
): Record<string, unknown> {
	if (typeof window === "undefined") return {};
	try {
		const raw = window.localStorage.getItem(storageKey(productId, pageKey));
		return raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
	} catch {
		return {};
	}
}

export function writePageContext(
	productId: number | null | undefined,
	pageKey: string,
	context: Record<string, unknown>,
) {
	if (typeof window === "undefined") return;
	try {
		const key = storageKey(productId, pageKey);
		window.localStorage.setItem(key, JSON.stringify(context));
		window.dispatchEvent(
			new CustomEvent("zeoprix:page-context-updated", { detail: { key } }),
		);
	} catch {
		// ignore storage failures
	}
}

export function getPageContextKey(
	productId: number | null | undefined,
	pageKey: string,
) {
	return storageKey(productId, pageKey);
}
