import {
	mockWorkbenchPayload,
	type ActionsPayload,
	type AnalysisPayload,
	type ReviewPayload,
	type SettingsPayload,
	type UploadPayload,
	type WorkbenchPayload,
} from "@/lib/mock-data";

const BACKEND_BASE_URL =
	process.env.BACKEND_BASE_URL ??
	process.env.NEXT_PUBLIC_BACKEND_BASE_URL ??
	"http://127.0.0.1:8008";

async function getJson<T>(path: string): Promise<T> {
	const response = await fetch(`${BACKEND_BASE_URL}${path}`, {
		cache: "no-store",
		next: { revalidate: 0 },
	});

	if (!response.ok) {
		throw new Error(`backend returned ${response.status}`);
	}

	return (await response.json()) as T;
}

function mergeWorkbench(payload: Partial<WorkbenchPayload>): WorkbenchPayload {
	return {
		...mockWorkbenchPayload,
		...payload,
		productContext:
			payload.productContext ?? mockWorkbenchPayload.productContext,
		productId: payload.productId ?? mockWorkbenchPayload.productId,
		workbenchStats:
			payload.workbenchStats ?? mockWorkbenchPayload.workbenchStats,
		topActions: payload.topActions ?? mockWorkbenchPayload.topActions,
		trendCards: payload.trendCards ?? mockWorkbenchPayload.trendCards,
		trendBars: payload.trendBars ?? mockWorkbenchPayload.trendBars,
		structureBuckets:
			payload.structureBuckets ?? mockWorkbenchPayload.structureBuckets,
		executionEffect:
			payload.executionEffect ?? mockWorkbenchPayload.executionEffect,
		opsTemplates: payload.opsTemplates ?? mockWorkbenchPayload.opsTemplates,
		aiCopilotCards:
			payload.aiCopilotCards ?? mockWorkbenchPayload.aiCopilotCards,
		analysisRows: payload.analysisRows ?? mockWorkbenchPayload.analysisRows,
		executionBatches:
			payload.executionBatches ?? mockWorkbenchPayload.executionBatches,
	};
}

export async function getWorkbenchPayload(
	productId?: number,
): Promise<WorkbenchPayload> {
	const params = productId ? `?product_id=${productId}` : "";
	try {
		return mergeWorkbench(
			await getJson<Partial<WorkbenchPayload>>(`/frontend/workbench${params}`),
		);
	} catch {
		return mockWorkbenchPayload;
	}
}

export async function getUploadPayload(
	productId?: number,
): Promise<UploadPayload> {
	const params = productId ? `?product_id=${productId}` : "";
	try {
		return mergeWorkbench(
			await getJson<UploadPayload>(`/frontend/upload${params}`),
		) as UploadPayload;
	} catch {
		return mockWorkbenchPayload as UploadPayload;
	}
}

export async function getAnalysisPayload(
	productId?: number,
): Promise<AnalysisPayload> {
	const params = productId ? `?product_id=${productId}` : "";
	try {
		return mergeWorkbench(
			await getJson<AnalysisPayload>(`/frontend/analysis${params}`),
		) as AnalysisPayload;
	} catch {
		return mockWorkbenchPayload as AnalysisPayload;
	}
}

export async function getActionsPayload(
	productId?: number,
): Promise<ActionsPayload> {
	const params = productId ? `?product_id=${productId}` : "";
	try {
		return mergeWorkbench(
			await getJson<ActionsPayload>(`/frontend/actions${params}`),
		) as ActionsPayload;
	} catch {
		return mockWorkbenchPayload as ActionsPayload;
	}
}

export async function getReviewPayload(
	productId?: number,
): Promise<ReviewPayload> {
	const params = productId ? `?product_id=${productId}` : "";
	try {
		return mergeWorkbench(
			await getJson<ReviewPayload>(`/frontend/review${params}`),
		) as ReviewPayload;
	} catch {
		return mockWorkbenchPayload as ReviewPayload;
	}
}

export async function getSettingsPayload(
	productId?: number,
): Promise<SettingsPayload> {
	const params = productId ? `?product_id=${productId}` : "";
	try {
		return mergeWorkbench(
			await getJson<SettingsPayload>(`/frontend/settings${params}`),
		) as SettingsPayload;
	} catch {
		return mockWorkbenchPayload as SettingsPayload;
	}
}

export { BACKEND_BASE_URL };
