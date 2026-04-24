import type { RecentActivityItem } from "@/lib/mock-data";

type StoredRecentActivityItem = RecentActivityItem & {
	timestamp: string;
};

const MAX_ITEMS = 6;

function storageKey(productId: number | null | undefined) {
	return `zeoprix-live-activity:${productId ?? "global"}`;
}

export function readFrontendActivity(
	productId: number | null | undefined,
): RecentActivityItem[] {
	if (typeof window === "undefined") return [];
	try {
		const raw = window.localStorage.getItem(storageKey(productId));
		if (!raw) return [];
		const parsed = JSON.parse(raw) as StoredRecentActivityItem[];
		return parsed.map((item) => ({
			label: item.label,
			title: item.title,
			detail: item.detail,
			href: item.href,
		}));
	} catch {
		return [];
	}
}

export function recordFrontendActivity(
	productId: number | null | undefined,
	item: RecentActivityItem,
) {
	if (typeof window === "undefined") return;
	try {
		const raw = window.localStorage.getItem(storageKey(productId));
		const current = raw ? (JSON.parse(raw) as StoredRecentActivityItem[]) : [];
		const next: StoredRecentActivityItem[] = [
			{ ...item, timestamp: new Date().toISOString() },
			...current,
		].slice(0, MAX_ITEMS);
		window.localStorage.setItem(storageKey(productId), JSON.stringify(next));
	} catch {
		// ignore storage failures
	}
}
