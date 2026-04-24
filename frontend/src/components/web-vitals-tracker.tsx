"use client";
/**
 * WebVitalsTracker — Sprint 5 · C.4
 *
 * Logs Core Web Vitals (CLS / INP / LCP / FCP / TTFB) to the console in
 * development. Production can hook a beacon later (see docs/ENGINEERING_BACKLOG.md
 * § C.6).
 *
 * Uses Next.js 16 App Router native `useReportWebVitals`, so no extra deps.
 */
import { useReportWebVitals } from "next/web-vitals";

export function WebVitalsTracker() {
	useReportWebVitals((metric) => {
		if (process.env.NODE_ENV !== "development") return;
		// eslint-disable-next-line no-console
		console.debug(
			"[web-vitals]",
			metric.name,
			Math.round(metric.value * 100) / 100,
			metric.rating ?? "",
			metric.id,
		);
	});

	return null;
}
