import { mockWorkbenchPayload, type WorkbenchPayload } from "@/lib/mock-data"

const BACKEND_BASE_URL =
  process.env.BACKEND_BASE_URL ??
  process.env.NEXT_PUBLIC_BACKEND_BASE_URL ??
  "http://127.0.0.1:8000"

export async function getWorkbenchPayload(productId?: number): Promise<WorkbenchPayload> {
  const params = productId ? `?product_id=${productId}` : ""

  try {
    const response = await fetch(`${BACKEND_BASE_URL}/frontend/workbench${params}`, {
      cache: "no-store",
      next: { revalidate: 0 },
    })

    if (!response.ok) {
      throw new Error(`backend returned ${response.status}`)
    }

    const payload = (await response.json()) as Partial<WorkbenchPayload>
    return {
      ...mockWorkbenchPayload,
      ...payload,
      productContext: payload.productContext ?? mockWorkbenchPayload.productContext,
      workbenchStats: payload.workbenchStats ?? mockWorkbenchPayload.workbenchStats,
      topActions: payload.topActions ?? mockWorkbenchPayload.topActions,
      trendCards: payload.trendCards ?? mockWorkbenchPayload.trendCards,
      trendBars: payload.trendBars ?? mockWorkbenchPayload.trendBars,
      structureBuckets: payload.structureBuckets ?? mockWorkbenchPayload.structureBuckets,
      executionEffect: payload.executionEffect ?? mockWorkbenchPayload.executionEffect,
      opsTemplates: payload.opsTemplates ?? mockWorkbenchPayload.opsTemplates,
      aiCopilotCards: payload.aiCopilotCards ?? mockWorkbenchPayload.aiCopilotCards,
      analysisRows: payload.analysisRows ?? mockWorkbenchPayload.analysisRows,
      executionBatches: payload.executionBatches ?? mockWorkbenchPayload.executionBatches,
    }
  } catch {
    return mockWorkbenchPayload
  }
}
